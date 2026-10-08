# Biopharmabot 대시보드

- 공개 페이지: https://biopharmabot.github.io (이 저장소 `index.html` · GitHub Pages)
- 데이터: 공개 버킷 `gs://biopharmabot-public/feed/<kind>/latest.json` (`kind` = news · dart · trials · market). 봇이 텔레그램으로 보낸 항목을 `feed_publish()`로 같이 적는다. 페이지는 fetch만 한다(DB·로그인 없음).

## 폴더
```
Biopharmabot/              ← git: Biopharmabot/biopharmabot.github.io (페이지 + tools만 추적)
  index.html               페이지 소스 (뉴스·DART·임상·마켓 탭)
  tools/deploy_bots.sh     봇 재배포: bash tools/deploy_bots.sh rss dart ctgov daily
  tools/patch_bots_feed.py feed_publish 패치(1회성 · 적용 완료)
  bots/                    (gitignore · 각각 별도 git 저장소)
    rss/     rss-monitor-svc   Cloud Run 서비스 · 뉴스 (원격 biopharmabot-rss-cloudrun)
    dart/    dart-monitor-svc  Cloud Run 서비스 · DART 공시
    ctgov/   ctgov-monitor-svc Cloud Run 서비스 · ClinicalTrials.gov 변경 (daily/tickers.csv를 읽음)
    daily/   biopharma-daily-job Cloud Run 잡 · 미국 바이오 마켓 데일리 (deploy.sh 자체 보유)
  archive/biopharmabot-v1/ 1세대 GitHub Actions 봇 (중지 · ARCHIVED.md 참고)
```
2026-10-08 `C:\biopharmabot*`에서 여기로 이동. GCP 프로젝트 `project-56beef4a-f1e9-4e7b-b7a` · 리전 asia-northeast3.

## 현재 상태 / 할 일
- 봇 4개 소스에 feed_publish 패치는 들어가 있으나 **아직 재배포 전** (배포본 rss v50 · dart v19.14 · ctgov v1.3 · daily v1.6). `bash tools/deploy_bots.sh rss dart ctgov daily` 실행 후 다음 발송부터 feed가 쌓인다.
- 각 봇 폴더의 수정분(main.py 등)은 아직 커밋 전. 배포가 확인되면 각 폴더에서 commit·push.
