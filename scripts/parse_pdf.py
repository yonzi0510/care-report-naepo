"""PDF(급여제공기록지 주간표) -> 사람별/날짜별 구조화 JSON.

pdfplumber의 extract_table()로 페이지를 표 그리드로 읽어, 6개 날짜 열이
나란히 있는 메인 페이지와, 날짜별 특이사항이 길 때 붙는 별지 페이지를
사람 단위로 묶는다.
"""
import json
import re
import sys
import pdfplumber

DATE_COL_RE = re.compile(r"^\d{2}/\d{2}\(.\)$")

GROUP_NAMES = {
    "신체활동지원": "physical",
    "인지관리및의사소통": "cognitive",
    "건강및간호관리": "health",
    "기능회복훈련": "rehab",  # 결합 대상 아님 (참고용으로만 보관)
}

ADDENDUM_HEADING_MAP = {
    "신체활동지원": "physical",
    "인지관리": "cognitive",
    "건강": "health",
    "간호관리": "health",
}


def norm(s):
    if s is None:
        return ""
    return s.replace("\n", "").strip()


def parse_main_page(text, table):
    lines = text.split("\n")
    name = lines[2].split("생년월일")[0].replace("수급자명", "").strip()
    header_row = None
    for row in table:
        if row and row[0] and norm(row[0]) == "(2026)년월/일":
            header_row = row
            break
    date_cols = {}  # date_str -> column index
    for idx, cell in enumerate(header_row):
        c = norm(cell)
        if DATE_COL_RE.match(c):
            date_cols[idx] = c[:5]  # '07/06'

    dates = {d: {"total_time": None, "vital": None,
                 "notes": {"physical": None, "cognitive": None, "health": None, "rehab": None}}
             for d in date_cols.values()}

    current_group = None
    for row in table:
        col0, col1 = row[0], row[1]
        if col0 and norm(col0) in GROUP_NAMES:
            current_group = GROUP_NAMES[norm(col0)]
        label = norm(col1) if col1 else norm(col0)
        if not label:
            continue
        if label == "총시간":
            for idx, d in date_cols.items():
                dates[d]["total_time"] = norm(row[idx]) if idx < len(row) else None
        elif label == "혈압/체온":
            for idx, d in date_cols.items():
                dates[d]["vital"] = norm(row[idx]) if idx < len(row) else None
        elif label == "특이사항" and current_group in ("physical", "cognitive", "health", "rehab"):
            for idx, d in date_cols.items():
                val = row[idx] if idx < len(row) else None
                # 메인 페이지 특이사항 칸은 폭이 좁아 pdfplumber가 단어 중간에서도
                # 고정폭으로 줄바꿈한다 (줄바꿈=공백 아님) - 공백 없이 이어붙인다.
                dates[d]["notes"][current_group] = val.replace("\n", "").strip() if val else None

    return name, dates


def parse_addendum_page(page):
    text = page.extract_text() or ""
    name = text.split("\n")[0].split("생년월일")[0].replace("수급자명", "").strip()
    result = {"physical": {}, "cognitive": {}, "health": {}, "rehab": {}}
    tables = page.find_tables()
    # 헤딩 텍스트와 표 bbox의 top 좌표로 어느 헤딩에 속하는지 매칭
    words = page.extract_words()
    headings = []  # (top, category)
    full_lines = text.split("\n")
    for w in words:
        pass
    # 헤딩 줄을 찾아 category 결정 + 그 헤딩 다음에 오는 표를 매칭
    heading_positions = []
    for obj in page.extract_text_lines() if hasattr(page, "extract_text_lines") else []:
        pass
    # 더 단순한 방법: 페이지 텍스트 라인 순서와 tables 순서가 동일하다고 가정
    # (■<라벨> 특이사항 헤딩이 표 바로 위에 위치)
    heading_lines = [l for l in full_lines if l.startswith("■")]
    cat_order = []
    for h in heading_lines:
        hn = h.replace(" ", "")
        cat = None
        if "신체활동지원" in hn:
            cat = "physical"
        elif "인지관리" in hn:
            cat = "cognitive"
        elif "건강" in hn and "간호관리" in hn:
            cat = "health"
        elif "기능회복훈련" in hn:
            cat = "rehab"
        cat_order.append(cat)

    data_tables = [t for t in tables if t.extract() and norm(t.extract()[0][0]) == "날짜"]
    for cat, t in zip(cat_order, data_tables):
        if cat is None:
            continue
        for row in t.extract()[1:]:
            if not row or not row[0]:
                continue
            d = row[0].strip()  # '2026.07.09'
            mmdd = d[5:].replace(".", "/")  # '07/09'
            content = (row[1] or "").replace("\n", " ").strip()
            result[cat][mmdd] = content
    return name, result


def parse_pdf(path):
    people = {}
    with pdfplumber.open(path) as pdf:
        pending_addendum_for = None
        for page in pdf.pages:
            text = page.extract_text() or ""
            first_line = text.split("\n", 1)[0]
            if first_line.startswith("■노인장기요양보험법시행규칙"):
                table = page.extract_table()
                name, dates = parse_main_page(text, table)
                people[name] = {"dates": dates, "addendum": {"physical": {}, "cognitive": {}, "health": {}, "rehab": {}}}
                pending_addendum_for = name
            elif "생년월일" in first_line and "성별" in first_line:
                name, add = parse_addendum_page(page)
                if name not in people:
                    raise RuntimeError(f"별지 페이지의 이름이 메인페이지와 매칭되지 않음: {name}")
                for cat in ("physical", "cognitive", "health", "rehab"):
                    people[name]["addendum"][cat].update(add[cat])
            else:
                raise RuntimeError(f"알 수 없는 페이지 형식: {first_line}")
    return people


if __name__ == "__main__":
    src = sys.argv[1]
    out = sys.argv[2]
    people = parse_pdf(src)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(people, f, ensure_ascii=False, indent=1)
    print(f"{len(people)}명 파싱 완료 -> {out}")
