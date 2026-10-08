#!/usr/bin/env bash
# 봇 재배포 (feed_publish 패치 반영). 사용: bash tools/deploy_bots.sh rss|dart|ctgov|daily [...]
# 이미지 태그는 현재 배포본 +1. 서비스/잡 설정(환경변수·시크릿·스케줄)은 건드리지 않고 이미지만 바꾼다.
# 봇 소스는 이 저장소의 bots/<name>/ (각각 별도 git 저장소).
set -euo pipefail
BOTS="$(cd "$(dirname "$0")/../bots" && pwd)"
P=project-56beef4a-f1e9-4e7b-b7a; R=asia-northeast3; REG=asia-northeast3-docker.pkg.dev/$P/biopharmabot
for t in "$@"; do case $t in
  rss)   IMG=$REG/rss-monitor:v55;      gcloud builds submit --tag $IMG "$BOTS/rss"   --project $P --quiet; gcloud run services update rss-monitor-svc   --image $IMG --region $R --project $P --quiet ;;
  dart)  IMG=$REG/dart-monitor:v19.20;  gcloud builds submit --tag $IMG "$BOTS/dart"  --project $P --quiet; gcloud run services update dart-monitor-svc  --image $IMG --region $R --project $P --quiet ;;
  ctgov) IMG=$REG/ctgov-monitor:v1.6;   gcloud builds submit --tag $IMG "$BOTS/ctgov" --project $P --quiet; gcloud run services update ctgov-monitor-svc --image $IMG --region $R --project $P --quiet ;;
  daily) IMG=$REG/biopharma-daily:v1.10; gcloud builds submit --tag $IMG "$BOTS/daily" --project $P --quiet; gcloud run jobs update biopharma-daily-job --image $IMG --region $R --project $P --quiet ;;
  *) echo "unknown $t"; exit 1;; esac; echo "== $t 배포 완료 → $IMG"; done
