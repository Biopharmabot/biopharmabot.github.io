# Biopharmabot 대시보드

- 공개 페이지: https://biopharmabot.github.io (이 저장소 `index.html` · GitHub Pages · 로그인 없음)
- 실시간 feed: 공개 버킷 `gs://biopharmabot-public/feed/<kind>/latest.json` (`kind` = news · dart · trials · market). 봇이 텔레그램으로 보낸 항목을 `feed_publish()`로 같이 적는다.
- 정적 데이터(`data/`): 이 저장소에 커밋하는 JSON. 헷지펀드 13F(분기) · Hub 카탈리스트 · Bloomberg 카탈리스트(주 1회) · 회사 매핑.

## 탭 (2026-10-08 개편 · mooboard · 박종현 coverage 대시보드 · bio-research.ai 참고)
| 탭 | 내용 | 데이터 |
|---|---|---|
| 개요 | KPI 줄 · 카드(HIGH 뉴스·임상·이번 주 카탈리스트·마켓 무버·13F 매집×등락·매집 종목 소식·14일 트렌드). "지난번 본 뒤로"·NEW 태그 없음(2026-10-10) | 전부 |
| Newsflow · Clinical Trials | 봇 feed(필터·검색·이전 날짜 더 보기). Newsflow = 카테고리 + HIGH/MID/LOW. **Clinical Trials = "임상시험 결과"(기본, rss 봇 임상 심층분석 → feed `clinical`(v58: phase·nct 필드, 48h 같은 사건 중복 차단 rss_clinical_recent.json), 접으면 유효성 첫 줄·펼치면 유효성/안전성/기타/표준치료/경쟁/개발계획) / "임상시험 변동"(ctgov 봇 → feed `trials`; v1.9: 종료 상태 시험의 날짜·환자수 소급 편집, 환자수 ±5% 미만 변동은 알림 안 함)**. 사이드바·시간순/종목별·건수·배지 없음. feed clinical 백필: 텔레그램 채널 JSON 내보내기 → `tools/backfill_clinical.py result.json --out <폴더>` → gcloud storage cp (2026-08-10~10-09 283건 완료). DART 탭은 2026-10-10 제거(dart 봇·텔레그램은 그대로) | feed |
| US 헬스케어 (글로벌마켓 다음, 2026-10-10 개명·이동, 구 마켓 탭. 유니버스 = BB 피어 308 + NBI/IBB/XBI 보강 26 + **13F 보유 종목 보강 128(2026-10-10, tickers.csv source=13F; 같은 날 야후에 없는 인수·상폐 16개 제거, 티커 변경 4개 교체 AADI→WHWK·ATHA→LONA·CYBN→HELP·OCUP→IRD, 중복 3개 제거 — tickers_extra.csv 주석 참고, daily v1.33)** + IPO 편입분(feed/ipo/watch.json listed, v1.34) = 미국 상장 462종목. 텔레그램 데일리·feed 모두 462 전부. ctgov 스폰서(v1.10, 봇 상태 기준 478개 — 10-10 08:00 자동 실행에서 113개 신규 편입)도 13F 보강분 포함하되 의료기기·진단·도구·서비스·보험은 EXCLUDE_MEDTECH 로 제외, 연구자 주도(IIT)는 봇이 lead sponsor class 로 제외) | 지수 띠 · KPI(등락 중앙값·급등락·RSI 과열/과매도·52주 고점권·거래량 2배) · Top/Bottom 10 · 전체 307종목 표(1D 양방향 막대·1W·1M·RSI14+1년 백분위·52주 고점比·거래량比·신호 배지·13F) | feed market (daily v1.8부터 기술지표 포함) |
| 글로벌마켓 (개요 바로 다음) | 전체 시장 스냅샷(미국 장 마감 기준 아침). 상단 KPI 12개(S&P·NASDAQ·Dow·STOXX600·DAX·FTSE100 / Nikkei·CSI300·상해·항셍·KOSPI·KOSDAQ) · 바이오 KPI 6개(NBI·XBI·SOX·KOSPI의약품·KOSDAQ제약·KRX반도체) · CNN Fear & Greed · 국가별 블록(미국·중국홍콩·한국): 왼쪽 지수(1D/1M/YTD/스파크) 오른쪽 그 국가 전일 섹터 등락 — 국가별 단일 소스 원칙: 미국 GICS SPDR ETF 11, 홍콩 항셍 종합산업지수 12(Hang Seng Indexes 공식 API), 한국 KRX 산업지수 17(KRX Open API krx_dd_trd, 코스피+코스닥 통합; 2026-10-10 결정). 한국 지수 = KOSPI·KOSDAQ·KOSPI200·코스닥150·KRX반도체·KRX헬스케어·코스닥150헬스케어·KOSPI의약품·KOSDAQ제약(KRX API 시리즈는 `feed/macro/kr_sector_hist.json` 에 2025-12-01부터 종가 누적, 백필은 `tools/krx_hist_backfill.py`) · 금리(야후 국채 + FRED) · 환율·원자재·VIX/MOVE | feed macro (daily v1.27 `macro.py`, `sectors{국가}`·`sector_src` 필드) |
| 헷지펀드 | 13F 분기 동향(신규·순매수·순매도·혼조·청산·M&A소멸, 주식수/비중 기준, 티커 옆 전일 등락) · **수급 지도 산점도**(가로 13F 합산 비중 변화 · 세로 1M/1W/1D/3M 수익률, 사분면 담고·오름 등) · 종목별 시그널 표 · 교차 보유 매트릭스 · 펀드별 상위 보유 | `data/hedge.json` + feed market |
| Catalysts | Hub 저술 + Bloomberg 캘린더 합본(화면에는 소스 표기 없음 — 2026-10-10 사용자 결정, 중요도 기준 비공개) + **실적 발표**(daily v1.35 `earnings.py` → feed `earnings`: 유니버스 종목 야후 calendar 다음 발표일, 중요도는 시총 ≥500억$ HIGH·≥50억$ MID·그 외 LOW). 헤더는 '업데이트 날짜' 하나. 필터 = 전체/글로벌/국내 · HIGH/MID/LOW · 이벤트 칩 6개(임상 결과·임상 진행·학회 발표·허가 결정·기타(corporate·other)·실적 발표; 허가 신청·출시·상업화·라이선스 딜 유형은 제외) · 검색. **월간 달력 격자**(날짜 클릭 → 그 날만) · 이번 주/다음 주(D-n)/월별 · 진행 중 · 이후 · 미정 · 지난 예정일 | `data/catalyst.json` · `data/bloomberg.json` · `data/kiwoom.json` · feed earnings |
| 트렌드 | 최근 14일 일별 건수·카테고리·출처·회사 상위·카탈리스트 월별/유형/출처 | feed 날짜 파일 + data |
| 회사 모아보기 | 회사명·티커 클릭 또는 상단 「회사·티커 바로가기」 → 마켓 · 13F(미국 티커 회사만) · **임상 현황** · 카탈리스트 · 뉴스 · DART 공시(국내 회사만)를 한 패널에. 딥링크 `#<탭>&co=<티커 또는 회사명>`. 임상 현황 = ctgov 봇(v1.8)이 매일 08:00 스냅샷에서 만드는 `feed/ctgov/company/<티커 또는 회사명>.json`(+index.json): 회사가 리드 스폰서인 시험 중 최근 3개월 시작 · primary/study completion ±3개월 · 최근 1개월 갱신인 것만, 최근 활동순 최대 80건. "13F 매집/축소" 태그는 화면에 안 보임(2026-10-10) | 전부 + feed ctgov |

