#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UPSTAR (upstar.livestar.tokyo) の Firebase Cloud Function `fetchBorder` から
Pococha のランク別ボーダーを取得し、data/history.json に蓄積する。

締め時間ごとの反映ラグ（10時取得時点）:
  - 22時 / 24時 : 前日(D-1)まで確定
  - 13時        : 前々日(D-2)まで確定
そのため各締め時間ごとに「今日から遡って最初にデータがある日」を採用する。
"""
import json
import urllib.request
import datetime
import pathlib

ENDPOINT = "https://us-central1-viibar-adc.cloudfunctions.net/fetchBorder"
CLOSING_TIMES = [22, 24, 13]          # 締め時間
LOOKBACK_DAYS = 7                     # 何日前まで遡って探すか
HERE = pathlib.Path(__file__).resolve().parent
HISTORY = HERE / "data" / "history.json"


def call_border(t: int, d: datetime.date):
    """指定締め時間・日付のボーダーを取得。rows(list) を返す。無ければ []。"""
    payload = json.dumps({
        "data": {
            "borderTableTime": t,
            "year": d.year,
            "month": d.month,
            "day": d.day,
        }
    }).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT, data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        body = json.loads(res.read().decode("utf-8"))
    result = body.get("result") or [[]]
    return result[0] if result and result[0] else []


def latest_available(t: int, today: datetime.date):
    """今日から遡って最初にデータがある (date, rows) を返す。無ければ (None, [])。"""
    for back in range(0, LOOKBACK_DAYS + 1):
        d = today - datetime.timedelta(days=back)
        rows = call_border(t, d)
        if rows:
            return d, rows
    return None, []


def load_history():
    if HISTORY.exists():
        return json.loads(HISTORY.read_text(encoding="utf-8"))
    return {"closingTimes": {}, "updatedAt": None}


def main():
    today = datetime.date.today()
    hist = load_history()
    ct = hist.setdefault("closingTimes", {})

    for t in CLOSING_TIMES:
        key = str(t)
        d, rows = latest_available(t, today)
        slot = ct.setdefault(key, {"latestDate": None, "byDate": {}})
        if d is None:
            print(f"[{t}時] 直近{LOOKBACK_DAYS}日にデータなし（据え置き）")
            continue
        ds = d.isoformat()
        slot["byDate"][ds] = rows          # 既存日は上書き（確定値で更新）
        # latestDate は最新日に更新
        cur = slot.get("latestDate")
        if cur is None or ds >= cur:
            slot["latestDate"] = ds
        print(f"[{t}時] {ds} : {len(rows)}件 取得")

    hist["updatedAt"] = datetime.datetime.now().isoformat(timespec="seconds")
    HISTORY.write_text(
        json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"保存: {HISTORY}")


if __name__ == "__main__":
    main()
