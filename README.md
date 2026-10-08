# Biopharmabot 대시보드

- 공개 페이지: https://biopharmabot.github.io (이 저장소 `index.html` · GitHub Pages · 로그인 없음)
- 실시간 feed: 공개 버킷 `gs://biopharmabot-public/feed/<kind>/latest.json` (`kind` = news · dart · trials · market). 봇이 텔레그램으로 보낸 항목을 `feed_publish()`로 같이 적는다.
- 정적 데이터(`data/`): 이 저장소에 커밋하는 JSON. 헷지펀드 13F(분기) · Hub 카탈리스트 · Bloomberg 카탈리스트(주 1회) · 회사 매핑.

## 탭 (2026-10-08 개편 · mooboard · 박종현 coverage 대시보드 · bio-research.ai 참고)
| 탭 | 내용 | 데이터 |
|---|---|---|
| 개요 | 지난번 본 뒤로 요약 · KPI 줄 · 카드(HIGH 뉴스·공시·임상·이번 주 카탈리스트·마켓 무버·13F 매집×등락·매집 종목 소식·14일 트렌드) | 전부 |
| 뉴스 · DART · 임상 | 봇 feed (필터·검색·이전 날짜 더 보기 · 시간순/종목별 보기). 오른쪽 사이드바: 공시 스트림·회사별 언급·임상 변경. 13F 매집/축소 종목엔 태그 | feed |
| 마켓 | 지수 띠 · KPI(등락 중앙값·급등락·RSI 과열/과매도·52주 고점권·거래량 2배) · Top/Bottom 10 · 전체 307종목 표(1D 양방향 막대·1W·1M·RSI14+1년 백분위·52주 고점比·거래량比·신호 배지·13F) | feed market (daily v1.8부터 기술지표 포함) |
| 글로벌마켓 (개요 바로 다음) | 전체 시장 스냅샷(미국 장 마감 기준 아침). KPI 2줄(S&P·NASDAQ·KOSPI·KOSDAQ / NBI·XBI·DRG·KODEX 바이오·TIGER 헬스케어) · CNN Fear & Greed 게이지+7개 구성지표 · 국가별 블록: 왼쪽 지수(1D/1M/YTD/스파크) 오른쪽 그 국가 전일 섹터 등락(미국 GICS SPDR ETF, 유럽 STOXX600 슈퍼섹터 iShares ETF, 일본 TOPIX-17 ETF, 중국 CSI 300 섹터지수 10개[csindex 공식 JSON·실패 시 ETF 대체], 한국 KOSPI 200 섹터지수 TIGER ETF 11개+KRX 헬스케어; 기타는 지수만) · 금리(야후 국채 + FRED 2Y/10Y/10Y−2Y/연방기금/HY·IG OAS) · 환율·원자재·VIX/MOVE | feed macro (daily v1.12 `macro.py`, `sectors{국가}`·`sector_src` 필드) |
| 헷지펀드 | 13F 분기 동향(신규·순매수·순매도·혼조·청산·M&A소멸, 주식수/비중 기준, 티커 옆 전일 등락) · **수급 지도 산점도**(가로 13F 합산 비중 변화 · 세로 1M/1W/1D/3M 수익률, 사분면 담고·오름 등) · 종목별 시그널 표 · 교차 보유 매트릭스 · 펀드별 상위 보유 | `data/hedge.json` + feed market |
| 캘린더 | Hub 저술 + Bloomberg 캘린더 합본. **월간 달력 격자**(날짜 클릭 → 그 날만) · 이번 주/다음 주(D-n)/월별 · 진행 중(이달·분기·반기) · 이후 · 미정 · 지난 예정일. 소스·지역·중요도·유형 필터. 같은 날짜·유형·티커면 한 건(Hub+BB) | `data/catalyst.json` · `data/bloomberg.json` |
| 트렌드 | 최근 14일 일별 건수·카테고리·출처·회사 상위·카탈리스트 월별/유형/출처 | feed 날짜 파일 + data |
| 회사 모아보기 | 회사명·티커 클릭 또는 상단 「회사·티커 바로가기」 → 마켓·13F·카탈리스트·뉴스·공시·임상을 한 패널에. 딥링크 `#<탭>&co=<티커 또는 회사명>` | 전부 |

## 폴더
```
Biopharmabot/                ← git: Biopharmabot/biopharmabot.github.io (페이지·tools·data 추적)
  index.html                 페이지 소스 (단일 파일 · 외부 라이브러리 없음)
  data/hedge.json            tools/export_hedge.py     ← D:\13F\out\Hedge_fund_<분기>.xlsx (분기 1회)
  data/catalyst.json         tools/export_catalyst.py  ← D:\Hub\hub.sqlite catalyst (upcoming/imminent · 수시)
  data/companies.json        (export_catalyst.py가 같이 씀) Hub company krx·bloomberg + bots/daily/tickers.csv
  data/bloomberg.json        tools/export_bloomberg.py ← D:\Catalyst\raw\excel\Biopharma_catalyst_YYYYMMDD.xlsx 최신 (주 1회)
  tools/deploy_bots.sh       봇 재배포: bash tools/deploy_bots.sh rss dart ctgov daily (이미지 태그는 파일 안에서 올림)
  tools/patch_bots_feed.py   feed_publish 패치(1회성 · 적용 완료)
  bots/                      (gitignore · 각각 별도 로컬 git 저장소 · 원격 없음)
    rss/    rss-monitor-svc    Cloud Run 서비스 · 뉴스 (10분)
    dart/   dart-monitor-svc   Cloud Run 서비스 · DART 공시 (평일 07~19시 매분)
    ctgov/  ctgov-monitor-svc  Cloud Run 서비스 · ClinicalTrials.gov 변경 (매일 08:00 KST)
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

## 알아둘 것
- 뉴스·임상의 회사 매칭은 회사명·티커 문자열 기반이라 누락·오탐이 있다. feed에 티커를 넣으면 정확해진다(봇 수정 필요).
- 캘린더 중요도: Hub high/medium/low 그대로, Bloomberg는 Key Catalyst → HIGH, 나머지 → LOW. 기본 필터는 HIGH·MID.
- 예정일이 지났는데 상태가 upcoming인 Hub 행은 「지난 예정일」로 접어 둔다(저술 미갱신분). 45일 넘게 지난 건 export에서 뺀다.
