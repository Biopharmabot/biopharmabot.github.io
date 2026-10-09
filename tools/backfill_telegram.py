# -*- coding: utf-8 -*-
"""텔레그램 채널 내보내기(HTML) → feed 날짜별 JSON(news·dart) 백필

사용:  python tools/backfill_telegram.py "<내보내기 폴더>" --out <출력폴더>          # 파싱만(드라이런)
       python tools/backfill_telegram.py "<내보내기 폴더>" --out <출력폴더> --upload # GCS에 올림

- 뉴스: <b>제목</b> / 이모지 카테고리 | 이모지 레벨 / 요약 / 📌 원문: URL  → id = md5(url) (봇과 동일 규칙)
- DART: 📢 [DART 공시] / 회사 (코드 | 시장 ...) / 📄 보고서명 / 상세 / 🔗 URL  → id = rcpNo
- 이미 feed에 있는 날짜는 기존 파일을 읽어 URL 기준으로 합친다(봇이 올린 건 그대로 둠).
- 마켓 데일리 테스트·안내 메시지는 건너뛴다.
"""
import sys, os, re, io, json, glob, html, hashlib, argparse, subprocess, collections

BUCKET = "biopharmabot-public"
REL = {"HIGH": "high", "MID": "medium", "LOW": "low"}
SRC_BY_HOST = {"prnewswire.com": "PRNewswire Pharma", "globenewswire.com": "GlobeNewswire", "businesswire.com": "Businesswire Pharma",
               "fiercebiotech.com": "Fierce Biotech", "fiercepharma.com": "Fierce Pharma", "endpts.com": "Endpoints"}
MSG = re.compile(r'<div class="message default clearfix[^"]*" id="message(\d+)">(.*?)(?=<div class="message |</body>)', re.S)

def clean(s):
    s = re.sub(r"<a [^>]*>(.*?)</a>", r"\1", s, flags=re.S)
    s = re.sub(r"</?(strong|b|i|em|u|code|pre|s)>", "", s)
    s = s.replace("<br>", "\n")
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()

def parse_news(t, ts):
    m = re.match(r"\s*(.*?)<br><br>\s*\S*\s*([^<|]+?)\s*\|\s*\S*\s*(HIGH|MID|LOW)\s*<br><br>(.*?)(?:<br><br>📌\s*원문:\s*(.*))?$", t, re.S)
    if not m:
        return None
    title, cat, rel, summary, tail = m.groups()
    url = ""
    if tail:
        u = re.search(r'href="([^"]+)"', tail) or re.search(r"(https?://\S+)", clean(tail))
        url = html.unescape(u.group(1)) if u else ""
    if not url:
        return None
    host = re.sub(r"^www\.", "", re.sub(r"^https?://([^/]+).*", r"\1", url))
    src = next((v for k, v in SRC_BY_HOST.items() if host.endswith(k)), host)
    return {"id": hashlib.md5(url.encode()).hexdigest(), "title": clean(title), "headline": "",
            "summary": clean(summary), "category": cat.strip(), "relevance": REL[rel], "source": src,
            "url": url, "published": "", "ts": ts, "kind": "news"}