## 폴더
```
Biopharmabot/                ← git: Biopharmabot/biopharmabot.github.io (페이지·tools·data 추적)
  index.html                 페이지 소스 (단일 파일 · 외부 라이브러리 없음)
  data/hedge.json            tools/export_hedge.py     ← D:\13F\out\Hedge_fund_<분기>.xlsx (분기 1회)
  data/catalyst.json         tools/export_catalyst.py  ← D:\Hub\hub.sqlite catalyst (upcoming/imminent · 수시)
  data/companies.json        (export_catalyst.py가 같이 씀) Hub company krx·bloomberg + bots/daily/tickers.csv
  data/bloomberg.json        tools/export_bloomberg.py ← D:\Catalyst\raw\excel\Biopharma_catalyst_YYYYMMDD.xlsx 최신 (주 1회)
  tools/import_kiwoom.py     키움증권 'Kiwoom Healthcare 종합정리' 주간 PDF(D:\Download) 1페이지 '향후 한달 이벤트 달력' → data/kiwoom.json (좌표로 격자 복원 · 여러 호 중복 제거 · 유형은 키워드 · 회사는 companies.json 매칭). **1~2주에 한 번** 새 PDF 받은 뒤 실행 → commit·push(이전 호와 중복은 자동 제거). 페이지는 Hub·Bloomberg 와 합쳐 보여 주고 출처 표기는 없음
  bots/daily/ipo_watch.py    IPO 대기 목록(GCS feed/ipo/watch.json): `list` · `add TICKER "회사명" [--note]` · `remove TICKER` · `check`. daily 봇(v1.34)이 매 실행 때 대기 종목을 야후에 조회해 시세가 생기면 유니버스에 편입(source=IPO, 티커가 안 잡히면 회사명 검색)하고 텔레그램 캡션에 "신규 상장 편입" 한 줄. 재배포 없음
  tools/sync_news_db.py      GCS feed(news·dart·trials·clinical 날짜 파일) → D:\NEWS\news.sqlite (로컬 조회용 사본 · 원할 때 실행 · 새 날짜만 추가)
ews.sqlite (로컬 조회용 사본 · 원할 때 실행 · 새 날짜만 추가)
  tools/backfill_telegram.py 텔레그램 채널 내보내기(HTML) → feed 날짜 파일 생성·GCS 업로드 (2026-10-09 1회 수행 · 4/24~10/8 뉴스·DART)
  db/                        (gitignore) backfill/ 임시 산출물
  tools/send_news.py         수동 뉴스 발송: --url + --headline/--summary-file/--category/--relevance 로 feed/news(페이지) 갱신 또는 신규 추가, --send 붙이면 텔레그램 메인 채널에도 같은 내용 전송(rss 봇 형식). 토큰은 Secret Manager 에서 실행 때 읽음
  tools/deploy_bots.sh       봇 재배포: bash tools/deploy_bots.sh rss dart ctgov daily (이미지 태그는 파일 안에서 올림)
  daily 수동 재실행(텔레그램 없이 feed만): gcloud run jobs execute biopharma-daily-job --region asia-northeast3 --project project-56beef4a-f1e9-4e7b-b7a --args="python,daily.py,--no-telegram" --wait (Dockerfile 이 CMD 만 쓰므로 --args 는 명령 전체를 줘야 한다)
  tools/patch_bots_feed.py   feed_publish 패치(1회성 · 적용 완료)
  bots/                      (gitignore · 각각 별도 로컬 git 저장소 · 원격 없음)
    rss/    rss-monitor-svc    Cloud Run 서비스 · 뉴스 (10분)
    dart/   dart-monitor-svc   Cloud Run 서비스 · DART 공시 (평일 07~19시 매분)
    ctgov/  ctgov-monitor-svc  Cloud Run 서비스 · ClinicalTrials.gov 변경 (매일 08:00 KST) · 미국 스폰서 = us_universe.py(tickers.csv − 의료기기·도구·진단·CRO) → us_sponsors.json, 유니버스 바뀌면 재생성 후 재배포(새 스폰서는 첫 실행 때 알림 없이 전체 수집)
    daily/  biopharma-daily-job Cloud Run 잡 · 미국 바이오 마켓 데일리 (화~토 07:30 KST) · macro.py = 글로벌마켓 스냅샷(무료 소스: 야후·FRED CSV·CNN F&G, 크립토 제외)
  archive/biopharmabot-v1/   1세대 GitHub Actions 봇 (중지 · ARCHIVED.md 참고)
```
GCP 프로젝트 `project-56beef4a-f1e9-4e7b-b7a` · 리전 asia-northeast3. 모델: 분류·요약 Haiku 5.5, 심층분석·MoA Sonnet 5.5 (2026-10-08).

