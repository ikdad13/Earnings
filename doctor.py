#!/usr/bin/env python3
"""doctor.py — 대시보드 통합 진단·수리 도구. repo 루트에서 실행.

  python3 tools/doctor.py          # 전체 진단 (푸시 전 게이트: 마지막 줄 ALL OK 필수)
  python3 tools/doctor.py --fix    # 기계적 문제 자동 수정 (캘린더 재생성, 카운트 동기화, 스탬프 갱신)

검사 항목:
  [1] 링크·앵커·스탬프·다운로드 링크 (tools/check_links.py 위임)
  [2] 확정본(st-final 배지) 리포트의 품질 게이트 (tools/validate_report.py 위임)
  [3] data/events.json ↔ index.html 캘린더 블록 동기화
  [4] 요약판(st-draft) 백로그 현황 표시 (오류 아님)

--fix가 고치는 것 (파생값만 — 원본 데이터·리포트 본문은 절대 건드리지 않음):
  - 캘린더+아젠다 블록을 events.json에서 재생성 (CAL 마커 사이)
  - 탭/섹션 배지 카운트를 실제 카드 수로 동기화
  - index.html이 수정됐으면 빌드 스탬프 rN+1로 갱신
캘린더를 고치고 싶으면 index.html을 직접 편집하지 말고 data/events.json 수정 후 --fix.
"""
import re, os, sys, json, subprocess, datetime

FIX = "--fix" in sys.argv
DOW = ["월", "화", "수", "목", "금", "토", "일"]  # datetime.weekday() 순서
issues, fixed, notes = [], [], []


