# AGENT.md — 실적 대시보드 레포 운영 지시문 (에이전트용)

이 문서는 **룰북 v2의 PHASE 5(전달) 확장**이다. 지위는 다음과 같다:
룰북 v2의 GATE 1~4를 통과하지 않은 산출물은 이 문서의 어떤 절차로도 배포할 수 없다.
이 문서와 룰북이 충돌하면 룰북이 우선한다.

---

## 1. 레포 구조 및 URL

```
earnings-hub/
├── index.html                  ← 허브: 캘린더 · 발표완료 카드 · 예정 Setup · Surprise Board
├── reports/
│   └── {TICKER}_{YYYYMMDD}.html   ← 종목별 리포트 (YYYYMMDD = KST 기준 발표일)
├── data/
│   └── events.json             ← 캘린더의 단일 원천(SSOT). 캘린더 수정은 여기서만
├── tools/
│   ├── doctor.py               ← 통합 진단·수리 (푸시 전 게이트 + --fix 자동수정)
│   ├── validate_report.py      ← 리포트 품질 게이트 (GATE 4)
│   └── check_links.py          ← 링크 무결성 게이트
├── AGENT.md / README.md / .nojekyll
```

공개 URL: `https://<아이디>.github.io/earnings-hub/` (사용자가 북마크한 고정 주소).
푸시 후 반영까지 수십 초~2분 지연이 정상이다.

## 2. 명명 규칙

- 리포트 파일명: `{TICKER}_{YYYYMMDD}.html`. 날짜는 **KST 기준 발표일**이다
  (미국 장마감 후 발표 = KST 다음 날 새벽 → 그 KST 날짜를 쓴다. 회계분기 표기는
  미국/일본/독일이 제각각이라 파일명에 쓰지 않는다. 분기는 리포트 본문 제목에만).
- 같은 발표에 대한 재작성·수정은 **같은 파일명에 덮어쓴다** (버전은 git 히스토리가 관리).
  다음 분기 발표는 새 날짜의 새 파일이다.
- 티커 표기: 미국 상장은 심볼(AMD), 일본은 코드(7011), 유럽은 심볼.거래소(ENR.DE의 경우 `ENR-DE`로
  파일명에서는 점을 하이픈으로 치환).

## 2.5 모든 작업의 시작: 동기화

사용자가 GitHub 웹에서 직접 파일을 고쳤을 수 있다. **모든 작업은
`git pull origin main`으로 시작한다.** pull 없이 작업 후 push가 거부되면
rebase가 아니라 `git pull` 후 재작업한다. 충돌 발생 시 임의로 해소하지 말고
충돌 파일 목록을 사용자에게 보고한다.

## 3. 이벤트별 표준 워크플로우

### A. 예정 setup 추가/갱신 (발표 전)
1. **캘린더는 index.html에서 직접 수정하지 않는다.** `data/events.json`에
   이벤트를 추가/수정하고 `python3 tools/doctor.py --fix`로 재생성한다
   (카운트·아젠다·스탬프 자동 처리). `#upcoming`의 setup 카드(`.scard`,
   id=`up-{TICKER}`)만 SEC:UPCOMING 마커 아래에서 직접 편집한다.
2. setup 카드 필수 항목: KST 예상 시각, 확보된 컨센서스(수치+소스), 미확보 항목.
   컨센서스 미확보 시 룰북 §14의 증거 4요소 없이 "미확보"라고 쓰지 않는다.
3. 게이트 → 커밋: `setup(TICKER): consensus EPS $X.XX 반영` 형식.

### B. 발표 완료 → 최종 리포트 게시 (핵심 워크플로우)
1. **룰북 v2 PHASE 1~4 수행. GATE 1~3 증거 블록을 채팅에 출력했고,
   `python3 tools/validate_report.py <신규 리포트>` 가 PASS인 경우에만 계속한다.**
2. `reports/{TICKER}_{YYYYMMDD}.html` 추가. 상단 backbar에는 허브 역링크와
   자기 파일명을 가리키는 `download` 링크를 포함한다(check_links가 검증).
3. index.html 동기 수정 (한 커밋에 함께):
   - 캘린더: `data/events.json`에서 해당 이벤트 status `next → done`, href를
     `reports/...` 파일로 전환 후 doctor --fix로 재생성
   - `#upcoming`: 해당 setup 카드 제거
   - `#done`: 카드 추가(결론 2~3문장은 리포트의 "결론 먼저"에서 그대로 발췌, 새 문장 창작 금지),
     배지 `st-final`, 카운트 갱신. 카드는 `<div class="tcard">` 구조이며 하단 `.acts`에
     "리포트 열기 →"(페이지)와 "다운로드 ↓"(`download` 속성) 두 링크를 모두 넣는다
     (카드 전체를 `<a>`로 감싸지 않는다 — 중첩 앵커 금지)
   - `#surprise`: 행 추가(핵심 수치/판정/코멘트 — 리포트 결론에서만 추출)
