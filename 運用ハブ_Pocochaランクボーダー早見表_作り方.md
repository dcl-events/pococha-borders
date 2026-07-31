> 📌 最終更新: 2026-07-31（クラウド化：launchdからGitHub Actions cronへ載せ替え＝PC不要）／オーナー: sukeaki.ito

# Pococha ランクボーダー早見表 ― 作り方（構築ガイド）

DeNA Creator Links の「Pococha ランクボーダー早見表」（→使い方は同フォルダの `Pocochaランクボーダー早見表.md`）を、ゼロから作り直す／別の人が引き継ぐための技術手順。Claude Code で再現できるように書いてある。

---

## 0. 全体像
UPSTAR という外部サイトが公開している Pococha ランクボーダーのデータ（Firebase Cloud Function・認証不要）を毎朝取得し、静的HTMLに整形して GitHub Pages で公開する。**取得〜生成〜デプロイはすべて GitHub Actions（クラウド）で完結＝PC不要**（2026-07-31にlaunchdから載せ替え）。

```
GitHub Actions update.yml（cron 0 1 * * * = JST10:00）
  ├ fetch.py   … UPSTAR API から取得 → data/history.json に蓄積
  ├ build.py   … history.json → docs/index.html（全日付データ埋め込み＋カレンダーUI）
  ├ 自動コミット（github-actions[bot]）
  └ deploy-pages … docs/ を GitHub Pages へデプロイ
```

- プロジェクト（ソース）：`~/Claude/pococha-borders`（sukeaki の Mac。編集はここ→push）
- リポジトリ：`github.com/dcl-events/pococha-borders`（Public）
- 公開URL：`https://dcl-events.github.io/pococha-borders/`
- ※旧構成：ローカル `launchd`＋`run.sh` で毎朝実行していたが、Mac稼働に依存するためクラウドへ移行。launchd は停止（unload）済・plistは残置。

---

## 1. データソースの見つけ方（UPSTAR の API 特定）
UPSTAR（`upstar.livestar.tokyo`）は React 製の SPA で、HTMLにはデータが無い。JSバンドルを読むと Firebase を使っているのが分かる。

1. トップHTMLから JSバンドルのURLを拾う（`/static/js/main.*.chunk.js`）
2. バンドル内を検索：
   - Firebase 設定 … `projectId:"viibar-adc"` 等
   - データ取得は Cloud Functions の `httpsCallable("fetchBorder")`
   - ボーダー列のラベル定義 … `{top:{name:"borderTop",label:"+2"}, upper:{...label:"+1"}, normal:{...label:"±0"}}`
3. Cloud Function は callable。認証なしで直接叩ける（確認済み）。リージョンは `us-central1`。

### API仕様
```
POST https://us-central1-viibar-adc.cloudfunctions.net/fetchBorder
Content-Type: application/json

{"data":{"borderTableTime":22,"year":2026,"month":7,"day":29}}
```
- `borderTableTime` … 締め時間。**22 / 24 / 13** のいずれか
- レスポンス：`{"result":[[ {rank, borderTop, borderUpper, borderNormal, borderLower}, ... ]]}`
- 表示は **borderTop=+2 / borderUpper=+1 / borderNormal=±0** の3列。`borderLower` は使わない
- データが無い日は `{"result":[[]]}`（空）

### 反映ラグ（重要）
10:00取得時点で確定している最新日：
- **22時・24時 → 前日(D-1)**
- **13時 → 前々日(D-2)**

→ `fetch.py` は締め時間ごとに「今日から遡って最初にデータがある日」を採用してラグを吸収する。

### 注意（連続アクセス）
短時間に連打すると空応答/Bad Requestが返ることがある。バックフィル等では各リクエストの間に 0.6秒ほどウェイトを入れる。

---

