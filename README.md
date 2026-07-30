# Pococha ランクボーダー早見表

Pococha の各締め時間（22時 / 24時 / 13時）のランク別ボーダー（メーター）を
毎日自動取得し、社内向けに GitHub Pages で公開する。

- **データ出典**: UPSTAR (`upstar.livestar.tokyo`) の Firebase Cloud Function `fetchBorder`
- **公開**: GitHub Pages（`docs/`）
- **更新**: 毎日 10:00（launchd → `run.sh`）

## 反映ラグ（10時取得時点の最新確定日）

| 締め時間 | 最新確定 |
|---|---|
| 22時 | 前日 (D-1) |
| 24時 | 前日 (D-1) |
| 13時 | 前々日 (D-2) |

`fetch.py` は各締め時間ごとに「今日から遡って最初にデータがある日」を採用するため、
ラグがあっても常に最新の確定値が入る。

## 構成

| ファイル | 役割 |
|---|---|
| `fetch.py` | UPSTAR API から取得し `data/history.json` に蓄積 |
| `build.py` | `history.json` → `docs/index.html` を生成 |
| `run.sh` | 取得 → 生成 → commit → push（launchd から実行） |
| `.github/workflows/deploy.yml` | push を GitHub Pages へデプロイ |

## 手動実行

```bash
python3 fetch.py && python3 build.py   # 取得＋生成のみ
./run.sh                                # 取得＋生成＋push
```