4. 게이트 → **원자적 커밋 1건**: `report(TICKER): {YYYYMMDD} final (validate PASS)`.
   리포트 파일과 index.html 수정을 커밋 2개로 쪼개지 않는다
   (쪼개면 중간 상태에서 허브에 깨진 링크가 배포된다).

### C. 확정본 수정 (fix)
- **diff-only.** 파일 재생성 금지. 수정 전후로
  `wc -c`, `grep -c "<h2>"`, `grep -c "<title>"` 3개 지표를 출력하고,
  하나라도 감소하면(사용자가 명시적으로 삭제 지시한 경우 제외) 커밋하지 않고 원복한다.
- 커밋: `fix(TICKER): 수정 내용 요약`.

### D. 월 전환
1. 새 달 1일: `data/events.json`의 `month`를 새 달로 바꾸고 `events`를 새 달
   일정으로 교체 → `doctor --fix` (그리드·요일 시작·아젠다 자동 재계산).
2. 지난 달 발표완료 카드는 `#done`에 누적 유지한다(월 라벨 소제목으로 구분).
   리포트 파일은 어떤 경우에도 삭제·이동하지 않는다.
3. 커밋: `hub: calendar 2026-09`.

## 3.5 빌드 스탬프 규칙 (캐시 대응)

모든 HTML 파일 첫 줄에는 `<!-- build:YYYYMMDD-rN -->` 스탬프가 있다.
- **파일을 수정하는 모든 커밋에서 해당 파일의 스탬프를 갱신한다** (같은 날 2번째 수정이면 r2).
- index.html을 함께 수정하는 커밋(워크플로우 B 등)에서는 index 스탬프도 갱신한다.
- 이유: GitHub Pages CDN은 최대 10분 캐시를 갖는다. 티커 문자열 grep은 구버전에도
  존재하므로 배포 검증이 되지 않는다. 스탬프만이 "지금 이 커밋"의 배포를 증명한다.

## 4. 커밋 규칙

- 브랜치: `main` 직접 푸시. PR 불필요(단일 운영자).
- 메시지 컨벤션:

| 상황 | 형식 |
| --- | --- |
| 최종 리포트 게시 | `report(TICKER): YYYYMMDD final (validate PASS)` |
| 요약판→최종본 교체 | `report(TICKER): rebuild to final (validate PASS)` |
| 확정본 수정 | `fix(TICKER): ...` |
| setup 추가/갱신 | `setup(TICKER): ...` |
| 캘린더/허브 | `hub: ...` |
| 도구/규칙 | `tools: ...` |

- **금지**: force-push, 히스토리 재작성, reports/ 파일 삭제, `git add .`로 의도 밖 파일 포함.
  잘못 게시했으면 삭제가 아니라 정정 커밋으로 고친다. 직전 커밋 전체를 되돌려야 하면:
  `git revert HEAD --no-edit && git push origin main` (히스토리 보존형 롤백. reset/force-push 금지).
- 커밋 전 `git status`와 `git diff --stat`를 출력하여 변경 파일이 의도와 일치하는지
  확인한 결과를 함께 보고한다.

## 5. 푸시 전 게이트 (순서 고정, 전부 통과해야 push)

```bash
# 1) 통합 게이트 (내부에서 check_links + 확정본 validate + 캘린더 동기화 검사)
python3 tools/doctor.py                               # → 마지막 줄 ALL OK 필수
#    ✗ 항목 중 기계적 문제(캘린더/카운트)는: python3 tools/doctor.py --fix 후 재실행
# 2) 신규 게시 리포트는 개별 validate도 실행 (doctor는 st-final 배지 기준이므로,
#    배지를 달기 전의 신규 파일은 직접 확인해야 한다)
python3 tools/validate_report.py reports/<신규파일>   # → PASS 필수
# 3) 변경 범위 확인
git status && git diff --stat
```
어느 하나라도 실패하면 push하지 않고, 실패 출력 원문을 보고한 뒤 해당 PHASE로 복귀한다.
"이번만 예외"는 없다.

## 6. 푸시 후 검증 및 알림

