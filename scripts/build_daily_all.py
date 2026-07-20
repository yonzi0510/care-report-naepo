#!/usr/bin/env python3
"""cfg.json (+ data.json) -> 카드형 HTML (특이사항 보고서 일일 카드).

양식-이식-지침서.md의 정식 양식을 그대로 구현한 공통 엔진(삽교/내포 동일):
 - 상단 "오늘의 태그" 모아보기(태그별 어르신 이름 묶음)
 - 카드별 원자 태그 칩(warn=호박색 / care=파란색)
 - 본문 형광펜(danger=분홍 / info=노랑), 부정문("없이·없음·않") 오검출 가드
 - 발열(체온≥37.0)·혈압 이상 수치 강조

data.json(사람이 검수한 juui 태그)을 같이 주면 그 태그를 원자 단위로 나눠
칩·요약에 쓰고, 없으면 rules.judge() 자동판정으로 대체한다.

사용법: build_daily_all.py cfg.json [data.json] > 보고서.html
"""
import html
import json
import re
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from rules import (  # noqa: E402
    VITAL_RE, judge, parse_vital,
    CHRONIC_LOW_SYS, CHRONIC_HIGH_SYS, CHRONIC_HIGH_DIA,
)

CENTER_TITLE = "내포소망주간보호 — 특이사항 보고서"

# 태그 색 분류: care(파란군)=반복적 처치·의료 연계, 나머지는 warn(호박군) 기본.
CARE_TAG_HINTS = ("물리치료", "병원", "진료", "투약", "안약", "인공눈물", "점안",
                  "드레싱", "처치", "응급", "영양제", "수액")

# 본문 형광펜 트리거. danger=분홍(급성 위험), info=노랑(증상·처치).
DANGER_WORDS = ["낙상", "배회", "부종", "욕창", "포진", "상처", "설사", "묽은변",
                "혈변", "변실수", "대변실수", "소변실수", "골절", "경련", "출혈",
                "밀치", "때리려", "공격", "쏠림", "휘청", "비틀"]
INFO_WORDS = ["통증", "복통", "두통", "요통", "어지럼", "어지러", "물리치료",
              "드레싱", "안약", "인공눈물", "점안", "핫팩", "파스", "연고",
              "병원", "진료", "침침", "눈물", "가려움"]
NEG_MARKERS = ("없", "않", "아니")


def _is_care(tag):
    return any(h in tag for h in CARE_TAG_HINTS)


def _negated(text, end):
    # 키워드 바로 뒤 4글자 안에 부정 표지가 있으면 강조/태그 제외
    return any(m in text[end:end + 4] for m in NEG_MARKERS)


def highlight_note(note):
    esc = html.escape(note)
    pairs = [(w, "danger") for w in DANGER_WORDS] + [(w, "info") for w in INFO_WORDS]
    pairs.sort(key=lambda x: len(x[0]), reverse=True)  # 긴 단어 우선 매칭
    cls_of = {}
    for w, c in pairs:
        cls_of.setdefault(w, c)
    pattern = re.compile("|".join(re.escape(w) for w, _ in pairs))

    def repl(m):
        w = m.group(0)
        if _negated(esc, m.end()):
            return w
        return f'<mark class="hl-{cls_of[w]}">{w}</mark>'

    return pattern.sub(repl, esc)


def vital_html(vital, name=None):
    if not vital or vital in ("/", "측정안됨"):
        return f'<span class="vital">{html.escape(vital or "측정안됨")}</span>'
    v = parse_vital(vital)
    warn = False
    if v:
        sys_, dia, temp = v
        if sys_ <= 100 and name not in CHRONIC_LOW_SYS:
            warn = True
        if sys_ >= 140 and name not in CHRONIC_HIGH_SYS:
            warn = True
        if dia >= 90 and name not in CHRONIC_HIGH_DIA:
            warn = True
        if temp >= 37.0:
            warn = True
    cls = "vital vital-warn" if warn else "vital"
    return f'<span class="{cls}">{html.escape(vital)}</span>'


def person_tags(name, vital, note, verified_tags):
    if verified_tags is not None:
        atoms = []
        for t in verified_tags.get(name, []):
            atoms += [a.strip() for a in t.split("·") if a.strip()]
        return atoms
    return judge(vital, note, name)[1]


def chip(tag):
    cls = "chip chip-care" if _is_care(tag) else "chip chip-warn"
    return f'<span class="{cls}">{html.escape(tag)}</span>'


