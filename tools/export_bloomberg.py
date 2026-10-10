# -*- coding: utf-8 -*-
"""Bloomberg Intelligence 카탈리스트 캘린더(D:\\Catalyst\\raw\\excel\\Biopharma_catalyst_YYYYMMDD.xlsx) → data/bloomberg.json
사용: python tools/export_bloomberg.py [파일경로]   (생략 시 raw/excel 최신 파일)
주 1회 Bloomberg raw를 받아 둔 뒤 실행하고 커밋. 페이지 캘린더 탭의 'Bloomberg' 소스·개요 카드·회사 모아보기가 읽는다.
- Date Sort(Bloomberg가 정렬용으로 붙인 날짜)가 있는 행만. 7일 넘게 지난 것·ONGOING·PENDING은 뺀다.
- prec(정밀도)은 Expected Date 문구에서: 'Oct 9 2026'=day · 'Oct 9-14 2026'=range · 'Aug, 2026'=month · '3Q 2026'=quarter
  · '2H 2026'·'Mid/Early/Late/End of 2026'=half · '2026'·'>=2026'=year
- imp: Key Catalyst=True → high, 아니면 low (Hub 저술분의 high/medium과 섞여도 기본 필터에서 Key만 보이게)
"""
import sys, os, re, json, glob, datetime as dt, warnings
sys.stdout.reconfigure(encoding="utf-8")
warnings.filterwarnings("ignore")
import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = r"D:\Catalyst\raw\excel"
TYPE = {"Data Release": "phase-readout", "Trial Initiation": "trial-milestone", "Regulatory Filing": "regulatory-filing",
        "Regulatory Action": "regulatory-decision", "PDUFA": "pdufa", "Drug Launch": "drug-launch",
        "Medical Meeting": "data-presentation", "Last Patient In": "trial-milestone", "Trial Completion": "trial-milestone",
        "Loss of Exclusivity": "commercial", "M&A Deals": "corporate", "CHMP Meeting": "regulatory-decision"}
PHASE = {"PHASE_III": "Phase 3", "PHASE_II": "Phase 2", "PHASE_I": "Phase 1", "PHASE_I_II": "Phase 1/2",
         "PHASE_II_III": "Phase 2/3", "PRECLINICAL": "Preclinical", "PHASE_I_III": "Phase 1/3"}


MON = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def range_end(s, sort):
    """'Oct 23-27 2026' / 'Oct 30 - Nov 2 2026' → 끝 날짜 ISO. 못 읽으면 None."""
    s = (s or "").strip()
    m = re.match(r"^([A-Za-z]{3})[A-Za-z]*\.?,? \d{1,2} ?- ?(?:([A-Za-z]{3})[A-Za-z]*\.? )?(\d{1,2}),? (\d{4})$", s)
    if not m:
        return None
    mon = MON.get((m.group(2) or m.group(1)).lower())
    if not mon:
        return None
    try:
        return dt.date(int(m.group(4)), mon, int(m.group(3))).isoformat()
    except ValueError:
        return None


def prec_of(s):
    s = (s or "").strip()
    if re.match(r"^[A-Za-z]{3,5}\.?,? \d{1,2} \d{4}$", s): return "day"
    if re.match(r"^[A-Za-z]{3,5}\.?,? \d{1,2}-\d{1,2},? \d{4}$", s) or re.match(r"^[A-Za-z]{3,5}\.? \d{1,2} ?- ?[A-Za-z]{3,5}\.? \d{1,2},? \d{4}$", s): return "range"
    if re.match(r"^[A-Za-z]{3,9}\.?,? \d{4}$", s): return "month"
    if re.match(r"^(Early|Mid|Late|End of|>=|<=|>|<)\s*[A-Za-z]{3,9}\.?,? \d{4}$", s): return "month"
    if re.match(r"^[A-Za-z]{3,5}\.? \d{1,2} .*\d{4}$", s): return "day"  # 'Oct 18 6:05pm ET (...) 2026'
    if re.match(r"^[1-4]Q \d{4}", s): return "quarter"
    if re.match(r"^([12]H|Mid|Early|Late|End of|Fall|Spring|Summer|Winter) \d{4}", s): return "half"
    if re.match(r"^[<>]?=?\d{4}", s): return "year"
    return "year"


def tickers(s):
    out = []
    for p in re.split(r"\s*/\s*", s or ""):
        p = p.strip()
        if p:
            out.append(re.sub(r"\s+US$", "", p))
    return out


def main(argv):
    if len(argv) > 1:
        path = argv[1]
    else:
        fs = sorted(f for f in glob.glob(os.path.join(RAW, "Biopharma_catalyst_*.xlsx")) if "processed" not in f)
        path = fs[-1]
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["Calendar"]
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    asof = ""
    m = re.search(r"as of:\s*(\d{1,2})/(\d{1,2})/(\d{4})", str(rows[0][5] or ""))
    if m:
        asof = f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    today = dt.date.today()
    floor = (today - dt.timedelta(days=7)).isoformat()
    items = []
    for r in rows[2:]:
        co, asset, event, exp, srt, ind, moa, mod, io, key, cat, etype, phase, tk, notes, src, srct, chg, upd = r[2:21]
        if not isinstance(srt, dt.datetime) or not event:
            continue
        sort = srt.date().isoformat()
        if sort < floor:
            continue
        exp = str(exp or "").strip()
        items.append({"id": "bb-" + re.sub(r"[^a-z0-9]+", "-", f"{co} {asset} {event} {exp}".lower())[:90],
                      "src": "bb", "region": "GLOBAL", "sponsor": (co or "").strip() or "(학회)", "asset": (asset or "").strip(),
                      "event": re.sub(r"\s+", " ", str(event)).strip(), "ind": (ind or "").strip(), "ta": (moa or "").strip(),
                      "mod": (mod or "").strip(), "type": TYPE.get(etype, "other"), "cat": cat, "status": "upcoming",
                      "date": exp, "sort": sort, "prec": prec_of(exp), "end": range_end(exp, sort) if prec_of(exp) == "range" else None,
                      "imp": "high" if str(key) == "True" else "low", "key": str(key) == "True",
                      "stage": PHASE.get(phase, phase), "nct": None, "tk": tickers(tk),
                      "notes": re.sub(r"\s+", " ", str(notes or "")).strip()[:240], "src_type": (srct or "").strip(),
                      "upd": upd.date().isoformat() if isinstance(upd, dt.datetime) else None})
    items.sort(key=lambda x: (x["sort"], 0 if x["key"] else 1))
    out = {"generated": today.isoformat(), "asof": asof, "file": os.path.basename(path),
           "source": "Bloomberg Intelligence Biotech & Pharma Catalyst Calendar", "n": len(items), "items": items}
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    p = os.path.join(ROOT, "data", "bloomberg.json")
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    key_n = sum(1 for i in items if i["key"])
    print(f"{os.path.basename(path)} (as of {asof}) · {len(items)} items · key {key_n} → {p} ({os.path.getsize(p)//1024} KB)")


if __name__ == "__main__":
    main(sys.argv)
