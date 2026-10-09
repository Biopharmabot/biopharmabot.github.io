# -*- coding: utf-8 -*-
"""GCS 공개 feed(news·dart·trials 날짜별 JSON) → 로컬 SQLite D:NEWS
ews.sqlite (환경변수 NEWS_DB로 변경 가능)

사용:  python tools/sync_news_db.py            # 새 날짜만 추가(오늘·어제는 항상 다시 읽음)
       python tools/sync_news_db.py --full     # 전체 날짜 다시 읽기
       python tools/sync_news_db.py --kinds news   # 특정 종류만

feed 항목의 id가 기본키라 같은 기사는 두 번 들어가지 않는다. raw 컬럼에 원본 JSON 전체를 둔다.
전문검색: SELECT * FROM feed_fts WHERE feed_fts MATCH 'Novo OR 노보';
"""
import sys, os, json, sqlite3, datetime as dt, argparse
from google.cloud import storage

BUCKET = "biopharmabot-public"
KINDS = ["news", "dart", "trials"]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.environ.get("NEWS_DB", r"D:NEWS
ews.sqlite")
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

def main():
    ap = argparse.ArgumentParser()
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
                    (x["id"], kind, day, x.get("ts"), x.get("published"), x.get("title"), x.get("headline"),
                     x.get("summary"), x.get("category"), x.get("relevance"), x.get("source"), x.get("url"),
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
    con.close()

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
