#!/usr/bin/env python3
"""cfg.json -> 카드형 HTML (특이사항 보고서 일일 카드).

사용법: build_daily_all.py cfg.json [data.json] > 보고서.html

data.json(주간 집계용, juui/tag가 사람이 검수한 값)을 같이 주면 그 판정을
그대로 쓰고, 없으면 rules.judge()의 자동판정으로 대체한다(참고용 자동화 경로).

index.html의 #report 스코프에 이미 정의된 CSS 변수
(--color-text-primary/secondary/tertiary, --color-background-danger/info)를
그대로 사용하고, 카드 레이아웃 자체 스타일만 <style>로 포함한다.
"""
import html
import json
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from rules import judge, KEYWORD_GROUPS, VITAL_RE  # noqa: E402


def highlight_note(note):
    esc = html.escape(note)
    # 통증/치료 계열 키워드는 info, 나머지 위험 키워드는 danger로 강조
    info_kws = sorted(set(sum((kws for label, kws in KEYWORD_GROUPS if label == "통증호소"), [])), key=len, reverse=True)
    danger_kws = sorted(
        set(sum((kws for label, kws in KEYWORD_GROUPS if label != "통증호소"), [])),
        key=len, reverse=True,
    )
    for kw in danger_kws:
        esc = esc.replace(html.escape(kw), f'<mark class="hl-danger">{html.escape(kw)}</mark>')
    for kw in info_kws:
        esc = esc.replace(html.escape(kw), f'<mark class="hl-info">{html.escape(kw)}</mark>')
    return esc


def vital_html(vital):
    if not vital or vital in ("/", "측정안됨"):
        return f'<span class="vital">{html.escape(vital or "측정안됨")}</span>'
    m = VITAL_RE.search(vital)
    cls = "vital"
    if m:
        sys_, dia, temp = int(m.group(1)), int(m.group(2)), float(m.group(3))
        if sys_ <= 100 or sys_ >= 140 or dia >= 90 or temp >= 37.0:
            cls = "vital vital-warn"
    return f'<span class="{cls}">{html.escape(vital)}</span>'


def person_card(name, vital, note, verified_tags=None):
    if verified_tags is not None:
        is_juui, tags = (name in verified_tags), verified_tags.get(name, [])
    else:
        is_juui, tags = judge(vital, note, name)
    tag_html = ""
    if tags:
        chips = "".join(f'<span class="chip">{html.escape(t)}</span>' for t in tags)
        tag_html = f'<div class="chips">{chips}</div>'
    warn_cls = " card-warn" if is_juui else ""
    return f'''<article class="card{warn_cls}">
  <header><span class="name">{html.escape(name)}</span>{vital_html(vital)}</header>
  <p class="note">{highlight_note(note)}</p>
  {tag_html}
</article>'''


STYLE = '''<style>
.rpt-wrap{font-size:14px;line-height:1.6;}
.rpt-head{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin:10px 0 14px;}
.rpt-head h2{font-size:16px;margin:0;color:var(--color-text-primary);}
.rpt-head .wd{color:var(--color-text-secondary);font-size:13px;}
.rpt-absent{font-size:12.5px;color:var(--color-text-tertiary);margin:0 0 16px;padding:8px 12px;
  background:var(--color-background-info);border-radius:8px;}
.rpt-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px;}
.card{border:1px solid #e0ddd5;border-radius:10px;padding:12px 14px;background:#fff;}
.card-warn{border-color:#eab8b6;background:var(--color-background-danger);}
.card header{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;}
.card .name{font-weight:700;color:var(--color-text-primary);font-size:13.5px;}
.card .vital{font-size:12px;color:var(--color-text-secondary);font-variant-numeric:tabular-nums;}
.card .vital-warn{color:#b3261e;font-weight:700;}
.card .note{margin:0;color:var(--color-text-primary);font-size:13px;word-break:keep-all;}
.card .chips{margin-top:8px;display:flex;gap:5px;flex-wrap:wrap;}
.card .chip{font-size:11px;padding:2px 8px;border-radius:999px;background:#b3261e;color:#fff;font-weight:600;}
mark.hl-danger{background:var(--color-background-danger);color:inherit;border-radius:3px;padding:0 2px;}
mark.hl-info{background:var(--color-background-info);color:inherit;border-radius:3px;padding:0 2px;}
</style>'''


def build(cfg, data=None):
    verified_tags = None
    if data is not None:
        verified_tags = {p["name"]: [p["tag"]] for p in data.get("juui", [])}
    cards = "\n".join(person_card(n, v, note, verified_tags) for n, v, note in cfg["people"])
    absent_html = ""
    if cfg.get("absent"):
        absent_html = f'<p class="rpt-absent">🚫 결석: {html.escape(cfg.get("gyeolseok") or ", ".join(cfg["absent"]))}</p>'
    return f'''{STYLE}
<div class="rpt-wrap">
  <div class="rpt-head"><h2>{html.escape(cfg["date"])}</h2><span class="wd">{html.escape(cfg["weekday"])}요일</span></div>
  {absent_html}
  <div class="rpt-grid">
{cards}
  </div>
</div>'''


if __name__ == "__main__":
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
    data = json.load(open(sys.argv[2], encoding="utf-8")) if len(sys.argv) > 2 else None
    sys.stdout.write(build(cfg, data))
