# -*- coding: utf-8 -*-
"""봇 4개에 feed_publish(공개 버킷 저장)를 심는 1회성 패치. 멱등: 이미 패치된 파일은 건너뜀.
대상: C:\biopharmabot-rss-cloudrun\main.py · C:\biopharmabot-dart\main.py · C:\biopharmabot-ctgov\main.py · C:\biopharmabot-daily\daily.py
"""
import re, sys
sys.stdout.reconfigure(encoding="utf-8")

SNIP = r'''


# ──────────────────────────────────────────────
# [feed] 공개 대시보드(biopharmabot.github.io)용 저장
#   텔레그램으로 보낸 항목을 공개 버킷 feed/<kind>/<YYYY-MM-DD>.json 과
#   feed/<kind>/latest.json 에도 적는다. 실패해도 봇 동작에는 영향 없음.
# ──────────────────────────────────────────────
PUBLIC_BUCKET = os.environ.get("PUBLIC_BUCKET", "biopharmabot-public")
_FEED_KST = timezone(timedelta(hours=9))


def feed_publish(kind: str, items: list, single: bool = False):
    try:
        from google.cloud import storage as _st
        if not items:
            return
        now = datetime.now(_FEED_KST)
        b = _st.Client().bucket(PUBLIC_BUCKET)
        items = [dict(x) for x in items]
        for x in items:
            x.setdefault("ts", now.isoformat(timespec="seconds"))
            x["kind"] = kind
        if single:
            day = items[0].get("date") or now.strftime("%Y-%m-%d")
            for name in (f"feed/{kind}/{day}.json", f"feed/{kind}/latest.json"):
                blob = b.blob(name)
                blob.cache_control = "no-cache, max-age=0"
                blob.upload_from_string(json.dumps(items[0], ensure_ascii=False), content_type="application/json")
            return
        for name, cap in ((f"feed/{kind}/{now:%Y-%m-%d}.json", 3000), (f"feed/{kind}/latest.json", 300)):
            blob = b.blob(name)
            try:
                arr = json.loads(blob.download_as_text()) if blob.exists() else []
            except Exception:
                arr = []
            have = {x.get("id") for x in arr if x.get("id")}
            arr += [x for x in items if not x.get("id") or x["id"] not in have]
            arr = arr[-cap:]
            blob.cache_control = "no-cache, max-age=0"
            blob.upload_from_string(json.dumps(arr, ensure_ascii=False), content_type="application/json")
    except Exception as e:
        print(f"[feed] 저장 실패(무시): {e}")
'''


def patch(path, anchor, edits):
    s = open(path, encoding="utf-8").read()
    if "def feed_publish" in s:
        print("skip (already patched)", path); return
    i = s.index(anchor) + len(anchor)
    s = s[:i] + SNIP + s[i:]
    for old, new in edits:
        assert s.count(old) == 1, (path, old[:70], s.count(old))
        s = s.replace(old, new)
    open(path, "w", encoding="utf-8", newline="").write(s)
    print("patched", path)


# 1) RSS — 뉴스
patch("C:/biopharmabot-rss-cloudrun/main.py", 'SEEN_BLOB = "rss_seen_articles.json"', [(
"""                tg_ok = send_telegram(article, analysis)
                if tg_ok:
                    sonnet_sent += 1
""",
"""                tg_ok = send_telegram(article, analysis)
                if tg_ok:
                    sonnet_sent += 1
                    feed_publish("news", [{
                        "id": article.get("id") or hashlib.md5(article.get("link", "").encode()).hexdigest(),
                        "title": article.get("title", ""), "headline": analysis.get("headline", ""),
                        "summary": analysis.get("summary", ""), "category": cat, "relevance": rel,
                        "source": article.get("source", ""), "url": article.get("link", ""),
                        "published": article.get("published", ""),
                    }])
""")])