```bash
git push origin main
sleep 90
STAMP="build:YYYYMMDD-rN"   # 이번 커밋에서 갱신한 스탬프
BUST="?v=$(date +%s)"        # CDN 캐시 우회용 쿼리
curl -sf "https://<아이디>.github.io/earnings-hub/reports/<파일>${BUST}" | grep -q "$STAMP" \
  && echo LIVE_OK || echo LIVE_PENDING
# index.html을 수정했다면 허브도 동일 방식으로 확인
```
티커 문자열이 아니라 **이번 커밋의 스탬프**를 grep해야 한다 — 티커는 구버전 캐시에도
있어서 검증이 무효가 된다(§3.5).
- `LIVE_OK` 확인 후: Telegram으로 ① 요약문 ② 대시보드 URL ③ (룰북 §1 유지)
  단일 HTML `MEDIA:` 첨부를 전송한다. 레포 배포는 Telegram 첨부를 **대체하지 않는다** — 병행이다.
- **두 산출물의 구조는 다르며 서로의 템플릿을 복사하지 않는다:**
  | | 레포(홈페이지) | Telegram 단일본 |
  | --- | --- | --- |
  | 리포트 위치 | `reports/` 개별 파일 링크 | 같은 파일 내 `#report-{TICKER}` 앵커 |
  | 다운로드 버튼 | 카드·backbar에 있음 | **없음** (파일 자체가 다운로드물) |
  | 카운트 게이트 | check_links로 검증 | 수동 확인 |
  단일본에 `reports/...` 상대경로나 `download` 버튼을 넣으면 수신자 기기에서 깨진
  링크가 된다. 단일본은 앵커 구조를 유지한다.
- `LIVE_PENDING`이면 90초 후 1회 재시도, 그래도 실패면 사용자에게 배포 지연을 보고한다.
  완료 선언은 LIVE_OK 이후에만 한다.

## 7. 현재 백로그 (2026-08-06 기준)

`ANET, ALAB, SPCX, TSEM, 4062, 7011` 6종은 **요약판**(validate FAIL, 본문 ~4KB,
20Q 차트·tooltip 없음)으로 게시되어 있고 허브 카드에 "요약판" 배지가 붙어 있다.
각각에 대해 **룰북 v2 PHASE 1부터** 최종본을 재작성하여 같은 파일명으로 교체하고
배지를 `st-final`로 바꾸는 것이 우선 과제다. 교체 순서는 사용자 지시를 따르되,
지시가 없으면 예정 실적이 임박한 종목부터 처리한다.

## 8. 보안

- PAT는 환경변수로만 사용한다. 커밋 내용·로그·리포트 본문·이 문서에 토큰 문자열을
  절대 포함하지 않는다. 푸시 URL에 토큰이 포함된 경우 해당 명령 원문을 채팅에 출력하지 않는다.

## 9. 장애 대응 플레이북 (문제 발생 시 여기부터)

모든 대응의 1단계는 동일하다: `git pull` → `python3 tools/doctor.py`.

| 증상 | 진단 | 조치 |
| --- | --- | --- |
| 사이트가 깨져 보임 / 잘못 배포됨 | `git log --oneline -5`로 원인 커밋 특정 | `git revert <해시> --no-edit && git push` → LIVE 재검증(§6). reset/force-push 금지 |
| doctor [1] FAIL (링크/앵커/스탬프) | 출력의 파일·항목 확인 | 해당 파일만 국소 수정(SEC 마커 활용) → doctor 재실행 |
| doctor [3] FAIL (캘린더 불일치) | events.json이 의도와 맞는지 확인 | 맞으면 `doctor --fix`, 틀리면 JSON 수정 후 `--fix` |
| 카운트/배지 어긋남 | doctor가 자동 검출 | `doctor --fix` (수동 수정 금지 — 파생값) |
| 확정본 내용 오류 | 해당 리포트만 | 워크플로우 C(diff-only) + 스탬프 갱신 → doctor → 커밋 |
| push 거부 (rejected) | 사용자가 직접 수정했을 가능성 | `git pull` → 충돌 시 목록 보고, 임의 해소 금지 |
| LIVE_PENDING 지속 (재시도 후에도) | https://www.githubstatus.com 확인 | Pages 장애면 대기 후 재검증, 아니면 Settings→Pages 설정 확인을 사용자에게 요청 |
| doctor 자체가 크래시 | 파이썬 traceback 원문 보고 | tools/는 에이전트가 임의 수정하지 않는다 — 사용자 승인 후에만 수정, 수정 시 변이 테스트 필수 |

원칙: **진단 없이 수리하지 않는다. 수리 후 반드시 doctor ALL OK를 재확인하고 커밋한다.**
파일 삭제와 히스토리 재작성은 어떤 장애 대응에서도 금지된다.
