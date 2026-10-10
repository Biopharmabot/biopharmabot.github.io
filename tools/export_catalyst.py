# -*- coding: utf-8 -*-
"""Hub catalyst 테이블(D:\\Hub\\hub.sqlite) → data/catalyst.json · 회사 매핑 → data/companies.json
사용: python tools/export_catalyst.py
- catalyst: status upcoming/imminent, **region KR 제외**(2026-10-10 사용자 결정: 국내 저술은 내부 평가용, 공개 안 함). expected_date는 YYYY-MM-DD·YYYY-MM·YYYY-Qn·YYYY-Hn·YYYY·(미상) 혼재라
  정렬키(sort)·정밀도(prec)를 붙인다. 예정일이 45일 넘게 지난 것은 상태 미갱신분으로 보고 뺀다.
- companies: Hub company(krx·bloomberg 있는 것) + bots/daily/tickers.csv(미국 300여 종목).
  페이지의 종목 바로가기·회사 모아보기 매칭용.
"""
import sys, os, json, sqlite3, csv, re, datetime as dt
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = r"D:\Hub\hub.sqlite"


def parse_date(s):
    s = (s or "").strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s, "day"
    m = re.match(r"^(\d{4})-(\d{2})$", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-01", "month"
    m = re.match(r"^(\d{4})-Q([1-4])$", s)
    if m:
        return f"{m.group(1)}-{(int(m.group(2)) - 1) * 3 + 1:02d}-01", "quarter"
    m = re.match(r"^(\d{4})-H([12])$", s)
    if m:
        return f"{m.group(1)}-{1 if m.group(2) == '1' else 7:02d}-01", "half"
    if re.match(r"^\d{4}$", s):
        return f"{s}-01-01", "year"
    return "9999-12-31", "tbd"


def tickers(s):
    """'MRNA US / MRK US' → ['MRNA','MRK'] · 'ROG SW' → ['ROG SW'] · 'LLY' → ['LLY']"""
    out = []
    for p in re.split(r"\s*/\s*", s or ""):
        p = p.strip()
        if not p or p.lower() == "unknown":
            continue
        out.append(re.sub(r"\s+US$", "", p))
    return out


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    today = dt.date.today()
    floor = (today - dt.timedelta(days=45)).isoformat()
    rows, seen = [], set()
    for r in con.execute("select * from catalyst where status in ('upcoming','imminent') and region!='KR'"):
        sort, prec = parse_date(r["expected_date"])
        if sort < floor:
            continue
        key = (str(r["sponsor"]).strip().lower(), str(r["asset_raw"]).strip().lower(), sort, r["event_type"])
        if key in seen:
            continue  # 같은 회사·약물·시점·유형 중복 행(원천 저술 중복)
        seen.add(key)
        rows.append({"id": r["catalyst_id"], "src": "hub", "region": r["region"], "sponsor": r["sponsor"], "asset": r["asset_raw"],
                     "ind": r["indication"], "ta": r["ta"], "type": r["event_type"], "status": r["status"],
                     "date": r["expected_date"], "sort": sort, "prec": prec, "end": r["window_end"],
                     "imp": r["importance"], "stage": r["stage"], "nct": r["nct"], "tk": tickers(r["ticker"])})
    rows.sort(key=lambda x: (x["sort"], {"high": 0, "medium": 1, "low": 2}.get(x["imp"], 3)))
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    p = os.path.join(ROOT, "data", "catalyst.json")
    json.dump({"generated": today.isoformat(), "source": "Hub catalyst (직접 저술·추정 포함)", "n": len(rows), "items": rows},
              open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"catalyst {len(rows)} → {p} ({os.path.getsize(p)//1024} KB)")

    comp = {}
    for r in con.execute("select display,krx,bloomberg,n_catalyst from company "
                         "where (krx is not null and krx!='') or (bloomberg is not null and bloomberg!='')"):
        comp[r["display"]] = {"name": r["display"], "krx": (r["krx"] or "").strip() or None,
                              "tk": [] if "/" in r["display"] else tickers(r["bloomberg"]), "nc": r["n_catalyst"]}   # 'Hengrui/ Kailera' 같은 공동 스폰서 이름에는 티커를 붙이지 않음(2026-10-10)
    have = {t for c in comp.values() for t in c["tk"]}
    with open(os.path.join(ROOT, "bots", "daily", "tickers.csv"), encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) < 2 or row[0].startswith("#") or row[0] == "ticker":
                continue
            t, name = row[0].strip(), row[1].strip()
            if t not in have:
                comp[name] = {"name": name.title() if name.isupper() else name, "krx": None, "tk": [t], "nc": 0, "us": True}
    p2 = os.path.join(ROOT, "data", "companies.json")
    json.dump(sorted(comp.values(), key=lambda c: c["name"]), open(p2, "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    print(f"companies {len(comp)} → {p2} ({os.path.getsize(p2)//1024} KB)")


if __name__ == "__main__":
    main()