# 2) DART — 공시
patch("C:/biopharmabot-dart/main.py", 'GCS_BUCKET = os.environ.get("GCS_BUCKET", "biopharmabot-data")', [(
"""    if send_telegram_text(message):
        tag = "AI" if current_summary else "기본"
        print(f"[TG:{tag}] {filing['corp_name']} - {filing['report_nm'][:30]}")
""",
"""    if send_telegram_text(message):
        tag = "AI" if current_summary else "기본"
        print(f"[TG:{tag}] {filing['corp_name']} - {filing['report_nm'][:30]}")
        feed_publish("dart", [{
            "id": filing.get("rcept_no", ""), "company": filing.get("corp_name", ""),
            "stock_code": stock_code, "market": MARKET_LABEL.get(filing.get("corp_cls", ""), ""),
            "title": re.sub(r"\\s+", " ", filing.get("report_nm", "")).strip(),
            "summary": current_summary or "", "rcept_dt": filing.get("rcept_dt", ""),
            "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={filing.get('rcept_no', '')}",
        }])
""")])

# 3) ctgov — 임상 변경
REC = """{"id": f"{nct}:{today}", "nct": nct, "company": company, "region": region,
                               "change": KIND, "title": new.get("title", ""), "sponsor": new.get("sponsor", ""),
                               "status": new.get("status", ""), "phases": new.get("phases", []),
                               "cond": new.get("cond", [])[:3], "interv": new.get("interv", [])[:3],
                               "lines": LINES, "url": f"https://clinicaltrials.gov/study/{nct}"}"""
patch("C:/biopharmabot-ctgov/main.py", "TELEGRAM_SAFE = 3900", [(
"""    entries, changed, unchanged = [], 0, 0
    REGION_ORDER = {"KR": 0, "US": 1, "WATCH": 2}
""",
"""    entries, changed, unchanged = [], 0, 0
    feed_items = []  # [feed] 공개 대시보드용 구조화 레코드
    REGION_ORDER = {"KR": 0, "US": 1, "WATCH": 2}
"""), (
"""            entries.append((region, build_entry(nct, company, new, new_study_lines(new), kind)))
            changed += 1
""",
"""            entries.append((region, build_entry(nct, company, new, new_study_lines(new), kind)))
            feed_items.append(""" + REC.replace("KIND", "kind").replace("LINES", "new_study_lines(new)") + """)
            changed += 1
"""), (
"""                entries.append((region, build_entry(nct, company, new, lines, "change")))
                changed += 1
""",
"""                entries.append((region, build_entry(nct, company, new, lines, "change")))
                feed_items.append(""" + REC.replace("KIND", '"change"').replace("LINES", "lines") + """)
                changed += 1
"""), (
"""    if entries:
        send_report(entries, today)
""",
"""    if entries:
        send_report(entries, today)
        if not DRY_RUN:
            feed_publish("trials", feed_items)
""")])

# 4) daily — 미국 마켓
patch("C:/biopharmabot-daily/daily.py", 'ET = ZoneInfo("America/New_York")', [(
"""    ok = send_photo(png, caption)
    print("전송", "성공" if ok else "실패")
""",
"""    ok = send_photo(png, caption)
    print("전송", "성공" if ok else "실패")
    if ok:
        feed_publish("market", [{
            "id": trade_date.isoformat(), "date": trade_date.isoformat(),
            "index": [{"name": l, "value": v, "chg_pct": c} for l, v, c in index_rows],
            "top": [{"name": n, "chg_pct": c} for n, c in top], "bottom": [{"name": n, "chg_pct": c} for n, c in bot],
            "stocks": [{"rank": i, "ticker": t, "name": names[t], "close": round(close, 2), "chg_pct": round(chg, 2)}
                       for i, (t, close, chg, _) in enumerate(ranked, 1)],
        }], single=True)
""")])
p = "C:/biopharmabot-daily/daily.py"; s = open(p, encoding="utf-8").read()
s = s.replace("from datetime import date, datetime, timedelta\n", "from datetime import date, datetime, timedelta, timezone\n", 1)
if "\nimport json\n" not in s:
    s = s.replace("import csv\n", "import csv\nimport json\n", 1)
open(p, "w", encoding="utf-8", newline="").write(s)
r = "C:/biopharmabot-daily/requirements.txt"; t = open(r, encoding="utf-8").read()
if "google-cloud-storage" not in t:
    open(r, "a", encoding="utf-8").write("\ngoogle-cloud-storage\n")
print("done")
