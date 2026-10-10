# -*- coding: utf-8 -*-
"""키움증권 'Kiwoom Healthcare 종합정리' 주간 PDF 1페이지의 '향후 한달간 주요 예상 이벤트 달력' → data/kiwoom.json
사용: python tools/import_kiwoom.py [폴더 또는 PDF ...]   (생략 시 D:\\Download 의 '키움증권_*Kiwoom Healthcare 종합정리_YYYYMMDD.pdf' 전부)
- 달력 격자를 좌표로 복원한다: 날짜 숫자 행(일~토 7열)으로 주(週)를 나누고, 각 텍스트 조각은 왼쪽 끝이 열 시작과 맞으면 그 열,
  아니면 가운데가 들어가는 열의 날짜로 본다. 같은 열에서 바로 아랫줄이고 윗줄이 끝맺음(실적·PDUFA·해제·일·')' 등)이 아니면 이어 붙인다.
- 공휴일·'실적 시즌' 머리글은 뺀다. 여러 리포트에 겹치는 같은 (날짜, 문구)는 한 건(최신 리포트 기준).
- type 은 문구 키워드로 매긴다(earnings/approval/meeting/readout/trial/other). 회사는 data/companies.json 이름으로 찾아 sponsor·tk 를 채운다.
- 페이지는 이 파일을 Hub·Bloomberg 와 합쳐 보여 주며 출처는 표시하지 않는다(2026-10-10 사용자 결정).
"""
import sys, os, re, json, glob, datetime as dt
sys.stdout.reconfigure(encoding="utf-8")
import fitz

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DIR = r"D:\Download"
SKIP = re.compile(r"공휴일|대체휴일|한글날|개천절|추석|설날|성탄|크리스마스|신정|현충일|광복절|근로자의 날|어린이날|석가탄신일|실적 시즌|^[.;▶\s]*$")
DONE = re.compile(r"(서울|실적|PDUFA|해제|학회|Topline|탑라인|발표|결과|승인|허가|데이터|결정|상장|기간|일|주|월|\)|등|예정|종료|개시|마감|신청|제출|공개|회의|미팅|행사|데이|Day|E)\)?\s*$")
GENERIC = re.compile(r"(예상|제안|규칙|의견수렴|마감|간학회|화이자|머크|릴리|노보|노디스크|사노피|로슈|노바티스|아스트라제네카|애브비|암젠|길리어드|바이엘|다케다|다이이찌|리제네론|모더나|버텍스|존슨|글락소|베링거|테바|바이오젠|일라이|에자이|오츠카|아스텔라스|안과|면역항암|심혈관|세계폐암|폐암|피부과|유럽|미국|당뇨|혈액|종양|류마티스|신경|소화기|비뇨기|감염|호흡기|실적|학회|승인|허가|발표|해제|결과|데이터|제출|자료|추가|비임상|부분|홀드|미국|유럽|중국|일본|국내|글로벌|구두|포스터|등|및|기간|계약|기술평가|개월|보호예수|중순|초|말|상|임상|예정|결정|신청|출시|심사|톱라인|탑라인|중간|최종|종료|개시|환자|투여|적응증|치료제|백신|병용|단독|주|일|월|분기|년|에서|에게|에|의|로|과|와|을|를|이|가|은|는|도|만)")
TYPE_RULES = [
    ("earnings", re.compile(r"실적|어닝|Earnings", re.I)),
    ("approval", re.compile(r"PDUFA|승인|허가|CHMP|자문위|AdCom|ODAC|홀드|심사|BLA|NDA|MAA|CRL|FDA|EMA|식약처|MFDS", re.I)),
    ("meeting", re.compile(r"학회|\b(ESMO|ASCO|AACR|AASLD|SITC|ASH|AAO|ADA|EASD|ACC|AHA|ESC|ERS|ATS|AAN|EHA|ASGCT|ASN|ACR|EULAR|AAD|EADV|ARVO|WCLC|JPM|IR)\b|World ADC|J\.P\. ?Morgan|컨퍼런스|심포지엄|포럼|서밋|Summit|Congress|Conference|Meeting|구두|포스터|R&D ?Day|Corp\. ?Day|기업설명회")),
    ("readout", re.compile(r"Topline|탑라인|톱라인|결과|데이터|중간분석|interim|readout", re.I)),
    ("trial", re.compile(r"[1-3]상|임상|IND|투여|환자 등록|LPI|개시|첫 환자|FPI", re.I)),
]
MONTH_RE = re.compile(r"_(\d{8})\.pdf$")


