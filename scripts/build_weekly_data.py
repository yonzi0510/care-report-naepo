#!/usr/bin/env python3
"""cfg.json + judgments.json -> data/YYYYMMDD.json (주간 집계용 주의/일반 분류).

judgments.json 형식 (사람이 직접 판단해서 작성하는 파일):
{
  "weekday_full": "금요일",
  "juui": {"이름": {"tag": "고혈압·통증호소", "note": "축약된 임상 요약 1문장"}},
  "ilban_notes": {"이름": "축약된 요약 1문장"}
}
juui/ilban_notes에 없는 사람은 없이 처리하지 않는다 - cfg.json의 people과
개수가 맞아야 하며, 누락되면 에러를 낸다 (전원 카드 유지 원칙과 동일하게
주간 집계에서도 아무도 빠뜨리지 않기 위함).

사용법: build_weekly_data.py cfg.json judgments.json out.json
"""
import json
import sys


def fmt_vital(v):
    if not v or "/" not in v:
        return v  # '측정안됨' 등 비수치 값은 그대로 통과
    bp, temp = v.split("/")
    return f"{bp} / {temp}"


def build(cfg, judgments):
    vitals = {n: v for n, v, _ in cfg["people"]}
    juui_map = judgments.get("juui", {})
    ilban_map = judgments.get("ilban_notes", {})

    missing = [n for n in vitals if n not in juui_map and n not in ilban_map]
    if missing:
        raise SystemExit(f"judgments.json에 판정 누락: {missing}")
    overlap = set(juui_map) & set(ilban_map)
    if overlap:
        raise SystemExit(f"juui/ilban에 동시에 있는 이름: {overlap}")

    juui = [
        {"name": n, "vital": fmt_vital(vitals[n]), "note": v["note"], "tag": v["tag"]}
        for n, v in sorted(juui_map.items())
    ]
    ilban = [
        {"name": n, "vital": fmt_vital(vitals[n]), "note": note}
        for n, note in sorted(ilban_map.items())
    ]
    absent = [{"name": n, "reason": r} for n, r in judgments.get("absent_reason_short", {}).items()]
    if len(absent) != len(cfg["absent"]):
        raise SystemExit(f"absent_reason_short 누락: cfg.absent={cfg['absent']}")

    return {
        "date": cfg["date"],
        "weekday": judgments.get("weekday_full", cfg["weekday"]),
        "juui": juui,
        "ilban": ilban,
        "absent": absent,
    }


if __name__ == "__main__":
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
    judgments = json.load(open(sys.argv[2], encoding="utf-8"))
    out = build(cfg, judgments)
    json.dump(out, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("juui:", len(out["juui"]), "ilban:", len(out["ilban"]), "absent:", len(out["absent"]))