def parse_dart(t, ts):
    body = clean(t)
    lines = [l for l in body.split("\n")]
    url = re.search(r"https://dart\.fss\.or\.kr/\S*rcpNo=(\d+)", body)
    if not url:
        return None
    rcp = url.group(1)
    comp = re.search(r"^(.+?)\s*\(([0-9A-Z]{6})\s*\|\s*([^|)]+?)(?:\s*\|[^)]*)?\)\s*$", "\n".join(lines[1:4]), re.M)
    title_m = re.search(r"^📄\s*(.+?)\s*$", body, re.M)
    title = title_m.group(1) if title_m else ""
    paren = re.match(r"(.*?)\s{2,}\((.*)\)\s*$", title)   # "보고서명              (요약)" 꼴
    summary = ""
    if paren:
        title, summary = paren.group(1).strip(), paren.group(2).strip()
    # 📄 다음 줄부터 🔗/📅 전까지가 상세
    seg = body.split("📄", 1)[1] if "📄" in body else ""
    seg = seg.split("\n", 1)[1] if "\n" in seg else ""
    seg = re.split(r"\n(?:📅|🔗)", seg)[0].strip()
    if seg and not summary:
        summary = seg
    elif seg:
        summary = summary + "\n" + seg
    return {"id": rcp, "company": comp.group(1).strip() if comp else "", "stock_code": comp.group(2) if comp else "",
            "market": comp.group(3).strip() if comp else "", "title": re.sub(r"\s+", " ", title),
            "summary": summary.strip(), "rcept_dt": rcp[:8],
            "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcp}", "ts": ts, "kind": "dart"}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("export_dir"); ap.add_argument("--out", required=True); ap.add_argument("--upload", action="store_true")
    a = ap.parse_args()
    rows = []
    for f in glob.glob(os.path.join(a.export_dir, "messages*.html")):
        h = io.open(f, encoding="utf-8").read()
        for mid, b in MSG.findall(h):
            d = re.search(r'title="(\d\d)\.(\d\d)\.(\d{4}) (\d\d:\d\d:\d\d) UTC\+09:00', b)
            t = re.search(r'<div class="text">(.*?)</div>', b, re.S)
            if d and t:
                rows.append((int(mid), f"{d.group(3)}-{d.group(2)}-{d.group(1)}T{d.group(4)}+09:00", t.group(1).strip()))
    rows.sort()
    by_day = collections.defaultdict(lambda: collections.defaultdict(list))
    skipped = collections.Counter()
    for mid, ts, t in rows:
        if "[DART" in t:
            x = parse_dart(t, ts); kind = "dart"
        elif "원문" in t:
            x = parse_news(t, ts); kind = "news"
        else:
            skipped["안내/기타"] += 1; continue
        if not x:
            skipped[f"{kind} 파싱실패"] += 1; print("  [파싱실패]", mid, clean(t)[:80].replace("\n", " ")); continue
        by_day[kind][ts[:10]].append(x)

    stats = collections.Counter()
    # 버킷에 이미 있는 날짜 파일 목록을 한 번만 받는다(날짜마다 gsutil을 부르면 너무 느림)
    ls = subprocess.run(["gsutil", "ls", f"gs://{BUCKET}/feed/news/", f"gs://{BUCKET}/feed/dart/"], capture_output=True, text=True, shell=True)
    on_bucket = set(l.strip() for l in ls.stdout.splitlines() if l.strip().endswith(".json"))
    for kind, days in by_day.items():
        for day, items in days.items():
            existing = []
            if f"gs://{BUCKET}/feed/{kind}/{day}.json" in on_bucket:
                r = subprocess.run(["gsutil", "cat", f"gs://{BUCKET}/feed/{kind}/{day}.json"], capture_output=True, shell=True)
                if r.returncode == 0 and r.stdout.strip():
                    existing = json.loads(r.stdout.decode("utf-8"))
            have = {e.get("url") for e in existing} | {e.get("id") for e in existing}
            seen = set(); new = []
            for x in items:
                if x["url"] in have or x["id"] in have or x["id"] in seen:
                    continue
                seen.add(x["id"]); new.append(x)
            merged = sorted(existing + new, key=lambda e: e.get("ts", ""))
            os.makedirs(os.path.join(a.out, "feed", kind), exist_ok=True)
            with io.open(os.path.join(a.out, "feed", kind, f"{day}.json"), "w", encoding="utf-8") as fp:
                json.dump(merged, fp, ensure_ascii=False)
            stats[(kind, "new")] += len(new); stats[(kind, "existing")] += len(existing); stats[(kind, "days")] += 1
            if existing:
                print(f"  {kind}/{day}: 기존 {len(existing)} + 추가 {len(new)}")
    print("건너뜀:", dict(skipped))
    for kind in ("news", "dart"):
        print(f"[{kind}] 날짜 {stats[(kind,'days')]}개, 새 항목 {stats[(kind,'new')]}건, 기존 유지 {stats[(kind,'existing')]}건")

    if a.upload:
        src = os.path.join(a.out, "feed")
        r = subprocess.run(["gsutil", "-m", "-h", "Cache-Control:no-cache, max-age=0", "-h", "Content-Type:application/json",
                            "cp", "-r", src, f"gs://{BUCKET}/"], shell=True)
        print("업로드", "완료" if r.returncode == 0 else f"실패 rc={r.returncode}")
    else:
        print("드라이런: --upload 를 붙이면 GCS에 올립니다 →", a.out)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
