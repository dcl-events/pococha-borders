#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data/history.json から「ボーダー推移ダッシュボード」docs/trend.html を生成する。
- タブ: +2(borderTop) / +1(borderUpper) / ±0(borderNormal)
- 選択: ランク / 締め時間(22/24/13)
- 表示: 推移折れ線 + 中央値ライン / 予測レンジ(最小・中央値・最大) / 曜日別平均
個人データは一切使わない「誰が見ても」版。
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
HISTORY = HERE / "data" / "history.json"
OUT = HERE / "docs" / "trend.html"

TIERS = [("top", "+2"), ("upper", "+1"), ("normal", "±0")]
FIELD = {"top": "borderTop", "upper": "borderUpper", "normal": "borderNormal"}


def build_series():
    """data[ct][rank] = [{d:'MM/DD', iso:'YYYY-MM-DD', top, upper, normal}, ...] 日付昇順"""
    raw = json.loads(HISTORY.read_text())
    out = {}
    ranks_order = []
    for ct, ctobj in raw["closingTimes"].items():
        by = ctobj.get("byDate", {})
        out[ct] = {}
        for iso in sorted(by):
            for r in by[iso]:
                rk = r["rank"]
                if rk not in ranks_order:
                    ranks_order.append(rk)
                out[ct].setdefault(rk, []).append({
                    "iso": iso,
                    "d": iso[5:].replace("-", "/"),
                    "top": r.get("borderTop"),
                    "upper": r.get("borderUpper"),
                    "normal": r.get("borderNormal"),
                })
    # ランクは S6..E1 の順に固定（最新日の並びを利用）
    fixed = ['S6','S5','S4','S3','S2','S1','A3','A2','A1','B3','B2','B1','C3','C2','C1','D3','D2','D1','E1']
    ranks = [r for r in fixed if r in ranks_order] + [r for r in ranks_order if r not in fixed]
    cts = list(out.keys())
    updated = raw.get("updatedAt", "")
    try:
        import datetime
        updated = datetime.datetime.fromisoformat(updated).strftime("%Y/%m/%d %H:%M")
    except Exception:
        pass
    return out, ranks, cts, updated


