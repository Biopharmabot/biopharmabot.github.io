# -*- coding: utf-8 -*-
"""GCS 공개 feed/ctgov/company/<키>.json (ctgov 봇 v1.8+ 회사별 '지금 움직이는 시험' 스냅샷) → news.sqlite `ctgov_trial`

사용:  python tools/sync_ctgov_company.py          # index.json의 회사 전부
       python tools/sync_ctgov_company.py --keys VKTX,LLY,한미약품

feed 한 건 = 회사(key: 미국=티커·국내=회사명)가 리드 스폰서인 시험 중 ① 최근 3개월 시작 ② primary/study completion ±3개월
③ 최근 1개월 갱신인 것(회사당 최대 80건). 봇 요약이 아니라 ctgov 등록 필드 그대로다(start·pcd·cd·status·phase·cond·interv·enroll).
매일 08:00 스냅샷이라 같은 (key, nct)를 날마다 다시 본다 → first_seen/last_seen을 유지하고, pcd가 바뀌면 pcd_prev·pcd_changed_at에 직전 값을 남긴다.
창에서 빠진 시험(완료된 지 3개월 넘음 등)은 지우지 않는다 — last_seen이 asof보다 오래된 것이 '창 밖'이다.
Hub(news_adapter)가 이 표를 읽어 company·asset·indication·trial·catalyst로 조인한다. (2026-10-10)
"""
import sys, os, json, sqlite3, argparse, datetime as dt, urllib.request, urllib.parse
import concurrent.futures as cf

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = "https://storage.googleapis.com/biopharmabot-public/feed/ctgov/company/"
DB = os.environ.get("NEWS_DB", r"D:\NEWS\news.sqlite")
KST = dt.timezone(dt.timedelta(hours=9))

SCHEMA = """
CREATE TABLE IF NOT EXISTS ctgov_trial(
  key TEXT, nct TEXT, name TEXT, region TEXT,
  title TEXT, status TEXT, phases TEXT, cond TEXT, interv TEXT,
  start TEXT, pcd TEXT, pcd_t TEXT, cd TEXT, last_post TEXT, enroll TEXT, why TEXT, why_stopped TEXT, has_results TEXT,
  pcd_prev TEXT, pcd_changed_at TEXT,
  first_seen TEXT, last_seen TEXT, raw TEXT,
  PRIMARY KEY(key, nct));
CREATE INDEX IF NOT EXISTS ix_ctgov_nct ON ctgov_trial(nct);
CREATE INDEX IF NOT EXISTS ix_ctgov_pcd ON ctgov_trial(pcd);
CREATE TABLE IF NOT EXISTS ctgov_sync(asof TEXT PRIMARY KEY, n_companies INTEGER, n_trials INTEGER, at TEXT);
"""


def _get(url, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _s(v):
    """list는 JSON 문자열로, 그 외는 문자열로(봇 출력이 list/문자열 혼재)."""
    if v is None:
        return None
    if isinstance(v, list):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys", default="")
    a = ap.parse_args()
    idx = _get(BASE + "index.json")
    asof = idx.get("asof") or dt.datetime.now(KST).strftime("%Y-%m-%d")
    keys = [k for k in a.keys.split(",") if k] or list(idx.get("companies") or {})

    os.makedirs(os.path.dirname(DB), exist_ok=True)
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)

    def fetch(k):
        try:
            return k, _get(BASE + urllib.parse.quote(k) + ".json")
        except Exception as e:
            return k, e

    n_tr = n_new = n_pcd = n_fail = 0
    with cf.ThreadPoolExecutor(12) as ex:
        for k, d in ex.map(fetch, keys):
            if not isinstance(d, dict):
                n_fail += 1
                print(f"[읽기 실패] {k}: {d}")
                continue
            for it in d.get("items") or []:
                nct = it.get("nct")
                if not nct:
                    continue
                n_tr += 1
                old = con.execute("SELECT pcd, first_seen FROM ctgov_trial WHERE key=? AND nct=?", (k, nct)).fetchone()
                pcd = _s(it.get("pcd"))
                pcd_prev = pcd_changed = None
                first = asof
                if old:
                    first = old[1] or asof
                    if old[0] and pcd and old[0] != pcd:
                        pcd_prev, pcd_changed = old[0], asof
                        n_pcd += 1
                else:
                    n_new += 1
                con.execute("""INSERT INTO ctgov_trial(key,nct,name,region,title,status,phases,cond,interv,start,pcd,pcd_t,cd,last_post,
                                 enroll,why,why_stopped,has_results,pcd_prev,pcd_changed_at,first_seen,last_seen,raw)
                               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                               ON CONFLICT(key,nct) DO UPDATE SET name=excluded.name, region=excluded.region, title=excluded.title,
                                 status=excluded.status, phases=excluded.phases, cond=excluded.cond, interv=excluded.interv,
                                 start=excluded.start, pcd=excluded.pcd, pcd_t=excluded.pcd_t, cd=excluded.cd, last_post=excluded.last_post,
                                 enroll=excluded.enroll, why=excluded.why, why_stopped=excluded.why_stopped, has_results=excluded.has_results,
                                 pcd_prev=COALESCE(excluded.pcd_prev, ctgov_trial.pcd_prev),
                                 pcd_changed_at=COALESCE(excluded.pcd_changed_at, ctgov_trial.pcd_changed_at),
                                 last_seen=excluded.last_seen, raw=excluded.raw""",
                            (k, nct, d.get("name"), d.get("region"), it.get("title"), it.get("status"), _s(it.get("phases")),
                             _s(it.get("cond")), _s(it.get("interv")), _s(it.get("start")), pcd, _s(it.get("pcd_t")), _s(it.get("cd")),
                             _s(it.get("last_post")), _s(it.get("enroll")), _s(it.get("why")), _s(it.get("why_stopped")),
                             _s(it.get("has_results")), pcd_prev, pcd_changed, first, asof, json.dumps(it, ensure_ascii=False)))
    con.execute("INSERT OR REPLACE INTO ctgov_sync VALUES(?,?,?,?)",
                (asof, len(keys) - n_fail, n_tr, dt.datetime.now(KST).isoformat(timespec="seconds")))
    con.commit()
    tot = con.execute("SELECT count(*) FROM ctgov_trial").fetchone()[0]
    print(f"[ctgov_trial] asof {asof} · 회사 {len(keys) - n_fail}/{len(keys)} · 이번 스냅샷 {n_tr}건(신규 {n_new} · pcd 변경 {n_pcd}) · 누적 {tot}건 → {DB}")
    return 0 if n_fail < len(keys) else 1


if __name__ == "__main__":
    sys.exit(main())
