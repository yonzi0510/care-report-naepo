#!/usr/bin/env python3
"""data/YYYYMMDD.json (하루치, 여러 장) -> 주간 카드형 HTML.

사용법: build_weekly_all.py W주간라벨 data1.json data2.json ... > 주간보고서.html
(날짜순으로 넘긴다)
"""
import html
import json
import sys


def build(week_label, days):
    # days: [(date_str, weekday, juui[], ilban[], absent[])]
    juui_by_person = {}
    absent_by_person = {}
    total_juui = total_ilban = total_absent = 0
    for date, weekday, juui, ilban, absent in days:
        total_juui += len(juui)
        total_ilban += len(ilban)
        total_absent += len(absent)
        for p in juui:
            juui_by_person.setdefault(p["name"], []).append((date, weekday, p["vital"], p["tag"], p["note"]))
        for a in absent:
            absent_by_person.setdefault(a["name"], []).append((date, weekday, a.get("reason", "")))

    overview_rows = "".join(
        f'<tr><td>{html.escape(date)}({weekday})</td><td>{len(juui)}</td><td>{len(ilban)}</td><td>{len(absent)}</td></tr>'
        for date, weekday, juui, ilban, absent in days
    )

    absent_cards = ""
    for name in sorted(absent_by_person):
        entries = absent_by_person[name]
        days_str = ", ".join(f"{d}({w}·{r})" if r else f"{d}({w})" for d, w, r in entries)
        absent_cards += f'<div class="arow"><span class="name">{html.escape(name)}</span><span class="cnt">{len(entries)}일</span><span class="days">{html.escape(days_str)}</span></div>'

    juui_cards = ""
    for name in sorted(juui_by_person):
        entries = juui_by_person[name]
        rows = "".join(
            f'<li><span class="d">{html.escape(date)}({weekday})</span> '
            f'<span class="v">{html.escape(vital)}</span> '
            f'<span class="chip">{html.escape(tag)}</span>'
            f'<p class="n">{html.escape(note)}</p></li>'
            for date, weekday, vital, tag, note in entries
        )
        juui_cards += f'''<article class="pcard">
  <header><span class="name">{html.escape(name)}</span><span class="freq">{len(entries)}회</span></header>
  <ul>{rows}</ul>
</article>'''

    return f'''<style>
.wk-wrap{{font-size:14px;line-height:1.6;}}
.wk-head{{margin:10px 0 16px;}}
.wk-head h2{{font-size:16px;margin:0 0 4px;color:var(--color-text-primary);}}
.wk-head .sub{{color:var(--color-text-secondary);font-size:12.5px;}}
.wk-section{{margin:20px 0;}}
.wk-section h3{{font-size:13.5px;color:var(--color-text-primary);margin:0 0 8px;}}
table.wk-table{{width:100%;border-collapse:collapse;font-size:12.5px;}}
table.wk-table th,table.wk-table td{{padding:6px 8px;border-bottom:1px solid #e0ddd5;text-align:center;}}
table.wk-table th{{color:var(--color-text-secondary);font-weight:600;}}
.arow{{display:flex;gap:10px;align-items:baseline;padding:6px 0;border-bottom:1px solid #ece9e1;font-size:12.5px;}}
.arow .name{{font-weight:700;min-width:56px;color:var(--color-text-primary);}}
.arow .cnt{{color:#b3261e;font-weight:600;min-width:34px;}}
.arow .days{{color:var(--color-text-tertiary);}}
.wk-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px;}}
.pcard{{border:1px solid #eab8b6;background:var(--color-background-danger);border-radius:10px;padding:10px 14px;}}
.pcard header{{display:flex;justify-content:space-between;margin-bottom:6px;}}
.pcard .name{{font-weight:700;font-size:13.5px;color:var(--color-text-primary);}}
.pcard .freq{{font-size:11.5px;color:#b3261e;font-weight:700;}}
.pcard ul{{list-style:none;margin:0;padding:0;}}
.pcard li{{padding:6px 0;border-top:1px dashed #ecb9b7;}}
.pcard li:first-child{{border-top:none;}}
.pcard .d{{font-size:11.5px;color:var(--color-text-secondary);font-weight:600;}}
.pcard .v{{font-size:11.5px;color:var(--color-text-secondary);}}
.pcard .chip{{font-size:10.5px;padding:1px 7px;border-radius:999px;background:#b3261e;color:#fff;font-weight:600;margin-left:4px;}}
.pcard .n{{margin:3px 0 0;font-size:12.5px;color:var(--color-text-primary);}}
</style>
<div class="wk-wrap">
  <div class="wk-head"><h2>{html.escape(week_label)}</h2>
    <div class="sub">주의 연인원 {total_juui} · 일반 연인원 {total_ilban} · 결석 연인원 {total_absent}</div>
  </div>
  <div class="wk-section">
    <h3>요일별 현황</h3>
    <table class="wk-table"><thead><tr><th>날짜</th><th>주의</th><th>일반</th><th>결석</th></tr></thead>
    <tbody>{overview_rows}</tbody></table>
  </div>
  <div class="wk-section">
    <h3>이번주 결석 현황</h3>
    {absent_cards or '<p class="sub">이번주 결석자 없음</p>'}
  </div>
  <div class="wk-section">
    <h3>이번주 주의 인원 ({len(juui_by_person)}명)</h3>
    <div class="wk-grid">{juui_cards}</div>
  </div>
</div>'''


if __name__ == "__main__":
    week_label = sys.argv[1]
    days = []
    for path in sys.argv[2:]:
        d = json.load(open(path, encoding="utf-8"))
        days.append((d["date"], d["weekday"].replace("요일", ""), d["juui"], d["ilban"], d["absent"]))
    sys.stdout.write(build(week_label, days))