def load_companies():
    try:
        cs = json.load(open(os.path.join(ROOT, "data", "companies.json"), encoding="utf-8"))
    except Exception:
        return []
    return [(c["name"], c.get("tk") or [], bool(c.get("krx"))) for c in cs if c.get("name")]


def match_company(text, comps):
    """문구의 토큰이 회사명의 앞부분과 같으면 그 회사(가장 짧은 이름). 한글 3자·영문 4자 이상 토큰만."""
    toks = [t for t in re.split(r"[\s/,;:()\[\]~·]+", text) if t]
    best = None
    for i, t in enumerate(toks[:6]):
        t2 = re.sub(r"(의|이|가|은|는|과|와|도|-|–)$", "", t)
        hangul = bool(re.search(r"[가-힣]", t2))
        if len(t2) < (3 if hangul else 4) or (not hangul and i > 0):
            continue
        for name, tk, kr in comps:
            nl = name.lower()
            if nl.startswith(t2.lower()) or nl.replace(" ", "").startswith(t2.lower()):
                if best is None or len(name) < len(best[0]):
                    best = (name, tk, kr)
        if best:
            break
    return best


TYPE_CANON = {"earnings": "earnings", "approval": "regulatory-decision", "meeting": "data-presentation", "readout": "phase-readout", "trial": "trial-milestone"}


def classify(text):
    """페이지 CT_TYPE/CT_GROUP 이 아는 유형 코드로 돌려준다."""
    for k, rx in TYPE_RULES:
        if rx.search(text):
            return TYPE_CANON[k]
    return "other"


def region_of(text):
    rest = GENERIC.sub("", text)
    return "KR" if re.search(r"[가-힣]", rest) else "GLOBAL"


def parse_calendar(pdf_path):
    m = MONTH_RE.search(os.path.basename(pdf_path))
    if not m:
        return None, []
    rep = dt.date(int(m.group(1)[:4]), int(m.group(1)[4:6]), int(m.group(1)[6:]))
    page = fitz.open(pdf_path)[0]
    spans = []
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                t = s["text"].strip()
                if t:
                    spans.append({"x0": s["bbox"][0], "y0": s["bbox"][1], "x1": s["bbox"][2], "y1": s["bbox"][3], "t": t, "font": s["font"]})
    # 요일 머리글 아래 ~ '주:' 각주 위
    hdr = [s for s in spans if s["t"] in ("일", "월", "화", "수", "목", "금", "토") and s["x1"] - s["x0"] < 12]
    if len(hdr) < 7:
        return rep, []
    top = max(s["y1"] for s in hdr)
    foot = min([s["y0"] for s in spans if s["t"].startswith("주:") and s["y0"] > top] or [page.rect.height])
    body = [s for s in spans if top < s["y0"] < foot]
    # 날짜 숫자 행: 한 줄에 7개의 1~31 숫자
    rows = {}
    for s in body:
        if re.fullmatch(r"\d{1,2}", s["t"]) and 1 <= int(s["t"]) <= 31:
            rows.setdefault(round(s["y0"]), []).append(s)
    day_rows = sorted((y, sorted(v, key=lambda s: s["x0"])) for y, v in rows.items() if len(v) == 7)
    if not day_rows:
        return rep, []
    cols = [s["x0"] for s in day_rows[0][1]]  # 7열 왼쪽 끝
    right = max(s["x1"] for s in body)
    bounds = cols + [right + 1]

    def col_of(s):
        for i, cx in enumerate(cols):
            if abs(s["x0"] - cx) <= 2.5:
                return i
        cx = (s["x0"] + s["x1"]) / 2
        for i in range(7):
            if bounds[i] <= cx < bounds[i + 1]:
                return i
        return 6

    # 주(週)별 날짜 매핑: 첫 행의 첫 숫자가 리포트 일자보다 크면 전월
    first = int(day_rows[0][1][0]["t"])
    y, mth = rep.year, rep.month
    if first > rep.day:
        mth -= 1
        if mth == 0:
            y, mth = y - 1, 12
    week_dates, prev = [], None
    for ry, nums in day_rows:
        ds = []
        for s in nums:
            d = int(s["t"])
            if prev is not None and d < prev:
                mth += 1
                if mth == 13:
                    y, mth = y + 1, 1
            prev = d
            try:
                ds.append(dt.date(y, mth, d))
            except ValueError:
                ds.append(None)
        week_dates.append((ry, ds))
    # 텍스트 조각 → (주, 열)
    texts = [s for s in body if not re.fullmatch(r"\d{1,2}", s["t"]) and not SKIP.search(s["t"]) and "Bold" not in s["font"]]
    cells = {}
    for s in texts:
        wk = max((i for i, (ry, _) in enumerate(week_dates) if ry < s["y0"]), default=None)
        if wk is None:
            continue
        cells.setdefault((wk, col_of(s)), []).append(s)
    items = []
    for (wk, ci), ss in cells.items():
        ss.sort(key=lambda s: s["y0"])
        merged = []
        for s in ss:
            if merged and s["y0"] - merged[-1]["y1"] < 6 and not DONE.search(merged[-1]["t"]):
                merged[-1] = {**merged[-1], "t": merged[-1]["t"] + " " + s["t"], "y1": s["y1"]}
            else:
                merged.append(dict(s))
        d = week_dates[wk][1][ci]
        if not d:
            continue
        for s in merged:
            for t in re.split(r"(?<=[가-힣])(?=[A-Z]{2,})", s["t"]):
                t = re.sub(r"\s+", " ", t).strip(" ;.,")
                if len(t) < 2 or SKIP.search(t):
                    continue
                items.append({"date": d.isoformat(), "text": t})
    return rep, items