# ── 캘린더 생성기 (data/events.json → HTML 블록) ─────────────────────────
def gen_calendar(data):
    year, month = map(int, data["month"].split("-"))
    today = data.get("today", "")
    ev_by_day = {}
    for e in data["events"]:
        d = int(e["date"].split("-")[2])
        ev_by_day[d] = e
    first_wd = datetime.date(year, month, 1).weekday()      # 월=0
    blanks = (first_wd + 1) % 7                              # 일요일 시작 그리드
    ndays = (datetime.date(year + month // 12, month % 12 + 1, 1)
             - datetime.timedelta(days=1)).day
    out = ['<div class="cal">']
    for d in ["일", "월", "화", "수", "목", "금", "토"]:
        out.append(f'<div class="cal-dow{" sun" if d == "일" else ""}">{d}</div>')
    out.extend(['<div class="cal-d blank"></div>'] * blanks)
    for day in range(1, ndays + 1):
        e = ev_by_day.get(day)
        chips = "".join(f'<a class="chip {e["status"]}" href="{it["href"]}">{it["ticker"]}</a>'
                        for it in e["items"]) if e else ""
        cnt = len(e["items"]) if e else 0
        is_today = today == f"{year}-{month:02d}-{day:02d}"
        kls = "cal-d" + (" ev" if chips else "") + (" today" if is_today else "")
        badge = f'<em class="cal-cnt">{cnt}</em>' if cnt else ""
        out.append(f'<div class="{kls}"><span class="n">{day}{badge}</span>{chips}</div>')
    out.append("</div>")
    out.append('<div class="agenda">')
    for e in data["events"]:
        y2, m2, d2 = map(int, e["date"].split("-"))
        wd = DOW[datetime.date(y2, m2, d2).weekday()]
        chips = "".join(f'<a class="chip {e["status"]}" href="{it["href"]}">{it["ticker"]}</a>'
                        for it in e["items"])
        out.append(f'<div class="agenda-row"><div class="agenda-when">{m2}/{d2} ({wd})'
                   f'<small>{e["label"]}</small></div><div>{chips}</div></div>')
    out.append("</div>")
    return "".join(out)


# ── [1] 링크·구조 게이트 ────────────────────────────────────────────────
r = subprocess.run([sys.executable, "tools/check_links.py"], capture_output=True, text=True)
if r.returncode != 0:
    issues.append("[1] check_links FAIL:\n" + r.stdout.strip())
else:
    notes.append("[1] 링크/앵커/스탬프/다운로드: OK")

idx = open("index.html", encoding="utf-8").read()

# ── [2] 확정본 품질 게이트 (허브 배지 기준으로 확정본만 검사) ────────────
finals, drafts = [], []
for card in re.findall(r'<div class="tcard">.*?</div>', idx, re.S):  # 카드 내 중첩 div 없음 전제(check_links가 구조 보증)
    href = re.search(r'href="(reports/[^"]+)"', card)
    if not href:
        continue
    (finals if "st-final" in card else drafts).append(href.group(1))
for f in finals:
    v = subprocess.run([sys.executable, "tools/validate_report.py", f],
                       capture_output=True, text=True)
    if v.returncode != 0:
        issues.append(f"[2] 확정본 validate FAIL: {f}\n" +
                      "\n".join(l for l in v.stdout.splitlines() if l.startswith("✗")))
    else:
        notes.append(f"[2] 확정본 validate PASS: {f}")

# ── [3] events.json ↔ 캘린더 동기화 ─────────────────────────────────────
CAL_RE = re.compile(r"(<!-- CAL:BEGIN -->)(.*?)(<!-- CAL:END -->)", re.S)
if not os.path.exists("data/events.json"):
    issues.append("[3] data/events.json 없음")
elif not CAL_RE.search(idx):
    issues.append("[3] index.html에 CAL:BEGIN/END 마커 없음")
else:
    data = json.load(open("data/events.json", encoding="utf-8"))
    want = gen_calendar(data)
    cur = CAL_RE.search(idx).group(2)
    if cur.strip() != want.strip():
        if FIX:
            idx = CAL_RE.sub(lambda m: m.group(1) + want + m.group(3), idx)
            fixed.append("[3] 캘린더/아젠다 블록을 events.json 기준으로 재생성")
        else:
            issues.append("[3] 캘린더가 events.json과 불일치 — `--fix`로 재생성하거나 JSON을 확인")
    else:
        notes.append("[3] 캘린더 ↔ events.json: 동기화됨")

# ── 카운트 자동 동기화 (--fix) ──────────────────────────────────────────
if FIX:
    n_t, n_s = idx.count('class="tcard"'), idx.count('class="scard"')
    idx2 = re.sub(r'(>발표 완료 <b>)\d+(</b>)', rf'\g<1>{n_t}\g<2>', idx)
    idx2 = re.sub(r'(>예정 Setup <b>)\d+(</b>)', rf'\g<1>{n_s}\g<2>', idx2)
    idx2 = re.sub(r'(hub-badge b-ok">)\d+(<)', rf'\g<1>{n_t}\g<2>', idx2)
    idx2 = re.sub(r'(hub-badge b-up">)\d+(<)', rf'\g<1>{n_s}\g<2>', idx2)
    if idx2 != idx:
        idx = idx2
        fixed.append(f"카운트 동기화 (완료 {n_t} / 예정 {n_s})")

# ── 스탬프 갱신 및 저장 (--fix로 index가 바뀐 경우) ─────────────────────
if FIX and fixed:
    m = re.search(r"<!-- build:(\d{8})-r(\d+) -->", idx)
    if m:
        today_s = datetime.date.today().strftime("%Y%m%d")
        new_r = int(m.group(2)) + 1 if m.group(1) == today_s else 1
        idx = idx.replace(m.group(0), f"<!-- build:{today_s}-r{new_r} -->")
        fixed.append(f"index 스탬프 → build:{today_s}-r{new_r}")
    open("index.html", "w", encoding="utf-8").write(idx)

# ── 리포트 ──────────────────────────────────────────────────────────────
print("=" * 62)
for n in notes:
    print("✓", n)
if drafts:
    print(f"ℹ [4] 요약판 백로그 {len(drafts)}건 (오류 아님, 재작성 대상):",
          ", ".join(os.path.basename(d) for d in drafts))
for x in fixed:
    print("🔧 FIXED:", x)
for i in issues:
    print("✗", i)
print("=" * 62)
if fixed:
    print("FIXED — 수정을 적용했습니다. 위 ✗ 항목은 수정 전 상태의 진단일 수 있으니")
    print("        재실행하여 ALL OK를 확인한 뒤 커밋하세요.")
    sys.exit(0)
if issues:
    print("FAIL — 위 항목 수리 후 재실행. 자동 수정 가능 항목은 --fix.")
    sys.exit(1)
print("ALL OK")
