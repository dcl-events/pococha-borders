#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data/history.json から社内公開用の docs/index.html を生成する。
標準ライブラリのみ（GitHub Actions 上でも pip 不要）。

全日付ぶんのデータをページに埋め込み、日付ボタン→カレンダーで
過去データをクリック切替できるようにする（GitHub Pages は静的なので
サーバ通信なしでクライアント側だけで日付切替する）。
"""
import json
import datetime
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
HISTORY = HERE / "data" / "history.json"
OUT = HERE / "docs" / "index.html"

CLOSING_ORDER = ["22", "24", "13"]
CLOSING_LABEL = {"22": "22時締め", "24": "24時締め", "13": "13時締め"}

# ランク表示順（上位→下位）
RANK_ORDER = ["S6", "S5", "S4", "S3", "S2", "S1",
              "A3", "A2", "A1", "B3", "B2", "B1",
              "C3", "C2", "C1", "D3", "D2", "D1", "E1"]

# 遡って貯めるデータの下限（この月をカレンダー最小に）
MIN_DATE = "2026-06-01"


def sort_rows(rows):
    idx = {r: i for i, r in enumerate(RANK_ORDER)}
    return sorted(rows, key=lambda x: idx.get(x.get("rank"), 999))


def main():
    hist = json.loads(HISTORY.read_text(encoding="utf-8"))
    ct = hist.get("closingTimes", {})
    updated = hist.get("updatedAt") or ""
    try:
        updated_disp = datetime.datetime.fromisoformat(updated).strftime("%Y/%m/%d %H:%M") + " JST"
    except Exception:
        updated_disp = updated

    # 埋め込み用データ payload: {time: {date: [ {rank,+2,+1,±0}, ... ]}}
    payload = {}
    all_dates = set()
    for key in CLOSING_ORDER:
        by = (ct.get(key, {}) or {}).get("byDate", {}) or {}
        payload[key] = {}
        for ds, rows in by.items():
            compact = [
                {
                    "rank": r.get("rank"),
                    "t": r.get("borderTop"),
                    "u": r.get("borderUpper"),
                    "n": r.get("borderNormal"),
                }
                for r in sort_rows(rows)
            ]
            payload[key][ds] = compact
            all_dates.add(ds)

    max_date = max(all_dates) if all_dates else MIN_DATE
    # デフォルト表示日：22時データがある最新日、無ければ全体の最新
    dates_22 = sorted(payload.get("22", {}).keys())
    default_date = dates_22[-1] if dates_22 else max_date

    html_doc = TEMPLATE
    replacements = {
        "__DATA__": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        "__UPDATED__": updated_disp,
        "__MINDATE__": MIN_DATE,
        "__MAXDATE__": max_date,
        "__DEFAULTDATE__": default_date,
    }
    for k, v in replacements.items():
        html_doc = html_doc.replace(k, v)

    OUT.write_text(html_doc, encoding="utf-8")
    print(f"生成: {OUT}  (収録日数: {len(all_dates)} / 最新: {max_date})")


TEMPLATE = r"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="assets/dcl_mark.png">
<link rel="apple-touch-icon" href="assets/dcl_mark.png">
<title>Pococha ランクボーダー早見表</title>
<style>
  :root {
    --bg1:#fff5fb; --bg2:#f0ecff; --card:#ffffff; --fg:#3a2e4d; --sub:#a596bb;
    --line:#f3e6f2; --accent:#e75c9c; --pink:#ff6fae; --purple:#8f6bff;
    --soft:#ffe6f2; --soft2:#efe8ff; --accent-bg:#ffe6f2; --zebra:#fdf3f9; --th:#faf0f7;
    --grad:linear-gradient(90deg,#ff6fae,#8f6bff); --shadow:rgba(226,110,170,.16);
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg1:#1b1526; --bg2:#171029; --card:#241b33; --fg:#f2ecfb; --sub:#a99ec2;
      --line:#372c4a; --accent:#ff8bbd; --pink:#ff8bbd; --purple:#a98bff;
      --soft:#3a2740; --soft2:#2c2442; --accent-bg:#3a2740; --zebra:#201830; --th:#241b33;
      --grad:linear-gradient(90deg,#ff8bbd,#a98bff); --shadow:rgba(0,0,0,.35);
    }
  }
  * { box-sizing:border-box; }
  body {
    margin:0; color:var(--fg); min-height:100vh;
    background:linear-gradient(165deg,var(--bg1) 0%,var(--bg2) 100%); background-attachment:fixed;
    font-family:"Hiragino Maru Gothic ProN",-apple-system,BlinkMacSystemFont,"Hiragino Kaku Gothic ProN","Noto Sans JP",sans-serif;
    line-height:1.5; padding:24px 14px 60px;
  }
  .wrap { max-width:760px; margin:0 auto; }
  .brandbar { display:flex; justify-content:center; margin:2px 0 16px; }
  .brandbar img { height:34px; width:auto; }
  h1 { font-size:24px; font-weight:800; margin:0 0 6px; text-align:center; letter-spacing:.5px;
       background:var(--grad); -webkit-background-clip:text; background-clip:text; color:transparent; }
  .meta { color:var(--sub); font-size:12.5px; margin:0 0 20px; text-align:center; }

  /* 日付セレクタ */
  .datebar { position:relative; margin-bottom:16px; }
  .datebtn {
    display:inline-flex; align-items:center; gap:8px;
    border:1.5px solid var(--line); background:var(--card); color:var(--fg);
    padding:10px 16px; border-radius:16px; font-size:15px; font-weight:800;
    cursor:pointer; box-shadow:0 4px 14px var(--shadow);
  }
  .datebtn:hover { border-color:var(--pink); }
  .datebtn .ico { font-size:15px; }
  .datebtn .chev { color:var(--accent); font-size:11px; transition:transform .15s; }
  .datebtn.open .chev { transform:rotate(180deg); }

  .calendar {
    position:absolute; z-index:20; top:calc(100% + 6px); left:0;
    width:300px; max-width:calc(100vw - 28px);
    background:var(--card); border:1.5px solid var(--line); border-radius:20px;
    box-shadow:0 14px 36px var(--shadow); padding:14px;
  }
  .calendar[hidden] { display:none; }
  .cal-head { display:flex; align-items:center; justify-content:space-between; margin-bottom:8px; }
  .cal-title { font-weight:800; font-size:14px; }
  .cal-nav {
    border:1.5px solid var(--line); background:var(--card); color:var(--accent);
    width:32px; height:32px; border-radius:10px; cursor:pointer; font-size:14px;
  }
  .cal-nav:disabled { opacity:.35; cursor:default; }
  .cal-grid { display:grid; grid-template-columns:repeat(7,1fr); gap:2px; }
  .cal-wd { text-align:center; font-size:11px; color:var(--sub); padding:4px 0; }
  .cal-day {
    position:relative; aspect-ratio:1/1; border:none; background:transparent;
    color:var(--fg); border-radius:10px; font-size:13px; cursor:pointer; font-weight:700;
  }
  .cal-day:hover:not(:disabled) { background:var(--soft); }
  .cal-day.sel { background:var(--grad); color:#fff; font-weight:800; }
  .cal-day:disabled { color:var(--sub); opacity:.3; cursor:default; }
  .cal-day .dot {
    position:absolute; bottom:5px; left:50%; transform:translateX(-50%);
    width:4px; height:4px; border-radius:50%; background:var(--purple);
  }
  .cal-day.sel .dot { background:#fff; }
  .cal-empty { background:transparent; }

  .tabs { display:flex; gap:8px; margin-bottom:16px; flex-wrap:wrap; align-items:center; }
  .tab {
    border:1.5px solid var(--line); background:var(--card); color:var(--sub);
    padding:9px 18px; border-radius:999px; font-size:14px; cursor:pointer; font-weight:800;
    box-shadow:0 2px 8px var(--shadow);
  }
  .tab.active { background:var(--grad); border-color:transparent; color:#fff; box-shadow:0 4px 12px var(--shadow); }
  a.tab.trend { margin-left:auto; text-decoration:none; color:var(--accent);
    background:var(--soft); border:none; display:inline-flex; align-items:center; gap:3px; }
  a.tab.trend:hover { filter:brightness(.97); }

  .card { background:var(--card); border:1.5px solid var(--line); border-radius:24px;
          padding:8px 14px; box-shadow:0 10px 30px var(--shadow); }
  table { width:100%; border-collapse:collapse; font-variant-numeric:tabular-nums; }
  th,td { padding:9px 8px; text-align:right; font-size:13.5px; border-bottom:1px solid var(--line); }
  thead th { color:var(--sub); font-weight:800; font-size:13px; }
  thead th:not(.rk) { color:var(--accent); }
  th.rk { text-align:left; }
  td { white-space:nowrap; }
  tbody th.rk { font-weight:800; }
  tbody tr:last-child th, tbody tr:last-child td { border-bottom:none; }
  tbody tr.rrow { cursor:pointer; border-radius:12px; }
  tbody tr.rrow:hover { background:var(--soft); }
  .rchev { color:var(--pink); font-weight:800; opacity:.6; }
  .empty { color:var(--sub); padding:28px 20px; text-align:center; }
  footer { color:var(--sub); font-size:11.5px; margin-top:22px; text-align:center; }
</style>
</head>
<body>
  <div class="wrap">
    <div class="brandbar">
      <picture>
        <source srcset="assets/dcl_logo_dark.png" media="(prefers-color-scheme: dark)">
        <img src="assets/dcl_logo.png" alt="DeNA Creator Links">
      </picture>
    </div>
    <h1>Pococha ランクボーダー早見表</h1>
    <p class="meta">数値は各締め時間の到達ボーダー（メーター）。最終更新：__UPDATED__</p>

    <div class="datebar">
      <button id="dateBtn" class="datebtn" aria-haspopup="true" aria-expanded="false">
        <span class="ico">📅</span><span id="dateLabel">—</span><span class="chev">▼</span>
      </button>
      <div id="calendar" class="calendar" hidden></div>
    </div>

    <div class="tabs">
      <button class="tab active" data-t="22">22時締め</button>
      <button class="tab" data-t="24">24時締め</button>
      <button class="tab" data-t="13">13時締め</button>
      <a id="trendLink" class="tab trend" href="trend/">📈 推移</a>
    </div>

    <div class="card"><div id="tableHost"></div></div>
    <footer>DeNA Creator Links ✨ Pocochaランクボーダー早見表／毎朝10:00 更新</footer>
  </div>

<script>
  var DATA = __DATA__;
  var MIN = "__MINDATE__", MAX = "__MAXDATE__", DEFAULT = "__DEFAULTDATE__";
  var COLS = [["t","+2"],["u","+1"],["n","±0"]];
  var WD = ["日","月","火","水","木","金","土"];

  var state = { date: DEFAULT, time: "22" };

  function pad(n){ return (n<10?"0":"")+n; }
  function key(y,m,d){ return y+"-"+pad(m)+"-"+pad(d); }
  function parse(s){ var a=s.split("-"); return {y:+a[0],m:+a[1],d:+a[2]}; }
  function fmt(n){ return (n==null)?"—":Number(n).toLocaleString("en-US"); }
  function jpLabel(s){ var p=parse(s); var dt=new Date(p.y,p.m-1,p.d);
    return p.y+"年"+p.m+"月"+p.d+"日（"+WD[dt.getDay()]+"）"; }
  function hasAny(s){ return ["22","24","13"].some(function(t){ return DATA[t] && DATA[t][s]; }); }

  function renderTable(){
    var rows = (DATA[state.time]||{})[state.date];
    var host = document.getElementById("tableHost");
    if(!rows || !rows.length){
      host.innerHTML = '<p class="empty">この日のデータはありません</p>';
      return;
    }
    var head = COLS.map(function(c){ return "<th>"+c[1]+"</th>"; }).join("");
    var body = rows.map(function(r){
      var tds = COLS.map(function(c){ return "<td>"+fmt(r[c[0]])+"</td>"; }).join("");
      return '<tr class="rrow" onclick="goTrend(\''+r.rank+'\')" title="'+r.rank+' の推移を見る">'
        + '<th class="rk">'+r.rank+' <span class="rchev">›</span></th>'+tds+'</tr>';
    }).join("");
    host.innerHTML = '<table><thead><tr><th class="rk">ランク</th>'+head+'</tr></thead><tbody>'+body+'</tbody></table>';
  }

  function updateDateLabel(){ document.getElementById("dateLabel").textContent = jpLabel(state.date); }

  // 推移ページへの導線（現在の締め時間を引き継ぐ）
  function updateTrendLink(){ document.getElementById("trendLink").href = "trend/?ct=" + state.time; }
  function goTrend(rank){ location.href = "trend/?rank=" + encodeURIComponent(rank) + "&ct=" + state.time; }

  // ----- カレンダー -----
  var view = parse(state.date); // {y,m}
  var calEl = document.getElementById("calendar");

  function monthStr(y,m){ return y+"年"+m+"月"; }
  function ymNum(y,m){ return y*12+(m-1); }
  function inRange(s){ return s>=MIN && s<=MAX; }

  function renderCalendar(){
    var y=view.y, m=view.m;
    var first=new Date(y,m-1,1), startWd=first.getDay();
    var days=new Date(y,m,0).getDate();
    var minYM=ymNum(parse(MIN).y,parse(MIN).m), maxYM=ymNum(parse(MAX).y,parse(MAX).m), curYM=ymNum(y,m);
    var h='';
    h+='<div class="cal-head">';
    h+='<button class="cal-nav" id="calPrev"'+(curYM<=minYM?' disabled':'')+'>‹</button>';
    h+='<span class="cal-title">'+monthStr(y,m)+'</span>';
    h+='<button class="cal-nav" id="calNext"'+(curYM>=maxYM?' disabled':'')+'>›</button>';
    h+='</div><div class="cal-grid">';
    WD.forEach(function(w){ h+='<div class="cal-wd">'+w+'</div>'; });
    for(var i=0;i<startWd;i++) h+='<button class="cal-day cal-empty" disabled></button>';
    for(var d=1;d<=days;d++){
      var s=key(y,m,d);
      var dis=!inRange(s);
      var sel=(s===state.date)?' sel':'';
      var dot=hasAny(s)?'<span class="dot"></span>':'';
      h+='<button class="cal-day'+sel+'" data-d="'+s+'"'+(dis?' disabled':'')+'>'+d+dot+'</button>';
    }
    h+='</div>';
    calEl.innerHTML=h;
    document.getElementById("calPrev").onclick=function(e){ e.stopPropagation(); if(view.m===1){view.y--;view.m=12;}else{view.m--;} renderCalendar(); };
    document.getElementById("calNext").onclick=function(e){ e.stopPropagation(); if(view.m===12){view.y++;view.m=1;}else{view.m++;} renderCalendar(); };
    calEl.querySelectorAll(".cal-day[data-d]").forEach(function(btn){
      btn.onclick=function(){ state.date=btn.dataset.d; updateDateLabel(); renderTable(); closeCal(); };
    });
  }

  function openCal(){ view=parse(state.date); renderCalendar(); calEl.hidden=false;
    document.getElementById("dateBtn").classList.add("open");
    document.getElementById("dateBtn").setAttribute("aria-expanded","true"); }
  function closeCal(){ calEl.hidden=true;
    document.getElementById("dateBtn").classList.remove("open");
    document.getElementById("dateBtn").setAttribute("aria-expanded","false"); }

  document.getElementById("dateBtn").addEventListener("click", function(e){
    e.stopPropagation(); calEl.hidden ? openCal() : closeCal();
  });
  document.addEventListener("click", function(e){
    if(!calEl.hidden && !calEl.contains(e.target)) closeCal();
  });

  // ----- タブ（推移リンクの <a> は除外） -----
  document.querySelectorAll('.tab[data-t]').forEach(function(b){
    b.addEventListener('click', function(){
      state.time=b.dataset.t;
      document.querySelectorAll('.tab[data-t]').forEach(function(x){ x.classList.toggle('active', x.dataset.t===state.time); });
      renderTable();
      updateTrendLink();
    });
  });

  // ----- URL 深リンク（推移ページ等から ?date=YYYY-MM-DD&ct=22 で着地） -----
  (function(){
    try {
      var sp = new URLSearchParams(location.search);
      var t = sp.get("ct") || sp.get("time");
      if (t && ["22","24","13"].indexOf(t) >= 0) {
        state.time = t;
        document.querySelectorAll('.tab').forEach(function(x){ x.classList.toggle('active', x.dataset.t===state.time); });
      }
      var d = sp.get("date");
      if (d && d >= MIN && d <= MAX && hasAny(d)) { state.date = d; }
    } catch (e) {}
  })();

  // ----- 初期描画 -----
  updateDateLabel();
  renderTable();
  updateTrendLink();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