## 갱신 루틴
- **매주** Bloomberg raw를 `D:\Catalyst\raw\excel\`에 받은 뒤: `python tools/export_bloomberg.py` → commit·push.
- **분기** 13F 파이프라인(`D:\13F` run_all.py) 끝난 뒤: `python tools/export_hedge.py` → commit·push.
- **수시** Hub catalyst 저술이 바뀌면: `python tools/export_catalyst.py` → commit·push.
- 페이지 수정: `index.html` 고치고 push하면 GitHub Pages 반영. 로컬 확인은 `python -m http.server 8799` (8765는 Hub agentview가 씀). `?feed=local`을 붙이면 `devfeed/`(gitignore)의 feed를 읽는다 — 마켓 개발용 샘플은 bots/daily의 fetch_all+technicals로 만든다.
- 개편 참고: mooboard.xyz · 박종현 coverage(newsbot-3uj.pages.dev/coverage/coverage: 개요 카드·KPI 줄·기계적 수급 표·수급 지도 산점도·뉴스 사이드바·월간 달력) · bio-research.ai.

## 뉴스 DB
- 원본은 GCS `feed/<kind>/<날짜>.json` (삭제 없음 · 텔레그램에 전송된 건만 · 제목·요약·카테고리·중요도·출처·URL). 2026-04-24부터 텔레그램 백필분이 들어 있고(헤드라인·발행시각은 비어 있음), 2026-10-08부터는 봇이 직접 씀. 임상 변경(trials)은 백필 없이 10-09부터.
- 로컬 조회는 `python tools/sync_news_db.py` → `D:\NEWS\news.sqlite` (feed 테이블 + feed_fts 전문검색).
ews.sqlite` (feed 테이블 + feed_fts 전문검색).

## 알아둘 것
- 뉴스·임상의 회사 매칭은 회사명·티커 문자열 기반이라 누락·오탐이 있다. feed에 티커를 넣으면 정확해진다(봇 수정 필요).
- 캘린더 중요도: Hub high/medium/low 그대로, Bloomberg는 Key Catalyst → HIGH, 나머지 → LOW. 기본 필터는 HIGH·MID.
- 예정일이 지났는데 상태가 upcoming인 Hub 행은 「지난 예정일」로 접어 둔다(저술 미갱신분). 45일 넘게 지난 건 export에서 뺀다.
