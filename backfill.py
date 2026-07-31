#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2026-07-01 から今日まで、22/24/13時のボーダーを遡って取得し
data/history.json に蓄積する（一度きりのバックフィル用）。
連続アクセスで空応答が返ることがあるため各リクエスト間にウェイトを入れる。
"""
import json
import time
import urllib.request
import datetime
import pathlib

ENDPOINT = "https://us-central1-viibar-adc.cloudfunctions.net/fetchBorder"
CLOSING_TIMES = [22, 24, 13]
START = datetime.date(2026, 6, 1)
SLEEP = 0.6
HERE = pathlib.Path(__file__).resolve().parent
HISTORY = HERE / "data" / "history.json"


def call_border(t, d, retries=2):
    payload = json.dumps({"data": {
        "borderTableTime": t, "year": d.year, "month": d.month, "day": d.day
    }}).encode("utf-8")
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                ENDPOINT, data=payload,
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as res:
                body = json.loads(res.read().decode("utf-8"))
            result = body.get("result") or [[]]
            return result[0] if result and result[0] else []
        except Exception as e:
            if attempt < retries:
                time.sleep(1.5)
                continue
            print(f"    ! {t}時 {d}: {e}")
            return []


def main():
    hist = json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() \
        else {"closingTimes": {}, "updatedAt": None}
    ct = hist.setdefault("closingTimes", {})
    today = datetime.date.today()

    for t in CLOSING_TIMES:
        slot = ct.setdefault(str(t), {"latestDate": None, "byDate": {}})
        by = slot.setdefault("byDate", {})
        got, empty = 0, 0
        d = START
        while d <= today:
            ds = d.isoformat()
            rows = call_border(t, d)
            if rows:
                by[ds] = rows
                got += 1
            else:
                empty += 1
            time.sleep(SLEEP)
            d += datetime.timedelta(days=1)
        # latestDate 更新
        if by:
            slot["latestDate"] = max(by.keys())
        print(f"[{t}時] 取得 {got}日 / 空 {empty}日 / 最新 {slot['latestDate']}")

    hist["updatedAt"] = datetime.datetime.now().isoformat(timespec="seconds")
    HISTORY.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"保存: {HISTORY}")


if __name__ == "__main__":
    main()