HTML = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pococha ボーダー推移</title>
<style>
  :root{ --bg:#f6f7f9; --card:#fff; --border:#e3e8ef; --text:#1a1d21; --sub:#697586;
         --accent:#5b8def; --accent-soft:#c9dcff; --track:#f3f5f8; --hot:#e8544f; }
  @media (prefers-color-scheme:dark){
    :root{ --bg:#0f1216; --card:#161b22; --border:#2a313c; --text:#e6edf3; --sub:#9aa4b2;
           --accent:#5b8def; --accent-soft:#2a3d5f; --track:#1c232c; }
  }
  *{ box-sizing:border-box; }
  body{ margin:0; padding:24px 14px 40px; background:var(--bg); color:var(--text);
        font-family:-apple-system,BlinkMacSystemFont,"Hiragino Kaku Gothic ProN","Noto Sans JP",sans-serif; }
  .app{ max-width:820px; margin:0 auto; }
  .brandbar{ display:flex; justify-content:center; margin:2px 0 18px; }
  .brandbar img{ height:34px; width:auto; }
  h1{ font-size:19px; margin:0 0 4px; text-align:center; }
  .lead{ font-size:12.5px; color:var(--sub); margin:0 0 18px; text-align:center; }
  footer{ color:var(--sub); font-size:11.5px; margin-top:22px; text-align:center; }
  .controls{ display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-bottom:14px; }
  select{ font-size:13px; font-weight:600; padding:7px 10px; border-radius:10px;
          border:1px solid var(--border); background:var(--card); color:var(--text); }
  .tabs{ display:inline-flex; background:var(--track); border-radius:999px; padding:3px; gap:2px; }
  .tab{ font-size:13px; font-weight:700; padding:6px 16px; border-radius:999px; cursor:pointer;
        color:var(--sub); border:none; background:transparent; }
  .tab.active{ background:var(--accent); color:#fff; }
  .card{ background:var(--card); border:1px solid var(--border); border-radius:16px; padding:18px; margin-bottom:12px; }
  .chead{ display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px; }
  .ttl{ font-size:16px; font-weight:700; }
  .sub{ font-size:12px; color:var(--sub); margin-top:2px; }
  .stat{ text-align:right; }
  .statnum{ font-size:22px; font-weight:800; color:var(--accent); }
  .statnum small{ font-size:13px; margin-left:1px; }
  .statlbl{ font-size:11px; color:var(--sub); }
  svg.chart{ width:100%; height:210px; overflow:visible; display:block; }
  .line{ fill:none; stroke:var(--accent); stroke-width:2.5; stroke-linejoin:round; stroke-linecap:round; }
  .area{ fill:var(--accent); opacity:.07; }
  .medline{ stroke:var(--border); stroke-width:1; stroke-dasharray:4 4; }
  .grid{ stroke:var(--border); stroke-width:1; opacity:.5; }
  .lbl{ fill:var(--sub); font-size:11px; }
  .dot{ fill:var(--accent); stroke:var(--card); stroke-width:2; }
  .dotlbl{ fill:var(--hot); font-size:12px; font-weight:700; }
  .row{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }
  @media(max-width:600px){ .row{ grid-template-columns:1fr; } }
  .minihd{ font-size:13px; font-weight:700; margin-bottom:14px; }
  .rangebar{ display:flex; align-items:center; gap:8px; }
  .rmin,.rmax{ font-size:12px; font-weight:700; color:var(--sub); white-space:nowrap; }
  .track{ position:relative; flex:1; height:10px; background:var(--track); border-radius:6px; }
  .band{ position:absolute; top:0; bottom:0; background:var(--accent-soft); border-radius:6px; }
  .med{ position:absolute; top:-3px; width:3px; height:16px; background:var(--accent); border-radius:2px; }
  .rlabels{ display:flex; justify-content:space-between; font-size:10.5px; color:var(--sub); margin-top:7px; }
  .rlabels b{ color:var(--accent); }
  .note{ font-size:12px; color:var(--sub); margin-top:12px; line-height:1.55; }
  .note b{ color:var(--accent); }
  .bars{ display:flex; align-items:flex-end; gap:7px; height:130px; }
  .bar{ flex:1; display:flex; flex-direction:column; align-items:center; height:100%; justify-content:flex-end; }
  .bar em{ font-size:10px; font-style:normal; font-weight:700; color:var(--sub); margin-bottom:4px; white-space:nowrap; }
  .bar.hot em{ color:var(--accent); }
  .bar i{ width:100%; background:var(--accent-soft); border-radius:5px 5px 0 0; }
  .bar.hot i{ background:var(--accent); }
  .bar b{ font-size:11px; font-weight:600; color:var(--sub); margin-top:5px; }
  .foot{ font-size:11px; color:var(--sub); text-align:center; margin-top:6px; }
</style>
</head>
<body>
<div class="app">
  <div class="brandbar">
    <picture>
      <source srcset="assets/dcl_logo_dark.png" media="(prefers-color-scheme: dark)">
      <img src="assets/dcl_logo.png" alt="DeNA Creator Links">
    </picture>
  </div>
  <h1>Pococha ボーダー推移</h1>
  <p class="lead">過去のボーダー実績から「相場」を読む早見表（個人データは使いません）。最終更新：__UPDATED__</p>

  <div class="controls">
    <select id="rank"></select>
    <select id="ct"></select>
    <div class="tabs" id="tabs"></div>
  </div>

  <div class="card">
    <div class="chead">
      <div><div class="ttl" id="chartTtl"></div><div class="sub" id="chartSub"></div></div>
      <div class="stat"><div class="statnum" id="medBig"></div><div class="statlbl">期間中央値</div></div>
    </div>
    <svg class="chart" id="chart" viewBox="0 0 720 210" preserveAspectRatio="none" role="img"></svg>
  </div>

  <div class="row">
    <div class="card">
      <div class="minihd">予測レンジ</div>
      <div class="rangebar">
        <div class="rmin" id="rmin"></div>
        <div class="track"><i class="band" id="band"></i><i class="med" id="medMark"></i></div>
        <div class="rmax" id="rmax"></div>
      </div>
      <div class="rlabels"><span>最小</span><span>中央値 <b id="rmed"></b></span><span>最大</span></div>
      <div class="note" id="rangeNote"></div>
    </div>
    <div class="card">
      <div class="minihd">曜日別 平均</div>
      <div class="bars" id="wbars"></div>
      <div class="note" id="wNote"></div>
    </div>
  </div>
  <footer>DeNA Creator Links — Pocochaボーダー推移／毎日10:00 自動更新</footer>
</div>

<script>
const DATA = __DATA__;
const RANKS = __RANKS__;
const CTS = __CTS__;
const TIER_LABEL = {top:"+2", upper:"+1", normal:"±0"};
const TIER_DESC = {top:"2ランクアップ", upper:"1ランクアップ", normal:"現ランク維持"};
const WD = ["月","火","水","木","金","土","日"];
let state = { rank: RANKS.includes("S3") ? "S3" : RANKS[0], ct: CTS[0], tier: "normal" };

const man = v => (v/1e4);
const fmtMan = v => (v==null? "-" : (Math.round(v/1e3)/10).toFixed(1)+"万");

function series(){
  const arr = (DATA[state.ct] && DATA[state.ct][state.rank]) || [];
  return arr.map(p => ({ iso:p.iso, d:p.d, v:p[state.tier] })).filter(p => p.v!=null);
}
function median(nums){ const s=[...nums].sort((a,b)=>a-b); const n=s.length; if(!n) return null;
  return n%2? s[(n-1)/2] : (s[n/2-1]+s[n/2])/2; }

function render(){
  // selectors
  document.getElementById("rank").value = state.rank;
  document.getElementById("ct").value = state.ct;
  [...document.querySelectorAll(".tab")].forEach(t=>t.classList.toggle("active", t.dataset.tier===state.tier));

  const all = series();
  const last14 = all.slice(-14);
  const recent = all.slice(-30);            // レンジ・曜日別は直近30日で相場を今に寄せる
  const vals = recent.map(p=>p.v);
  const med = median(vals), mn = Math.min(...vals), mx = Math.max(...vals);

  document.getElementById("chartTtl").textContent = `${state.rank}  ${TIER_LABEL[state.tier]} ボーダー 推移`;
  document.getElementById("chartSub").textContent = `締め${state.ct}時 ／ 直近${last14.length}日（${TIER_DESC[state.tier]}）`;
  document.getElementById("medBig").innerHTML = fmtMan(med).replace("万","<small>万</small>");

  drawChart(last14, med);

  // range
  const pct = v => ((v-mn)/(mx-mn||1))*100;
  document.getElementById("rmin").textContent = fmtMan(mn);
  document.getElementById("rmax").textContent = fmtMan(mx);
  document.getElementById("rmed").textContent = fmtMan(med);
  const q1 = median(vals.filter(v=>v<=med)), q3 = median(vals.filter(v=>v>=med));
  const band = document.getElementById("band");
  band.style.left = pct(q1)+"%"; band.style.right = (100-pct(q3))+"%";
  document.getElementById("medMark").style.left = pct(med)+"%";
  document.getElementById("rangeNote").innerHTML =
    `直近${vals.length}日の実績は <b>${fmtMan(mn)}〜${fmtMan(mx)}</b>。<br>` +
    `半分の日は <b>${fmtMan(q1)}〜${fmtMan(q3)}</b> に収まる。`;

  // weekday（直近30日）
  const wsum = Array.from({length:7},()=>[]);
  recent.forEach(p=>{ const wd=(new Date(p.iso).getDay()+6)%7; wsum[wd].push(p.v); });
  const wavg = wsum.map(a=> a.length? a.reduce((x,y)=>x+y,0)/a.length : null);
  const wvalid = wavg.filter(v=>v!=null);
  const wmax = Math.max(...wvalid), wmin = Math.min(...wvalid);
  const bars = wavg.map((v,i)=>{
    if(v==null) return `<div class="bar"><em>-</em><i style="height:0"></i><b>${WD[i]}</b></div>`;
    const h = 30 + (v-wmin)/((wmax-wmin)||1)*70;
    const hot = v===wmax ? " hot":"";
    return `<div class="bar${hot}"><em>${fmtMan(v)}</em><i style="height:${h}%"></i><b>${WD[i]}</b></div>`;
  }).join("");
  document.getElementById("wbars").innerHTML = bars;
  const we = median([wavg[5],wavg[6]].filter(v=>v!=null));
  const wk = median([wavg[0],wavg[1],wavg[2],wavg[3],wavg[4]].filter(v=>v!=null));
  const ratio = wk? (we/wk):1;
  const flat = Math.abs(ratio-1) < 0.12;
  document.getElementById("wNote").innerHTML = flat
    ? `→ 曜日差は <b>ほぼ無し</b>（週末${ratio.toFixed(2)}倍）。いつ走っても条件は近い。`
    : `→ 週末は平日の <b>${ratio.toFixed(2)}倍</b>。狙い目を意識。`;
}

function drawChart(pts, med){
  const W=720,H=210, padL=8,padR=8,padT=18,padB=26;
  const vals=pts.map(p=>p.v);
  let mn=Math.min(...vals), mx=Math.max(...vals);
  const span=(mx-mn)||1; mn-=span*0.15; mx+=span*0.15;
  const x=i=> padL + i*( (W-padL-padR)/Math.max(1,pts.length-1) );
  const y=v=> padT + (1-(v-mn)/(mx-mn))*(H-padT-padB);
  const line = pts.map((p,i)=>`${x(i).toFixed(1)},${y(p.v).toFixed(1)}`).join(" ");
  const area = `${padL},${H-padB} ${line} ${x(pts.length-1)},${H-padB}`;
  const ymed = y(med);
  const last = pts[pts.length-1];
  const lx=x(pts.length-1), ly=y(last.v);
  const labels = pts.map((p,i)=> (i===0||i===pts.length-1||i===Math.floor(pts.length/2))
    ? `<text class="lbl" x="${x(i)}" y="${H-8}" text-anchor="${i===0?'start':i===pts.length-1?'end':'middle'}">${p.d}</text>`:"").join("");
  const svg = `
    <polyline class="area" points="${area}"/>
    <line class="medline" x1="${padL}" y1="${ymed.toFixed(1)}" x2="${W-padR}" y2="${ymed.toFixed(1)}"/>
    <text class="lbl" x="${padL+4}" y="${(ymed-5).toFixed(1)}">中央値 ${fmtMan(med)}</text>
    <polyline class="line" points="${line}"/>
    <circle class="dot" cx="${lx.toFixed(1)}" cy="${ly.toFixed(1)}" r="5.5"/>
    <text class="dotlbl" x="${(lx-6).toFixed(1)}" y="${(ly-10).toFixed(1)}" text-anchor="end">${fmtMan(last.v)}</text>
    ${labels}`;
  document.getElementById("chart").innerHTML = svg;
}

// build controls
const rankSel=document.getElementById("rank");
RANKS.forEach(r=> rankSel.appendChild(Object.assign(document.createElement("option"),{value:r,textContent:r+" ランク"})));
const ctSel=document.getElementById("ct");
CTS.forEach(c=> ctSel.appendChild(Object.assign(document.createElement("option"),{value:c,textContent:"締め "+c+"時"})));
const tabs=document.getElementById("tabs");
[["top","+2"],["upper","+1"],["normal","±0"]].forEach(([t,l])=>{
  const b=document.createElement("button"); b.className="tab"; b.dataset.tier=t; b.textContent=l;
  b.onclick=()=>{ state.tier=t; render(); }; tabs.appendChild(b);
});
rankSel.onchange=e=>{ state.rank=e.target.value; render(); };
ctSel.onchange=e=>{ state.ct=e.target.value; render(); };
render();
</script>
</body>
</html>
"""


def main():
    data, ranks, cts, updated = build_series()
    html = (HTML
            .replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
            .replace("__RANKS__", json.dumps(ranks, ensure_ascii=False))
            .replace("__CTS__", json.dumps(cts, ensure_ascii=False))
            .replace("__UPDATED__", updated or "-"))
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT}  ({len(html)//1024} KB)")


if __name__ == "__main__":
    main()
