"""parsed.json + target date -> cfg 원재료(raw) JSON.
구조적 결합(순서/※별지첨부 해소/결석판정)만 수행하고, 띄어쓰기 교정·중복
정리 같은 자연어 판단은 하지 않는다 (사람이 다음 단계에서 검수).
"""
import json
import sys

SECTION_ORDER = ["physical", "cognitive", "health"]


def build(parsed, date, weekday, date_dot):
    people = []
    absent = []
    absent_reason = {}
    for name, p in sorted(parsed.items()):
        rec = p["dates"].get(date)
        if rec is None:
            continue  # 해당 요일에 스케줄이 없는 사람(예: 토요일 미이용자) - 이 날 보고서 대상 아님
        tt = (rec["total_time"] or "").strip()
        if tt == "일정없음":
            continue  # 그날 서비스 대상이 아님 - 급여제공/결석 어느 쪽에도 넣지 않고 전체 인원수에서도 제외
        if tt in ("결석", "미이용") or tt == "":
            absent.append(name)
            phys = (rec["notes"].get("physical") or "").strip()
            if "개인사유" in phys or "개인사정" in phys:
                absent_reason[name] = "개인사정으로 인한 결석"
            else:
                absent_reason[name] = tt or "결석"
            continue
        vital = (rec["vital"] or "").strip() or "측정안됨"
        segments = []
        for cat in SECTION_ORDER:
            val = rec["notes"].get(cat)
            val = (val or "").strip()
            if val == "※별지첨부":
                add = p["addendum"][cat].get(date, "")
                if add:
                    segments.append((cat, add.strip()))
            elif val and val != "특이사항없음" and val != "특이사항 없음":
                segments.append((cat, val))
            elif val in ("특이사항없음", "특이사항 없음"):
                pass  # 그 섹션만 없음, 다른 섹션에서 내용 있을 수 있음
        # 별지의 해당 날짜 항목이 추가로 더 있으면(메인에 ※별지첨부 표시가 없어도) 참고용으로 남김
        people.append({"name": name, "vital": vital, "segments": segments})
    return {
        "date": date_dot,
        "weekday": weekday,
        "people": people,
        "absent": absent,
        "absent_reason": absent_reason,
    }


if __name__ == "__main__":
    parsed = json.load(open(sys.argv[1], encoding="utf-8"))
    date = sys.argv[2]        # '07/10'
    weekday = sys.argv[3]     # '금'
    date_dot = sys.argv[4]    # '2026.07.10'
    out = sys.argv[5]
    result = build(parsed, date, weekday, date_dot)
    json.dump(result, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"people={len(result['people'])} absent={len(result['absent'])} total={len(result['people'])+len(result['absent'])}")
