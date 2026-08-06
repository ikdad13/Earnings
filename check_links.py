#!/usr/bin/env python3
"""허브/리포트 무결성 검사 (푸시 전 게이트 2). repo 루트에서 실행: python3 tools/check_links.py
검사 항목:
 1) index.html 내부 앵커·상대경로 링크 실존
 2) 각 리포트의 허브 역링크 및 내부 앵커
 3) 빌드 스탬프 존재 (<!-- build:YYYYMMDD-rN -->) — index와 모든 리포트
 4) 카운트 정합성, 5) 리포트별 자체 다운로드 링크: 탭/배지 숫자 == 실제 카드 수, 캘린더 날짜별 배지 == 실제 chip 수
모두 정상이면 LINKS OK, 아니면 목록 출력 후 exit 1."""
import re, os, sys, glob
bad = []
idx = open("index.html", encoding="utf-8").read()

# 1) 링크
ids = set(re.findall(r'id="([^"]+)"', idx))
for href in re.findall(r'href="([^"]+)"', idx):
    if href.startswith("#"):
        if href[1:] not in ids: bad.append(f"index.html 깨진 앵커: {href}")
    elif href.startswith("reports/"):
        if not os.path.exists(href): bad.append(f"index.html 없는 파일 링크: {href}")

# 2) 리포트
for f in sorted(glob.glob("reports/*.html")):
    r = open(f, encoding="utf-8").read()
    if '"../index.html"' not in r: bad.append(f"{f}: 허브 역링크 없음")
    rids = set(re.findall(r'id="([^"]+)"', r))
    for a in re.findall(r'href="#([^"]+)"', r):
        if a not in rids: bad.append(f"{f} 깨진 앵커: #{a}")
    if not re.search(r"<!-- build:\d{8}-r\d+ -->", r):
        bad.append(f"{f}: 빌드 스탬프 없음/형식 오류")
    fn = os.path.basename(f)
    if not re.search(rf'<a\b(?=[^>]*\bdownload\b)(?=[^>]*href="{re.escape(fn)}")[^>]*>', r):
        bad.append(f"{f}: 자체 다운로드 링크 없음/파일명 불일치")

# 3) 허브 스탬프
m = re.search(r"<!-- build:(\d{8}-r\d+) -->", idx)
if not m: bad.append("index.html: 빌드 스탬프 없음/형식 오류")
else: print(f"index 스탬프: {m.group(1)}")

# 4) 카운트 정합성, 5) 리포트별 자체 다운로드 링크
n_tcard, n_scard = idx.count('class="tcard"'), idx.count('class="scard"')
for label, n_real in [("발표 완료", n_tcard), ("예정 Setup", n_scard)]:
    for m2 in re.finditer(rf'>{label} <b>(\d+)</b>', idx):
        if int(m2.group(1)) != n_real:
            bad.append(f"탭 카운트 불일치: '{label}' 표기 {m2.group(1)} vs 실제 {n_real}")
for cls, n_real in [("ok", n_tcard), ("up", n_scard)]:
    for m2 in re.finditer(rf'hub-badge b-{cls}">(\d+)<', idx):
        if int(m2.group(1)) != n_real:
            bad.append(f"섹션 배지 카운트 불일치: b-{cls} 표기 {m2.group(1)} vs 실제 {n_real}")
for cell in re.findall(r'<div class="cal-d[^"]*">(.*?)</div>', idx, re.S):
    m2 = re.search(r'cal-cnt">(\d+)</em>', cell)
    if m2:
        chips = len(re.findall(r'class="chip', cell))
        if int(m2.group(1)) != chips:
            day = re.search(r'<span class="n">(\d+)', cell)
            bad.append(f"캘린더 {day.group(1) if day else '?'}일: 배지 {m2.group(1)} vs chip {chips}")

if bad:
    print("\n".join(bad)); print("LINKS FAIL"); sys.exit(1)
print(f"검사 완료: 리포트 {len(glob.glob('reports/*.html'))}개, 카드 {n_tcard}+{n_scard}")
print("LINKS OK")
