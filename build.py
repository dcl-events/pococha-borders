#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data/history.json から社内公開用の docs/index.html を生成する。
標準ライブラリのみ（GitHub Actions 上でも pip 不要）。
"""
import json
import datetime
import pathlib
import html

HERE = pathlib.Path(__file__).resolve().parent
HISTORY = HERE / "data" / "history.json"
OUT = HERE / "docs" / "index.html"

CLOSING_ORDER = ["22", "24", "13"]
CLOSING_LABEL = {"22": "22時締め", "24": "24時締め", "13": "13時締め"}

# ランク表示順（上位→下位）
RANK_ORDER = ["S6", "S5", "S4", "S3", "S2", "S1",
              "A3", "A2", "A1", "B3", "B2", "B1",
              "C3", "C2", "C1", "D3", "D2", "D1", "E1"]

COLS = [
    ("borderTop", "Top"),
    ("borderUpper", "上位"),
    ("borderNormal", "通常"),
    ("borderLower", "下位"),
]


def fmt(n):
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return "—"


def jp_date(iso):
    try:
        d = datetime.date.fromisoformat(iso)
        wd = "月火水木金土日"[d.weekday()]
        return f"{d.month}月{d.day}日（{wd}）"
    except Exception:
        return iso or "—"


def sort_rows(rows):
    idx = {r: i for i, r in enumerate(RANK_ORDER)}
    return sorted(rows, key=lambda x: idx.get(x.get("rank"), 999))


def build_table(rows):
    rows = sort_rows(rows)
    head = "".join(f"<th>{lbl}</th>" for _, lbl in COLS)
    body = []
    for r in rows:
        tds = "".join(f"<td>{fmt(r.get(k))}</td>" for k, _ in COLS)
        body.append(f'<tr><th class="rk">{html.escape(str(r.get("rank","")))}</th>{tds}</tr>')
    return (
        f'<table><thead><tr><th class="rk">ランク</th>{head}</tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table>'
    )


def main():
    hist = json.loads(HISTORY.read_text(encoding="utf-8"))
    ct = hist.get("closingTimes", {})
    updated = hist.get("updatedAt") or ""
    try:
        updated_disp = datetime.datetime.fromisoformat(updated).strftime("%Y/%m/%d %H:%M")
    except Exception:
        updated_disp = updated

    tabs, panels = [], []
    for i, key in enumerate(CLOSING_ORDER):
        slot = ct.get(key, {})
        latest = slot.get("latestDate")
        rows = (slot.get("byDate") or {}).get(latest, []) if latest else []
        active = " active" if i == 0 else ""
        tabs.append(
            f'<button class="tab{active}" data-t="{key}">{CLOSING_LABEL[key]}</button>'
        )
        table = build_table(rows) if rows else '<p class="empty">データ未取得</p>'
        panels.append(
            f'<section class="panel{active}" data-t="{key}">'
            f'<div class="asof">対象日：<strong>{jp_date(latest)}</strong></div>'
            f'{table}</section>'
        )

    html_doc = TEMPLATE.format(
        tabs="".join(tabs),
        panels="".join(panels),
        updated=html.escape(updated_disp),
    )
    OUT.write_text(html_doc, encoding="utf-8")
    print(f"生成: {OUT}")


TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pococha ランクボーダー早見表</title>
<style>
  :root {{
    --bg:#f6f7f9; --card:#fff; --fg:#1a1d21; --sub:#697586;
    --line:#e3e8ef; --accent:#5b8def; --accent-bg:#eaf1ff; --zebra:#fafbfc;
    --th:#f3f5f8;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg:#0f1216; --card:#161b22; --fg:#e6edf3; --sub:#9aa4b2;
      --line:#2a313c; --accent:#5b8def; --accent-bg:#1b2740; --zebra:#1a2028;
      --th:#1c232c;
    }}
  }}
  * {{ box-sizing:border-box; }}
  body {{
    margin:0; background:var(--bg); color:var(--fg);
    font-family:-apple-system,BlinkMacSystemFont,"Hiragino Kaku Gothic ProN","Noto Sans JP",sans-serif;
    line-height:1.5; padding:24px 14px 60px;
  }}
  .wrap {{ max-width:760px; margin:0 auto; }}
  .brandbar {{ display:flex; justify-content:center; margin:2px 0 18px; }}
  .brandbar img {{ height:34px; width:auto; }}
  h1 {{ font-size:20px; margin:0 0 4px; }}
  .meta {{ color:var(--sub); font-size:12.5px; margin:0 0 18px; }}
  .tabs {{ display:flex; gap:8px; margin-bottom:14px; flex-wrap:wrap; }}
  .tab {{
    border:1px solid var(--line); background:var(--card); color:var(--fg);
    padding:8px 16px; border-radius:999px; font-size:14px; cursor:pointer;
    font-weight:600;
  }}
  .tab.active {{ background:var(--accent-bg); border-color:var(--accent); color:var(--accent); }}
  .panel {{ display:none; }}
  .panel.active {{ display:block; }}
  .asof {{ font-size:13px; color:var(--sub); margin:2px 0 10px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:14px 12px; }}
  table {{ width:100%; border-collapse:collapse; font-variant-numeric:tabular-nums; }}
  th,td {{ padding:7px 8px; text-align:right; font-size:13.5px; border-bottom:1px solid var(--line); }}
  thead th {{ background:var(--th); color:var(--sub); font-weight:600; position:sticky; top:0; }}
  th.rk {{ text-align:left; }}
  td {{ white-space:nowrap; }}
  tbody th.rk {{ font-weight:700; }}
  tbody tr:nth-child(even) {{ background:var(--zebra); }}
  .empty {{ color:var(--sub); padding:20px; text-align:center; }}
  footer {{ color:var(--sub); font-size:11.5px; margin-top:20px; text-align:center; }}
</style>
</head>
<body>
  <div class="wrap">
    <div class="brandbar"><img src="assets/dcl_logo.png" alt="DeNA Creator Links"></div>
    <h1>Pococha ランクボーダー早見表</h1>
    <p class="meta">数値は各締め時間の到達ボーダー（メーター）。最終更新：{updated}</p>
    <div class="tabs">{tabs}</div>
    <div class="card">{panels}</div>
    <footer>DeNA Creator Links — Pococha Rank Boarder／毎日10:00 自動更新</footer>
  </div>
<script>
  document.querySelectorAll('.tab').forEach(function(b){{
    b.addEventListener('click', function(){{
      var t=b.dataset.t;
      document.querySelectorAll('.tab').forEach(function(x){{x.classList.toggle('active',x.dataset.t===t);}});
      document.querySelectorAll('.panel').forEach(function(x){{x.classList.toggle('active',x.dataset.t===t);}});
    }});
  }});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
