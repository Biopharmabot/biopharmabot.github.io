# -*- coding: utf-8 -*-
"""수동 뉴스 발송: feed/news(대시보드)에 올리고, --send 면 텔레그램 메인 채널에도 같은 내용을 보낸다.
  python tools/send_news.py --url <기사 URL> --headline "..." --summary-file sum.txt --category 규제 --relevance high [--title "영문 원제"] [--source "Fierce Pharma"] [--send]
  python tools/send_news.py --url <기사 URL> --send          # 이미 feed 에 있는 항목을 그대로 전송
URL 이 feed 에 이미 있으면 그 항목을 고치고(헤드라인·요약·분류·중요도), 없으면 새 항목으로 만든다(id = md5(url), ts = 지금).
feed/news/<오늘>.json 과 latest.json 을 내려받아 고친 뒤 gcloud storage cp 로 되올린다. 텔레그램 형식은 rss 봇 send_telegram 과 같다.
토큰·채널 ID는 디스크에 두지 않고 실행 때 Secret Manager(gcloud secrets versions access)에서 읽는다.
"""
import argparse, hashlib, io, json, os, subprocess, sys, tempfile, urllib.request
from datetime import datetime, timezone, timedelta
PROJECT = "project-56beef4a-f1e9-4e7b-b7a"; BUCKET = "biopharmabot-public"
PUB = f"https://storage.googleapis.com/{BUCKET}/feed/news/"
KST = timezone(timedelta(hours=9))
CATEGORY_EMOJI = {"임상시험": "🧬", "딜": "🤝", "펀딩": "💰", "규제": "🏛️", "정책": "📋", "실적": "📊", "기타": "📰"}
RELEVANCE_LABEL = {"high": "🔴 HIGH", "medium": "🟡 MID", "low": "⚪ LOW"}

def sh(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, check=True, shell=True, **kw).stdout

def secret(name):
    return sh(["gcloud", "secrets", "versions", "access", "latest", f"--secret={name}", f"--project={PROJECT}"]).strip()

def esc(t):
    return (t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def fetch(name):
    try:
        return json.load(urllib.request.urlopen(PUB + name))
    except Exception:
        return []

def upload(local, name):
    sh(["gcloud", "storage", "cp", local, f"gs://{BUCKET}/feed/news/{name}", "--cache-control=no-cache, max-age=0", f"--project={PROJECT}"])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True); ap.add_argument("--headline"); ap.add_argument("--summary"); ap.add_argument("--summary-file")
    ap.add_argument("--category", choices=list(CATEGORY_EMOJI)); ap.add_argument("--relevance", choices=list(RELEVANCE_LABEL))
    ap.add_argument("--title", help="영문 원제(새 항목일 때)"); ap.add_argument("--source", help="매체명(새 항목일 때)")
    ap.add_argument("--send", action="store_true", help="텔레그램 메인 채널 전송"); ap.add_argument("--korean-title", action="store_true")
    a = ap.parse_args()
    summary = a.summary or (io.open(a.summary_file, encoding="utf-8").read().strip() if a.summary_file else None)
    now = datetime.now(KST); today = now.strftime("%Y-%m-%d")
    latest = fetch("latest.json"); cur = next((x for x in latest if x.get("url") == a.url), None)
    if cur is None and not (a.headline and summary):
        sys.exit("feed 에 없는 URL 입니다 — --headline 과 --summary(-file) 가 필요합니다")
    item = dict(cur) if cur else {"id": hashlib.md5(a.url.encode()).hexdigest(), "title": a.title or a.headline, "source": a.source or "수동",
                                 "url": a.url, "published": now.strftime("%a, %d %b %Y %H:%M:%S +0900"), "ts": now.isoformat(timespec="seconds"), "kind": "news",
                                 "category": "기타", "relevance": "medium"}
    for k, v in (("headline", a.headline), ("summary", summary), ("category", a.category), ("relevance", a.relevance), ("title", a.title), ("source", a.source)):
        if v: item[k] = v
    # feed 갱신: 항목이 있던 날짜 파일(ts 기준) + latest
    day = (item.get("ts") or now.isoformat())[:10]
    tmp = tempfile.mkdtemp()
    for name in (f"{day}.json", "latest.json"):
        arr = fetch(name); hit = False
        for i, x in enumerate(arr):
            if x.get("id") == item["id"]:
                arr[i] = item; hit = True
        if not hit:
            arr.append(item); arr.sort(key=lambda x: x.get("ts", ""))
            if name == "latest.json": arr = arr[-300:]
        local = os.path.join(tmp, name); io.open(local, "w", encoding="utf-8").write(json.dumps(arr, ensure_ascii=False)); upload(local, name)
        print(f"feed/news/{name} {'갱신' if hit else '추가'}")
    title = item.get("headline") if a.korean_title else (item.get("title") or item.get("headline"))
    cat = item.get("category", "기타"); rel = RELEVANCE_LABEL.get(item.get("relevance", "medium"), "⚪ LOW")
    msg = f"<b>{esc(title)}</b>\n\n{CATEGORY_EMOJI.get(cat, '📰')} {cat}  |  {rel}\n\n{esc(item.get('summary', ''))}\n\n📌 원문: {item.get('url', '')}"
    print("\n" + msg.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">") + f"\n\n[{len(msg)}자]")
    if not a.send:
        print("텔레그램 전송 안 함(--send 없음)"); return
    token, chat = secret("TELEGRAM_BOT_TOKEN"), secret("TELEGRAM_CHAT_ID")
    data = json.dumps({"chat_id": chat, "text": msg, "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        print("텔레그램 전송", "성공" if json.load(r).get("ok") else "실패")

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8"); main()