## 2. ファイル構成と役割
| ファイル | 役割 |
|---|---|
| `fetch.py` | 締め時間ごとに最新確定日を取得 → `data/history.json` に upsert（日次用） |
| `backfill.py` | 過去日を一括取得（`START`日から今日まで）。一度きりの遡り用。ウェイト入り |
| `build.py` | `history.json` を読み、全日付データをJSONで埋め込んだ `docs/index.html` を生成 |
| `.github/workflows/update.yml` | **【本番】cron(JST10:00)で fetch→build→自動コミット→Pagesデプロイをクラウド実行。PC不要** |
| `.github/workflows/deploy.yml` | main への手動 push で `docs/` を Pages にデプロイ（ローカル編集を反映する用） |
| `run.sh` | fetch → build → commit → push（旧launchd用。現在は不使用） |
| `docs/assets/dcl_logo.png` / `dcl_mark.png` | ヘッダーロゴ / ファビコン（ランキングサイトと共通） |
| `~/Library/LaunchAgents/com.sukeakiito.pococha-borders.plist` | 毎朝10:00トリガー |

### build.py の要点
- データを `__DATA__` などのプレースホルダ置換でHTMLに埋め込む（`str.format`だとJS/CSSの `{}` を全部エスケープする羽目になるので `.replace()` 方式）
- ランク表示順は `S6…E1` の固定配列
- カレンダーはバニラJSで自前描画。全日付がページ内にあるのでサーバ通信なしで日付切替
- 下限日は `MIN_DATE = "2026-07-01"`、上限は取得済み最新日

---

## 3. GitHub リポジトリ & Pages
1. 空リポジトリを作成（このプロジェクトは `dcl-events` アカウント下・Public）
2. `git init` → commit → `git push -u origin main`
3. **Pages を GitHub Actions ソースで有効化**（API例）：
   ```
   POST /repos/dcl-events/pococha-borders/pages  {"build_type":"workflow"}
   ```
4. `deploy.yml` は `upload-pages-artifact`（path: docs）→ `deploy-pages` の最小構成

### デプロイの落とし穴（ハマった点）
- **Pages有効化前に push すると deploy-pages が失敗**する。先に Pages を workflow ソースで有効化してから走らせる
- **失敗ジョブの「rerun-failed-jobs」はNG**。アーティファクト `github-pages` が二重になり `Multiple artifacts...` で再び失敗する。→ **新規run（`workflow_dispatch` か 新しい push）で回す**

---

## 4. スケジュール実行（クラウド・毎朝10:00）＝本番
`.github/workflows/update.yml` の `on.schedule.cron: '0 1 * * *'`（UTC 01:00 = **JST 10:00**）。`workflow_dispatch` で手動実行も可。

- 権限は `contents: write`（history.json/docs を自動コミット）＋ `pages: write` ＋ `id-token: write`
- ジョブ：checkout → setup-python → `python fetch.py && python build.py` → 変更あれば `github-actions[bot]` でコミット&push → upload-pages-artifact → deploy-pages
- **Actions が push する時は GITHUB_TOKEN のため deploy.yml は連鎖しない**（ループ防止）。だから update.yml 自身の中で deploy まで済ませる
- 実行ログ・手動起動：GitHub の Actions 画面 →「Daily update & deploy」
- ランナーのタイムゾーンは UTC。`fetch.py` は「今日から遡って最初にデータがある日」を採るのでTZに関係なく正しく動く

### 旧：launchd（現在は停止）
以前は Mac の `launchd`（`com.sukeakiito.pococha-borders.plist`／`StartCalendarInterval Hour:10`）が `run.sh` を叩いていたが、**Mac稼働に依存する**ためクラウドへ移行し `launchctl unload` で停止済み（plistは残置。復活は `launchctl load`）。**クラウドと二重に動かすと push が競合する**ので、両方同時に有効化しないこと。

---

## 5. 拡張したいとき
- **もっと過去まで**：`backfill.py` の `START` を早い日付に変えて1回実行 → `build.py` → push。`build.py` の `MIN_DATE` も合わせる
- **列や表示を変える**：`build.py` の `COLS`（JS側）とテンプレートを編集
- **前日比・月平均など**：`history.json` に全日分があるので `build.py` 側で算出して埋め込めば追加可能

---

## 参考：この構築で使ったスタック
Python 標準ライブラリのみ（`urllib`/`json`/`datetime`）・GitHub Actions・GitHub Pages・macOS launchd。外部依存ゼロなので Actions 側も `pip install` 不要。
