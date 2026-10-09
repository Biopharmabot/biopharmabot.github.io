# -*- coding: utf-8 -*-
"""KRX Open API(KOSPI·KOSDAQ 시리즈 일별시세) → feed/macro/kr_sector_hist.json 백필
사용: python tools/krx_hist_backfill.py 2025-12-01 2026-10-09 --out <파일>   (키: 환경변수 KRX_AUTH_KEY 또는 bots/daily/.krx_key.txt)
결과 형식 {지수코드: {날짜: 종가}} — macro.py 의 KR_SECTOR_IDX 와 같은 코드(KRD020020156 = KOSPI 제약(의약품), KRD020020610 = KOSDAQ 제약)
"""
import sys, os, io, json, time, argparse, datetime as dt, requests
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = os.environ.get("KRX_AUTH_KEY") or io.open(os.path.join(ROOT, "bots", "daily", ".krx_key.txt"), encoding="utf-8").read().strip().strip('"')
WANT = {("kospi_dd_trd", "제약"): "KRD020020156", ("kosdaq_dd_trd", "제약"): "KRD020020610", ("krx_dd_trd", "KRX 반도체"): "KRXSEMI",
        ("kospi_dd_trd", "코스피 200 정보기술"): "KS200_IT", ("kospi_dd_trd", "코스피 200 헬스케어"): "KS200_HC", ("kospi_dd_trd", "코스피 200 금융"): "KS200_FIN",
        ("kospi_dd_trd", "코스피 200 커뮤니케이션서비스"): "KS200_COMM", ("kospi_dd_trd", "코스피 200 경기소비재"): "KS200_DISC", ("kospi_dd_trd", "코스피 200 생활소비재"): "KS200_STAPLE",
        ("kospi_dd_trd", "코스피 200 산업재"): "KS200_IND", ("kospi_dd_trd", "코스피 200 에너지/화학"): "KS200_ENCH", ("kospi_dd_trd", "코스피 200 철강/소재"): "KS200_STEEL",
        ("kospi_dd_trd", "코스피 200 중공업"): "KS200_HEAVY", ("kospi_dd_trd", "코스피 200 건설"): "KS200_CONS"}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("start"); ap.add_argument("end"); ap.add_argument("--out", required=True); ap.add_argument("--merge"); ap.add_argument("--eps", help="호출할 엔드포인트만(쉼표)")
    a = ap.parse_args()
    hist = json.load(io.open(a.merge, encoding="utf-8")) if a.merge and os.path.exists(a.merge) else {}
    d, end = dt.date.fromisoformat(a.start), dt.date.fromisoformat(a.end)
    calls = 0
    while d <= end:
        if d.weekday() < 5:
            for ep in (a.eps.split(",") if a.eps else ("kospi_dd_trd", "kosdaq_dd_trd", "krx_dd_trd")):
                r = requests.get(f"https://data-dbg.krx.co.kr/svc/apis/idx/{ep}", params={"basDd": d.strftime("%Y%m%d")}, headers={"AUTH_KEY": KEY}, timeout=30)
                calls += 1
                if not r.ok:
                    print(d, ep, r.status_code, r.text[:80]); time.sleep(2); continue
                for x in r.json().get("OutBlock_1", []):
                    code = WANT.get((ep, x.get("IDX_NM")))
                    if code and x.get("CLSPRC_IDX"):
                        hist.setdefault(code, {})[d.isoformat()] = float(x["CLSPRC_IDX"].replace(",", ""))
                time.sleep(0.3)
        d += dt.timedelta(days=1)
    io.open(a.out, "w", encoding="utf-8").write(json.dumps(hist, ensure_ascii=False))
    for c, h in hist.items():
        ks = sorted(h); print(c, len(ks), ks[0], "~", ks[-1])
    print("calls", calls, "→", a.out)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8"); main()
