# -*- coding: utf-8 -*-
"""GCS 공개 feed(news·dart·trials·clinical 날짜별 JSON) → 로컬 SQLite D:/NEWS/news.sqlite (환경변수 NEWS_DB로 변경 가능)

사용:  python tools/sync_news_db.py            # 새 날짜만 추가(오늘·어제는 항상 다시 읽음)
       python tools/sync_news_db.py --full     # 전체 날짜 다시 읽기
       --no-ctgov 를 주지 않으면 ctgov 스냅샷(비공개 버킷, gcloud 사용자 인증)·공개 feed(upcoming·company index·earnings·ipo)도
       D:/NEWS/ctgov/, D:/NEWS/feed/ 에 내려받고 스냅샷은 테이블 ctgov 로 적재한다. 자동 실행: Windows 작업 스케줄러 'Biopharmabot local sync' (매일 08:40)
       python tools/sync_news_db.py --kinds news   # 특정 종류만

feed 항목의 id가 기본키라 같은 기사는 두 번 들어가지 않는다. raw 컬럼에 원본 JSON 전체를 둔다.
전문검색: SELECT * FROM feed_fts WHERE feed_fts MATCH 'Novo OR 노보';
"""
import sys, os, json, sqlite3, datetime as dt, argparse
from google.cloud import storage

BUCKET = "biopharmabot-public"
KINDS = ["news", "dart", "trials", "clinical"]   # clinical = rss 봇 임상 심층분석(v57~, 2026-10-10 Hub 동기화 추가)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.environ.get("NEWS_DB", r"D:\NEWS\news.sqlite")  # 환경변수 NEWS_DB로 변경 가능
KST = dt.timezone(dt.timedelta(hours=9))

SCHEMA = """
CREATE TABLE IF NOT EXISTS feed(
  id TEXT PRIMARY KEY, kind TEXT, day TEXT, ts TEXT, published TEXT,
  title TEXT, headline TEXT, summary TEXT, category TEXT, relevance TEXT,
  source TEXT, url TEXT, raw TEXT);
CREATE INDEX IF NOT EXISTS ix_feed_kind_ts ON feed(kind, ts);
CREATE INDEX IF NOT EXISTS ix_feed_cat ON feed(category);
CREATE TABLE IF NOT EXISTS synced(kind TEXT, day TEXT, n INTEGER, at TEXT, PRIMARY KEY(kind, day));
CREATE VIRTUAL TABLE IF NOT EXISTS feed_fts USING fts5(title, headline, summary, content='feed', content_rowid='rowid');
CREATE TRIGGER IF NOT EXISTS feed_ai AFTER INSERT ON feed BEGIN
  INSERT INTO feed_fts(rowid, title, headline, summary) VALUES (new.rowid, new.title, new.headline, new.summary); END;
CREATE TRIGGER IF NOT EXISTS feed_ad AFTER DELETE ON feed BEGIN
  INSERT INTO feed_fts(feed_fts, rowid, title, headline, summary) VALUES('delete', old.rowid, old.title, old.headline, old.summary); END;
CREATE TRIGGER IF NOT EXISTS feed_au AFTER UPDATE ON feed BEGIN
  INSERT INTO feed_fts(feed_fts, rowid, title, headline, summary) VALUES('delete', old.rowid, old.title, old.headline, old.summary);
  INSERT INTO feed_fts(rowid, title, headline, summary) VALUES (new.rowid, new.title, new.headline, new.summary); END;
"""

PRIVATE_BUCKET = "biopharmabot-dart-jayjihoonshin"
CTGOV_SCHEMA = """
CREATE TABLE IF NOT EXISTS ctgov(nct TEXT PRIMARY KEY, sponsor TEXT, status TEXT, phases TEXT, start TEXT, pcd TEXT, pcd_t TEXT, cd TEXT,
  title TEXT, cond TEXT, interv TEXT, last_post TEXT, enroll INTEGER, has_results INTEGER, raw TEXT);
CREATE INDEX IF NOT EXISTS ctgov_sponsor ON ctgov(sponsor);
CREATE INDEX IF NOT EXISTS ctgov_pcd ON ctgov(pcd);
"""


