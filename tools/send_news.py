# -*- coding: utf-8 -*-
"""대시보드 feed/news 항목을 텔레그램 메인 채널로 수동 전송 (rss 봇 send_telegram 과 같은 형식).
  python tools/send_news.py --id <feed id>            # 미리보기만(기본)
  python tools/send_news.py --id <feed id> --send     # 실제 전송
  python tools/send_news.py --url <기사 URL> --send
토큰·채널 ID는 디스크에 두지 않고 실행 때 Secret Manager(gcloud secrets versions access)에서 읽는다.
"""
import argparse, json, subprocess, sys, urllib.request
PROJECT = "project-56beef4a-f1e9-4e7b-b7a"
FEED = "https://storage.googleapis.com/biopharmabot-public/feed/news/latest.json"
CATEGORY_EMOJI = {"임상시험": "🧬", "딜": "🤝", "펀딩": "💰", "규제": "🏛️", "정책": "📋", "실적": "📊", "기타": "📰"}
RELEVANCE_LABEL = {"high": "🔴 HIGH", "medium": "🟡 MID", "low": "⚪ LOW"}

def secret(name: str) -> str:
    return subprocess.run(["gcloud", "secrets", "versions", "access", "latest", f"--secret={name}", f"--project={PROJECT}"],
                          capture_output=True, text=True, check=True, shell=True).stdout.strip()

def esc(t: str) -> str:
    return (t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--id"); ap.add_argument("--url"); ap.add_argument("--send", action="store_true")
    ap.add_argument("--korean-title", action="store_true", help="영문 원제 대신 한국어 헤드라인을 제목으로")
    a = ap.parse_args()
    items = json.load(urllib.request.urlopen(FEED))
    x = next((i for i in items if (a.id and i.get("id") == a.id) or (a.url and i.get("url") == a.url)), None)
    if not x:
        sys.exit("feed/news/latest.json 에 해당 항목이 없습니다")
    title = x.get("headline") if a.korean_title else (x.get("title") or x.get("headline"))
    cat = x.get("category", "기타"); rel = RELEVANCE_LABEL.get(x.get("relevance", "medium"), "⚪ LOW")
    msg = f"<b>{esc(title)}</b>\n\n{CATEGORY_EMOJI.get(cat, '📰')} {cat}  |  {rel}\n\n{esc(x.get('summary', ''))}\n\n📌 원문: {x.get('url', '')}"
    print(msg.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">"))
    print(f"\n[{len(msg)}자]", "전송 안 함(미리보기)" if not a.send else "전송 중…")
    if not a.send:
        return
    token, chat = secret("TELEGRAM_BOT_TOKEN"), secret("TELEGRAM_CHAT_ID")
    data = json.dumps({"chat_id": chat, "text": msg, "parse_mode": "HTML", "disable_web_page_preview": False}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        print("전송", "성공" if json.load(r).get("ok") else "실패")

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8"); main()
