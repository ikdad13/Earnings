#!/usr/bin/env python3
"""
GATE 4 기계 검증 스크립트 — 실적발표 HTML 대시보드
사용법: python3 validate_report.py <report.html> [--min-size 80000]
모든 항목 PASS 시에만 "PASS" 출력. 하나라도 실패하면 "FAIL" + 사유 출력.
기준선: AMD_Q2_2026_feedback_v6 (134KB, tooltip 240개, 40Q 실데이터)
반례: SiemensEnergy v2 (20KB, 동일 좌표 2점 직선 6개 복붙)
"""
import sys, re, os
from collections import Counter

def main():
    if len(sys.argv) < 2:
        print("usage: validate_report.py <report.html> [--min-size N]"); sys.exit(2)
    path = sys.argv[1]
    min_size = 80000
    if "--min-size" in sys.argv:
        min_size = int(sys.argv[sys.argv.index("--min-size") + 1])

    html = open(path, encoding="utf-8").read()
    text = re.sub(r"<[^>]+>", " ", html)
    fails, warns = [], []

    # 1. 파일 크기 — 요약 래퍼/간이 리포트 감지
    size = os.path.getsize(path)
    if size < min_size:
        fails.append(f"파일 크기 {size:,}B < 기준 {min_size:,}B → 간이 리포트 의심. PHASE 2/3로 복귀.")

    # 2. 필수 섹션 10개
    required = ["결론", "KPI", "Consensus|컨센서스", "Segment|사업부", "차트|Chart",
                "Prepared|해석", "Q&A|QnA", "이전 4개|prior", "리스크|Risk", "Source|출처|appendix"]
    for pat in required:
        if not re.search(pat, html, re.I):
            fails.append(f"필수 섹션 누락 의심: /{pat}/")

    # 3. 차트 데이터 밀도 — 2점짜리 가짜 차트 감지
    polylines = re.findall(r'<polyline[^>]*points="([^"]+)"', html)
    paths = re.findall(r'<path[^>]*\bd="([^"]+)"', html)
    series_pts = []
    for p in polylines:
        series_pts.append(len(p.replace(",", " ").split()) // 2)
    for d in paths:
        n = len(re.findall(r"[LlMm]\s*[-\d.]+[ ,][-\d.]+", d))
        if n >= 2: series_pts.append(n)
    source_limited = bool(re.search(r'data-source-limited-series=["\']true["\']', html, re.I))
    if not series_pts:
        fails.append("SVG 시계열 차트(polyline/path)가 없음.")
    else:
        # 원칙은 20Q+. 다만 신규/분리상장 등으로 20Q 자체가 없고 evidence를 명시한 경우 12Q+ 예외 허용.
        thin_floor = 12 if source_limited else 12
        thin = [n for n in series_pts if n < thin_floor]
        if thin:
            fails.append(f"데이터 포인트 {thin_floor}개 미만 시리즈 {len(thin)}개 발견 (포인트 수: {sorted(set(thin))}). "
                         "실데이터 미확보 상태로 차트 생성 → 최악 위반.")
        if max(series_pts) < 20:
            if source_limited and re.search(r'source-limited\s+quarters\s*=\s*\d+', text, re.I) \
               and re.search(r'StockAnalysis|FinChat|Fiscal\.ai|SEC|IR|Company Not Found|500|timeout|20Q|40Q', text, re.I):
                warns.append(f"source-limited 예외 적용: 최대 {max(series_pts)}개 포인트. Source appendix 증거 확인 필요.")
            else:
                fails.append(f"20개 이상 포인트를 가진 메인 시계열이 하나도 없음 (최대 {max(series_pts)}개). "
                             "20Q 미수집 의심 → PHASE 2 복귀. 예외 시 data-source-limited-series와 증거 필요.")
        mid = [n for n in series_pts if 12 <= n < 16]
        if mid:
            warns.append(f"포인트 12~15개 시리즈 {len(mid)}개 — source-limited 예외 또는 YoY 파생인지 확인.")
        # 동일 좌표 복붙 감지 (Siemens 반례 패턴)
        dup = [(pts, c) for pts, c in Counter(polylines).items() if c > 1]
        if dup:
            fails.append(f"동일 좌표 polyline이 {sum(c for _, c in dup)}회 반복 → 서로 다른 지표에 같은 선 복붙 의심.")

    # 4. tooltip 밀도
    tooltips = len(re.findall(r"<title>", html)) - 1  # 문서 title 제외
    if tooltips < 40:
        fails.append(f"hover tooltip(title) {tooltips}개 < 40개. 포인트별 tooltip 미구현.")

    # 5. 축/틱 존재
    if len(re.findall(r"<line", html)) < 8:
        fails.append("축/tick용 <line> 요소 부족 → 축 없는 floating chart 의심.")
    if not re.search(r"[1-4]Q\d{2}|Q[1-4]\s?20\d{2}|Q[1-4] FY", html):
        fails.append("분기 tick 라벨(3Q16 / Q3 2026 형식) 미발견.")

    # 6. 컨센서스 표 실질성
    if re.search(r"consensus|컨센서스", html, re.I):
        if not re.search(r"(Delta|Δ|차이)", html, re.I) or not re.search(r"(Beat|Miss|Inline|부합)", html, re.I):
            fails.append("컨센서스 섹션에 Delta 또는 Beat/Miss 판정 열 부재 → 빈 껍데기 표 의심.")

    # 7. limitation 증거 4요소
    for m in re.finditer(r"(unavailable|not extracted|미확보|확인 불가|limitation)", text, re.I):
        ctx = text[max(0, m.start()-300):m.end()+300]
        if not re.search(r"https?://|400|403|404|timeout|fetch", ctx, re.I):
            warns.append(f"증거(URL/에러코드) 없는 limitation 문구 발견: …{text[m.start():m.start()+60].strip()}…")

    # 8. 금지 패턴
    if "file://" in html:
        fails.append("file:// 링크 발견 → Telegram/모바일에서 접근 불가.")
    if re.search(r"issue map", html, re.I) and re.search(r"analyst\s+Q&A|애널리스트\s*문답", html, re.I) \
       and not re.search(r"transcript\s*(미확보|unavailable)", html, re.I):
        warns.append("issue map이 실제 Q&A처럼 제시됐을 가능성. transcript 미확보 명시 확인 요망.")

    # 9. Q&A 상세도 (텍스트 분량 프록시)
    body_chars = len(re.sub(r"\s+", "", text))
    if body_chars < 8000:
        fails.append(f"본문 텍스트 {body_chars:,}자 < 8,000자 → 내용 깊이 부족.")

    print("=" * 60)
    print(f"검증 대상: {path} ({size:,}B, 본문 {body_chars:,}자, tooltip {tooltips}개, "
          f"시리즈 {len(series_pts)}개 포인트분포 {sorted(set(series_pts)) if series_pts else '-'}")
    for w in warns: print(f"⚠ WARN: {w}")
    if fails:
        for f in fails: print(f"✗ FAIL: {f}")
        print("=" * 60); print("FAIL — 완료 선언 금지. 해당 PHASE로 복귀할 것."); sys.exit(1)
    print("=" * 60); print("PASS"); sys.exit(0)

if __name__ == "__main__":
    main()