def sync_ctgov(con, pub_bucket):
    """ctgov 스냅샷·스폰서(비공개 버킷 → gcloud storage cp) + 공개 feed 몇 개 → D:/NEWS 아래 파일 + 테이블 ctgov"""
    import subprocess, shutil
    root = os.path.dirname(DB)
    cdir, fdir = os.path.join(root, "ctgov"), os.path.join(root, "feed")
    os.makedirs(cdir, exist_ok=True); os.makedirs(fdir, exist_ok=True)
    for name in ("ctgov/upcoming.json", "ctgov/company/index.json", "earnings/latest.json", "ipo/watch.json"):
        try:
            txt = pub_bucket.blob(f"feed/{name}").download_as_text()
            dst = os.path.join(fdir, name.replace("/", "_"))
            open(dst, "w", encoding="utf-8").write(txt)
            print(f"[feed] {name} → {dst} ({len(txt)//1024} KB)")
        except Exception as e:
            if "404" in str(e):
                print(f"[feed] {name}: 아직 없음")   # ipo/watch.json 은 대기 목록을 처음 등록할 때 생김
            else:
                print(f"[feed 실패] {name}: {e}")
    # 마켓·매크로 일별 스냅샷(feed/market/<날짜>.json, feed/macro/<날짜>.json + kr_sector_hist.json) — 새 날짜만
    for kind in ("market", "macro"):
        kdir = os.path.join(fdir, kind); os.makedirs(kdir, exist_ok=True)
        have = set(os.listdir(kdir)); n = 0
        for blob in pub_bucket.list_blobs(prefix=f"feed/{kind}/"):
            name = os.path.basename(blob.name)
            if not name.endswith(".json") or name == "latest.json":
                continue
            if name in have and name != "kr_sector_hist.json":
                continue
            blob.download_to_filename(os.path.join(kdir, name)); n += 1
        print(f"[feed] {kind}: 새 파일 {n}개 → {kdir} (총 {len(os.listdir(kdir))}개)")
    gcloud = shutil.which("gcloud") or shutil.which("gcloud.cmd")
    if not gcloud:
        print("[ctgov] gcloud 없음 — 스냅샷 생략"); return
    r = subprocess.run([gcloud, "storage", "cp", f"gs://{PRIVATE_BUCKET}/ctgov_snapshots.json", f"gs://{PRIVATE_BUCKET}/ctgov_sponsors.json", cdir + os.sep],
                       capture_output=True, text=True, shell=(os.name == "nt"))
    if r.returncode != 0:
        print(f"[ctgov 실패] gcloud storage cp: {(r.stderr or r.stdout)[-300:]}"); return
    snap = json.load(open(os.path.join(cdir, "ctgov_snapshots.json"), encoding="utf-8"))
    con.executescript(CTGOV_SCHEMA)
    con.execute("DELETE FROM ctgov")
    con.executemany("INSERT INTO ctgov VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    [(n, v.get("sponsor"), v.get("status"), "|".join(v.get("phases") or []), v.get("start"), v.get("pcd"), v.get("pcd_t"), v.get("cd"),
                      v.get("title"), " / ".join(v.get("cond") or []), " / ".join(v.get("interv") or []), v.get("last_post"), v.get("enroll"),
                      1 if v.get("has_results") else 0, json.dumps(v, ensure_ascii=False)) for n, v in snap.items()])
    con.commit()
    print(f"[ctgov] 스냅샷 {len(snap)}건 → 테이블 ctgov, 파일 {cdir}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-ctgov", action="store_true", help="ctgov 스냅샷·공개 feed 내려받기 생략")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--kinds", default=",".join(KINDS))
    a = ap.parse_args()
    kinds = [k for k in a.kinds.split(",") if k in KINDS]

    os.makedirs(os.path.dirname(DB), exist_ok=True)
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    done = {(k, d) for k, d in con.execute("SELECT kind, day FROM synced")}
    today = dt.datetime.now(KST).date()
    recent = {(today - dt.timedelta(days=i)).isoformat() for i in range(2)}

    b = storage.Client.create_anonymous_client().bucket(BUCKET)  # 공개 버킷: 로그인 불필요
    added_total = 0
    for kind in kinds:
        for blob in b.list_blobs(prefix=f"feed/{kind}/"):
            name = os.path.basename(blob.name)
            if not name.endswith(".json") or name == "latest.json":
                continue
            day = name[:-5]
            if not a.full and (kind, day) in done and day not in recent:
                continue
            try:
                arr = json.loads(blob.download_as_text())
            except Exception as e:
                print(f"[읽기 실패] {kind}/{day}: {e}"); continue
            if not isinstance(arr, list):
                continue
            added = 0
            for x in arr:
                if not isinstance(x, dict) or not x.get("id"):
                    continue
                cur = con.execute(
                    "INSERT OR IGNORE INTO feed(id,kind,day,ts,published,title,headline,summary,category,relevance,source,url,raw)"
                    " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (x["id"], kind, day, x.get("ts"), x.get("published"), x.get("title") or x.get("headline"), x.get("headline"),
                     x.get("summary") or x.get("text"), x.get("category"), x.get("relevance"), x.get("source"), x.get("url"),
                     json.dumps(x, ensure_ascii=False)))
                added += cur.rowcount
            con.execute("INSERT OR REPLACE INTO synced VALUES(?,?,?,?)",
                        (kind, day, len(arr), dt.datetime.now(KST).isoformat(timespec="seconds")))
            con.commit()
            added_total += added
            print(f"{kind}/{day}: 파일 {len(arr)}건, 새로 추가 {added}건")

    for kind, n, lo, hi in con.execute("SELECT kind, count(*), min(day), max(day) FROM feed GROUP BY kind"):
        print(f"[{kind}] 전체 {n}건  {lo} ~ {hi}")
    print(f"새로 추가 합계 {added_total}건 → {DB}")
    if not a.no_ctgov:
        sync_ctgov(con, b)
    con.close()

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
