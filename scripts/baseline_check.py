#!/usr/bin/env python3
"""data/*.json 누적 이력으로 사람별 혈압 경향(만성 저/고혈압)을 계산한다.

"특이사항"은 평소와 다른 변화를 뜻하므로, 그 사람에게 항상 나타나는
수축기 저혈압/고혈압 패턴은 매일 반복 태그하지 않는다(docs/daily-report-workflow.md
9번 규칙). 새 날짜를 분류하기 전에 이 스크립트로 만성 패턴 여부를 먼저 확인한다.

사용법: baseline_check.py [data_dir] [min_ratio]
  min_ratio: 이 비율 이상 반복되면 "만성"으로 판단 (기본 0.4 = 40%)
"""
import glob
import json
import re
import sys

VITAL_RE = re.compile(r"(\d+)-(\d+)\s*/\s*([\d.]+)")


def collect(data_dir):
    per_person = {}
    for f in sorted(glob.glob(f"{data_dir}/2026*.json")):
        d = json.load(open(f, encoding="utf-8"))
        for section in ("juui", "ilban"):
            for p in d.get(section, []):
                m = VITAL_RE.search((p.get("vital") or "").replace(" ", ""))
                if not m:
                    continue
                sys_, dia, temp = int(m.group(1)), int(m.group(2)), float(m.group(3))
                per_person.setdefault(p["name"], []).append((sys_, dia, temp))
    return per_person


def chronic_report(data_dir, min_ratio=0.4, min_n=5):
    per_person = collect(data_dir)
    low_bp, high_bp, high_dia = {}, {}, {}
    for name, records in per_person.items():
        n = len(records)
        if n < min_n:
            continue
        sysvals = [r[0] for r in records]
        diavals = [r[1] for r in records]
        low_ratio = sum(1 for s in sysvals if s <= 100) / n
        high_ratio = sum(1 for s in sysvals if s >= 140) / n
        dia_ratio = sum(1 for d in diavals if d >= 90) / n
        if low_ratio >= min_ratio:
            low_bp[name] = (low_ratio, n)
        if high_ratio >= min_ratio:
            high_bp[name] = (high_ratio, n)
        if dia_ratio >= min_ratio:
            high_dia[name] = (dia_ratio, n)
    return low_bp, high_bp, high_dia


if __name__ == "__main__":
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data"
    min_ratio = float(sys.argv[2]) if len(sys.argv) > 2 else 0.4
    low_bp, high_bp, high_dia = chronic_report(data_dir, min_ratio)
    print(f"=== 만성 저혈압(수축기 <=100, {min_ratio:.0%}+ 반복) ===")
    for name, (r, n) in sorted(low_bp.items(), key=lambda x: -x[1][0]):
        print(f"  {name}: {r:.0%} ({n}회 중)")
    print(f"=== 만성 고혈압(수축기 >=140, {min_ratio:.0%}+ 반복) ===")
    for name, (r, n) in sorted(high_bp.items(), key=lambda x: -x[1][0]):
        print(f"  {name}: {r:.0%} ({n}회 중)")
    print(f"=== 만성 이완기고혈압(>=90, {min_ratio:.0%}+ 반복) ===")
    for name, (r, n) in sorted(high_dia.items(), key=lambda x: -x[1][0]):
        print(f"  {name}: {r:.0%} ({n}회 중)")
