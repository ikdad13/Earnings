# 실적발표 통합 대시보드 — GitHub Pages 세팅 가이드 (최초 1회, 사람용)

이 폴더가 레포 초기 커밋 전체입니다. 아래 절차를 마치면 고정 URL을 북마크할 수 있고,
이후 갱신은 에이전트가 `AGENT.md`에 따라 수행합니다.

## 0. 공개 범위 먼저 결정 (중요)

| 선택지 | 비용 | 주의 |
| --- | --- | --- |
| Public 레포 + GitHub Pages | 무료 | **URL을 아는 누구나 열람 가능.** 리포트 내용 공개에 문제 없을 때만 |
| Private 레포 + GitHub Pages | GitHub Pro 필요 | 소스 레포만 비공개. **게시된 사이트는 여전히 공개**이며, 사이트 자체를 비공개(로그인 요구)로 만들려면 organization + Enterprise Cloud가 필요 (출처: docs.github.com/en/get-started/learning-about-github/githubs-plans) |
| Private 레포 + Cloudflare Pages + Access | 무료 | Cloudflare가 서빙하고 Zero Trust Access로 이메일 로그인 잠금 가능(무료 티어 소규모 사용자 지원). 개인용으로 사이트 접근 제어까지 원하면 이 조합이 유일한 무료안 (출처: developers.cloudflare.com/cloudflare-one, community.cloudflare.com/t/393299) |

투자 리포트 특성상 **Private + Cloudflare Pages(Access 잠금)** 조합을 권장하지만(사이트 접근 제어가 되는 유일한 무료안),
가장 간단한 것은 Public + GitHub Pages입니다. 아래는 GitHub Pages 기준입니다.

## 1. 레포 생성 및 초기 업로드

브라우저만으로:
1. github.com → **New repository** → 이름 예: `earnings-hub` → Public/Private 선택 → Create
2. **uploading an existing file** 클릭 → 이 폴더의 내용 전체(index.html, reports/, tools/, AGENT.md, .nojekyll)를 드래그 → Commit

또는 터미널로:
```bash
cd earnings-hub
git init && git add -A && git commit -m "init: earnings hub skeleton (2026-08-06)"
git branch -M main
git remote add origin https://github.com/<아이디>/earnings-hub.git
git push -u origin main
```

## 2. Pages 활성화

레포 → **Settings → Pages** → Source: **Deploy from a branch** → Branch: `main`, 폴더 `/ (root)` → Save.
1~2분 후 상단에 URL이 표시됩니다:
```
https://<아이디>.github.io/earnings-hub/
```
이 주소를 **북마크**하세요. 이후 에이전트가 푸시할 때마다 같은 주소에서 최신 상태가 보입니다
(반영까지 보통 수십 초~2분).

## 3. 에이전트용 토큰 발급 (Fine-grained PAT)

1. GitHub 우측 상단 프로필 → **Settings → Developer settings → Fine-grained tokens → Generate new token**
2. 설정:
   - Repository access: **Only select repositories** → `earnings-hub`만
   - Permissions → Repository permissions → **Contents: Read and write** (그 외 전부 No access)
   - Expiration: 90일 권장(만료 시 재발급)
3. 생성된 `github_pat_...` 토큰을 에이전트의 비밀 저장소(환경변수 등)에 넣습니다.
   **채팅 로그·룰북·레포 안에 토큰을 절대 넣지 마세요.**

## 4. 에이전트 초기 설정 (에이전트 환경에서 1회 실행)

```bash
git clone https://<아이디>:${GITHUB_PAT}@github.com/<아이디>/earnings-hub.git
cd earnings-hub
git config user.name  "earnings-agent"
git config user.email "agent@local"
```
주의: 위 방식은 토큰이 `.git/config`에 평문 저장됩니다. 에이전트 실행 환경이 단독
사용 컨테이너가 아니라면 `git config credential.helper` 또는 환경변수 주입 방식을 쓰세요.

## 5. 운영

- 에이전트: 이후 모든 갱신은 레포 루트의 **AGENT.md** 절차를 따릅니다
  (룰북 v2 게이트 통과 → 배포 게이트 → 원자적 커밋 → 푸시 → 라이브 검증 → Telegram 알림).
- 사용자 검수: 언제든 레포를 받아 아래 두 줄로 상태를 확인할 수 있습니다.
  ```bash
  python3 tools/check_links.py                      # 링크 무결성
  python3 tools/validate_report.py reports/<파일>    # 리포트 품질 게이트
  ```

## 문제가 생겼을 때 / 직접 고치고 싶을 때

- **한 줄 진단**: 레포 루트에서 `python3 tools/doctor.py` — 링크·품질·캘린더 동기화를
  한 번에 검사하고 마지막 줄에 ALL OK / FAIL을 출력합니다.
- **기계적 문제 자동 수리**: `python3 tools/doctor.py --fix` — 캘린더 재생성,
  카운트 동기화, 스탬프 갱신까지 자동 처리합니다.
- **캘린더를 직접 고치고 싶으면** index.html이 아니라 `data/events.json`을 수정한 뒤
  `--fix`를 실행하세요. 날짜·티커·상태(done/next)만 만지면 나머지는 도구가 만듭니다.
- **본문을 직접 고치고 싶으면** GitHub 웹에서 해당 파일을 편집·커밋해도 됩니다.
  에이전트는 작업 시작 시 항상 `git pull`을 하므로 수정이 유실되지 않습니다.
- **배포가 깨졌으면** 에이전트에게 "AGENT.md §9 플레이북대로 복구해"라고 지시하면
  원인 커밋 revert부터 라이브 재검증까지 표준 절차로 처리합니다.

## 현재 초기 상태 (2026-08-06 스냅샷)

- `index.html` — 허브: 8월 캘린더 / 발표 완료 카드 / 예정 Setup / Surprise Board
- `reports/AMD_20260804.html` — **확정본** (validate PASS)
- `reports/{ANET,ALAB,SPCX,TSEM,4062,7011}_20260804.html` — **요약판** (validate FAIL, 본문 4KB 수준).
  허브 카드에 "요약판" 배지로 표기되어 있으며, 에이전트 백로그(AGENT.md §7)에 따라
  룰북 PHASE 1부터 최종본으로 재작성 후 교체하는 것이 첫 과제입니다.
