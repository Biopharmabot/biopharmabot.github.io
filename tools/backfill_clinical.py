# -*- coding: utf-8 -*-
"""텔레그램 '바이오파마봇 ClinicalTrials 모니터' 채널 JSON 내보내기(result.json) → feed/clinical/<날짜>.json + latest.json
  python tools/backfill_clinical.py D:/Download/result.json --out <폴더>
글 구조(rss 봇 send_clinical_telegram): 헤드라인 / 💊 기전 / ① 임상 데이터(▫ 유효성 결과·안전성·기타 효력) / ② 표준치료요법 / ③ 경쟁 약물 / ④ 개발 계획 / ▫ CTgov NCT… / 📌 원문: URL
"""
import argparse, json, io, os, re, hashlib
from datetime import datetime, timezone, timedelta
KST = timezone(timedelta(hours=9))

def plain(t):
    if isinstance(t, str): return t
    return "".join(x if isinstance(x, str) else x.get("text", "") for x in t)

SEC = [("efficacy_result", r"▫ 유효성 결과"), ("safety", r"▫ 안전성·부작용"), ("other_efficacy", r"▫ 기타 효력"),
       ("soc", r"② 표준치료요법"), ("competitors", r"③ 경쟁 약물"), ("dev_plan", r"④ 개발 계획"), ("ctgov", r"▫ CTgov"), ("url", r"📌 원문:")]

def parse(text: str) -> dict | None:
    lines = text.split("\n")
    if not lines or not lines[0].strip(): return None
    out = {"headline": lines[0].strip(), "moa": ""}
    m = re.search(r"^💊 (.+)$", text, re.M)
    if m: out["moa"] = m.group(1).strip()
    # 섹션 경계로 자르기
    marks = []
    for key, pat in SEC:
        for mm in re.finditer(pat, text):
            marks.append((mm.start(), mm.end(), key))
    marks.sort()
    for i, (s, e, key) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        body = text[e:end].strip()
        body = re.sub(r"\n*① 임상 데이터\s*$", "", body).strip()
        if key == "ctgov":
            out["nct"] = re.findall(r"NCT\d{8}", body)
        elif key == "url":
            out["url"] = body.split()[0] if body else ""
        else:
            out[key] = body
    if "url" not in out:
        m = re.search(r"https?://\S+", text); out["url"] = m.group(0) if m else ""
    out.setdefault("nct", [])
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("--out", required=True); a = ap.parse_args()
    d = json.load(io.open(a.src, encoding="utf-8"))
    byday, items = {}, []
    for m in d.get("messages", []):
        if m.get("type") != "message": continue
        text = plain(m.get("text", "")).strip()
        if not text or "① 임상 데이터" not in text: continue
        p = parse(text)
        if not p: continue
        ts = datetime.fromisoformat(m["date"]).replace(tzinfo=KST)
        it = {"id": "tg" + str(m.get("id")), "ts": ts.isoformat(timespec="seconds"), "kind": "clinical", **p, "text": text}
        items.append(it); byday.setdefault(ts.strftime("%Y-%m-%d"), []).append(it)
    os.makedirs(os.path.join(a.out, "feed", "clinical"), exist_ok=True)
    for day, arr in byday.items():
        io.open(os.path.join(a.out, "feed", "clinical", f"{day}.json"), "w", encoding="utf-8").write(json.dumps(arr, ensure_ascii=False))
    io.open(os.path.join(a.out, "feed", "clinical", "latest.json"), "w", encoding="utf-8").write(json.dumps(items[-300:], ensure_ascii=False))
    print(f"{len(items)}건 · {len(byday)}일 · {min(byday)} ~ {max(byday)} → {a.out}/feed/clinical")
    miss = [k for k in ("efficacy_result", "safety", "soc", "competitors") if sum(1 for x in items if not x.get(k)) > len(items) * 0.3]
    print("필드 누락 30% 초과:", miss or "없음", "| url 없음:", sum(1 for x in items if not x.get("url")))

if __name__ == "__main__":
    main()
