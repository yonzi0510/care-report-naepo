"""주의 판정 규칙 (일일 카드 자동 형광펜·태그 / 주간 집계 juui-ilban 분류 공용).

기준(하나라도 해당하면 '주의'):
 수축기 ≤100 또는 ≥140, 이완기 ≥90, 체온 ≥37.0,
 목욕거부, 배회·낙상/낙상위험(거동불안·기력저하·앞뒤쏠림), 부종,
 상처/욕창, 설사/묽은변/혈변, 인지저하, 공격적, 통증호소·처치
"""
import re

VITAL_RE = re.compile(r"(\d+)-(\d+)\s*/\s*([\d.]+)")

KEYWORD_GROUPS = [
    ("목욕거부", ["목욕거부", "목욕 거부"]),
    ("낙상위험", ["배회", "낙상", "거동불안", "기력저하", "앞뒤쏠림", "쏠림", "휘청",
                 "균형유지어려워", "균형 유지", "졸음으로", "졸림으로"]),
    ("부종", ["부종", "부어보", "부어 보"]),
    ("상처", ["상처", "욕창", "포진"]),
    ("설사", ["설사", "묽은변", "혈변"]),
    ("인지저하", ["집에가겠다", "집에 가겠다", "보따리", "방금 한 일을 기억", "요일을 착각",
                 "날짜와 요일 개념이 없", "시간을 착각", "지남력"]),
    ("공격적", ["밀치", "소리지름", "소리를지름", "때리려는", "화를 내"]),
    ("통증호소", ["통증", "아프다고", "아프시", "복통", "두통", "요통", "어지럼증"]),
]
# 안약 점안·인공눈물·정기 투약처럼 일상적으로 반복되는 처치는 그 자체만으로는
# 주의 신호가 아니므로(가족 대상 보고서에서 매일 뜨는 게 무의미) 키워드에서 제외했다.
# 통증·낙상 등 실제 이상 신호가 문장에 있을 때만 주의로 잡힌다.


def parse_vital(vital):
    if not vital or vital == "/":
        return None
    m = VITAL_RE.search(vital)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), float(m.group(3))


def judge(vital, note):
    """(is_juui: bool, tag_parts: list[str]) 반환. 참고용 - 실제 배포본 태그는
    사람이 검수한 값을 우선한다."""
    tags = []
    v = parse_vital(vital)
    if v:
        sys_, dia, temp = v
        if sys_ <= 100 or sys_ >= 140:
            tags.append("고혈압" if sys_ >= 140 else "저혈압")
        if dia >= 90:
            tags.append("이완기고혈압")
        if temp >= 37.0:
            tags.append("발열")
    for label, kws in KEYWORD_GROUPS:
        if any(kw in note for kw in kws):
            tags.append(label)
    # 중복 제거, 순서 유지
    seen = set()
    uniq = [t for t in tags if not (t in seen or seen.add(t))]
    return (len(uniq) > 0, uniq)