def person_card(name, vital, note, tags):
    tag_html = ""
    if tags:
        tag_html = '<div class="chips">' + "".join(chip(t) for t in tags) + "</div>"
    return f'''<article class="card">
  <header><span class="name">{html.escape(name)}</span>{vital_html(vital, name)}</header>
  {tag_html}
  <p class="note">{highlight_note(note)}</p>
</article>'''


def tag_summary(people_tags):
    tag_names = {}
    for name, atoms in people_tags:
        for a in atoms:
            tag_names.setdefault(a, [])
            if name not in tag_names[a]:
                tag_names[a].append(name)
    if not tag_names:
        return ""
    rows = ""
    for a in sorted(tag_names):  # 가나다순
        names = " · ".join(html.escape(n) for n in tag_names[a])
        rows += f'<div class="trow">{chip(a)}<span class="tnames">{names}</span></div>'
    return f'<div class="tagbox"><div class="tagbox-h">오늘의 태그</div>{rows}</div>'


STYLE = '''<style>
.rpt{font-size:14px;line-height:1.7;color:var(--color-text-primary);}
.rpt-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin:6px 0 4px;}
.rpt-title{font-size:17px;font-weight:800;}
.rpt-date{font-size:14px;color:var(--color-text-secondary);white-space:nowrap;}
.rpt-sub{font-size:12.5px;color:var(--color-text-tertiary);margin-bottom:14px;}
.rpt-absent{font-size:12.5px;color:var(--color-text-secondary);background:var(--color-background-info);
  border-radius:10px;padding:9px 13px;margin-bottom:16px;}
.tagbox{background:#f4f2ec;border:1px solid #e7e3d8;border-radius:14px;padding:14px 16px;margin-bottom:16px;}
.tagbox-h{font-weight:700;font-size:14px;margin-bottom:9px;}
.trow{display:flex;align-items:center;gap:12px;padding:3px 0;}
.tnames{font-size:13.5px;}
.cards{display:flex;flex-direction:column;gap:12px;}
.card{background:#fff;border:1px solid #e5e1d8;border-radius:14px;padding:14px 16px;}
.card header{display:flex;justify-content:space-between;align-items:baseline;gap:10px;margin-bottom:2px;}
.card .name{font-size:16px;font-weight:800;}
.card .vital{font-size:13.5px;color:var(--color-text-secondary);font-variant-numeric:tabular-nums;white-space:nowrap;}
.card .vital-warn{color:#c0392b;font-weight:800;}
.card .chips{display:flex;flex-wrap:wrap;gap:6px;margin:7px 0 2px;}
.chip{font-size:12px;font-weight:700;padding:3px 11px;border-radius:999px;white-space:nowrap;}
.chip-warn{background:#f3e2c7;color:#95702f;}
.chip-care{background:#d9e6f4;color:#3f6699;}
.card .note{margin:7px 0 0;font-size:14px;word-break:keep-all;}
mark.hl-danger{background:#f9d6d3;color:inherit;border-radius:4px;padding:0 3px;}
mark.hl-info{background:#fbf0c1;color:inherit;border-radius:4px;padding:0 3px;}
</style>'''


def build(cfg, data=None):
    verified_tags = None
    if data is not None:
        verified_tags = {p["name"]: [p["tag"]] for p in data.get("juui", [])}

    people_tags, cards = [], []
    for n, v, note in cfg["people"]:
        tags = person_tags(n, v, note, verified_tags)
        people_tags.append((n, tags))
        cards.append(person_card(n, v, note, tags))

    prov_n = len(cfg["people"])
    absent_n = len(cfg.get("absent", []))
    total = prov_n + absent_n
    sub = (f"※ 3-6 급여제공리포트 PDF 출력본 기준 "
           f"(전체 {total}명 · 급여제공 {prov_n}명 · 결석 {absent_n}명)")
    absent_html = ""
    if cfg.get("absent"):
        gs = cfg.get("gyeolseok") or " · ".join(cfg["absent"])
        absent_html = f'<div class="rpt-absent">🚫 결석: {html.escape(gs)}</div>'

    return f'''{STYLE}
<div class="rpt">
  <div class="rpt-head">
    <div class="rpt-title">{html.escape(CENTER_TITLE)}</div>
    <div class="rpt-date">{html.escape(cfg["date"])} ({html.escape(cfg["weekday"])})</div>
  </div>
  <div class="rpt-sub">{html.escape(sub)}</div>
  {absent_html}
  {tag_summary(people_tags)}
  <div class="cards">
{chr(10).join(cards)}
  </div>
</div>'''


if __name__ == "__main__":
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
    data = json.load(open(sys.argv[2], encoding="utf-8")) if len(sys.argv) > 2 else None
    sys.stdout.write(build(cfg, data))