def main():
    args = sys.argv[1:] or [DEFAULT_DIR]
    pdfs = []
    for a in args:
        if os.path.isdir(a):
            pdfs += glob.glob(os.path.join(a, "키움증권_*Kiwoom Healthcare 종합정리_*.pdf"))
        else:
            pdfs.append(a)
    pdfs = sorted(set(pdfs), key=lambda p: MONTH_RE.search(os.path.basename(p)).group(1) if MONTH_RE.search(p) else "")
    comps = load_companies()
    seen, out, latest = {}, [], None
    for p in pdfs:  # 오래된 것부터 → 같은 (날짜, 문구)는 최신 리포트가 덮음
        rep, items = parse_calendar(p)
        if rep is None:
            continue
        latest = max(latest or rep, rep)
        print(f"{os.path.basename(p)}: {len(items)}건")
        for it in items:
            key = (it["date"], re.sub(r"\s", "", it["text"]).lower())
            seen[key] = {**it, "rep": rep.isoformat()}
    uniq = {}
    for (d, _), it in sorted(seen.items()):
        k = (classify(it["text"]), re.sub(r"\s|\(.*?\)", "", it["text"]).lower())
        cur = uniq.get(k)
        if cur is None or it["rep"] > cur["rep"]:
            uniq[k] = it
    vals = sorted(uniq.values(), key=lambda x: x["date"])
    norm = lambda x: re.sub(r"\s", "", x["text"]).lower()
    vals = [a for a in vals if not any(b is not a and b["date"] == a["date"] and norm(a) != norm(b) and norm(a) in norm(b) for b in vals)]
    for it in vals:
        d, t = it["date"], it["text"]
        mc = match_company(t, comps)
        if mc:  # 회사명이 문구 맨 앞이면 asset 에서는 뺀다(화면이 회사 · 문구로 보이므로)
            first = t.split(" ")[0]
            if mc[0].lower().startswith(first.lower().rstrip("-–,")) and len(t) > len(first) + 2:
                t = t[len(first):].lstrip(" -–,")
        out.append({"id": "kw-" + re.sub(r"[^0-9a-zA-Z가-힣]+", "-", d + "-" + t)[:80].strip("-"), "src": "kw", "region": ("KR" if (mc[2] or re.search(r"[가-힣]", mc[0])) else "GLOBAL") if mc else region_of(t),
                    "sponsor": mc[0] if mc else "", "asset": t, "event": "", "ind": "", "ta": "", "type": classify(t), "status": "upcoming",
                    "date": d, "sort": d, "prec": "day", "end": d, "imp": "medium", "stage": None, "nct": None,
                    "tk": [k.split(" ")[0] for k in (mc[1] if mc else [])], "rep": it["rep"]})
    doc = {"generated": dt.date.today().isoformat(), "asof": latest.isoformat() if latest else None, "n": len(out), "items": out}
    dst = os.path.join(ROOT, "data", "kiwoom.json")
    json.dump(doc, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"→ data/kiwoom.json {len(out)}건 (최신 리포트 {doc['asof']})")
    if "--show" in sys.argv or True:
        for x in out:
            print(f"  {x['date']} [{x['type']:8}] {x['region']:6} {x['sponsor'][:14]:14} | {x['asset']}")


if __name__ == "__main__":
    main()
