> 📌 最終更新: 2026-07-30（新規作成：ランクボーダー早見表サイトの構築手順＝ゼロから作り直す/引き継ぐ用の技術ガイド）／オーナー: sukeaki.ito

# Pococha ランクボーダー早見表 ― 作り方（構築ガイド）

DeNA Creator Links の「Pococha ランクボーダー早見表」（→使い方は同フォルダの `Pocochaランクボーダー早見表.md`）を、ゼロから作り直す／別の人が引き継ぐための技術手順。Claude Code で再現できるように書いてある。

---

## 0. 全体像
UPSTAR という外部サイトが公開している Pococha ランクボーダーのデータ（Firebase Cloud Function・認証不要）を毎朝取得し、静的HTMLに整形して GitHub Pages で公開する。ローカルの `launchd` が毎朝10:00に一連を実行する。

```
launchd(毎朝10:00) → run.sh
  ├ fetch.py   … UPSTAR API から当日ぶん取得 → data/history.json に蓄積
  ├ build.py   … history.json → docs/index.html（全日付データ埋め込み＋カレンダーUI）
  └ git push   → GitHub Actions(deploy.yml) が docs/ を Pages へデプロイ
```

- プロジェクト：`~/Claude/pococha-borders`（sukeaki の Mac）
- リポジトリ：`github.com/dcl-events/pococha-borders`（Public）
- 公開URL：`https://dcl-events.github.io/pococha-borders/`

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
| `run.sh` | fetch → build → 変更あれば commit → push（launchd から実行） |
| `.github/workflows/deploy.yml` | main への push で `docs/` を GitHub Pages にデプロイ |
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

## 4. launchd（毎朝10:00）
`~/Library/LaunchAgents/com.sukeakiito.pococha-borders.plist` に `StartCalendarInterval {Hour:10, Minute:0}`。ProgramArguments で `run.sh` を叩く。

```
launchctl load  ~/Library/LaunchAgents/com.sukeakiito.pococha-borders.plist
launchctl list | grep pococha-borders            # 登録確認
launchctl kickstart -k gui/$(id -u)/com.sukeakiito.pococha-borders  # 手動テスト
```
- ログ：`~/Claude/pococha-borders/logs/borders.{out,err}.log`
- git push は osxkeychain の認証を使う（launchdのGUIセッションから通ることを実証済み）
- リポジトリに `git config user.name/email` をローカル設定しておく（未設定だと commit が失敗する）

---

## 5. 拡張したいとき
- **もっと過去まで**：`backfill.py` の `START` を早い日付に変えて1回実行 → `build.py` → push。`build.py` の `MIN_DATE` も合わせる
- **列や表示を変える**：`build.py` の `COLS`（JS側）とテンプレートを編集
- **前日比・月平均など**：`history.json` に全日分があるので `build.py` 側で算出して埋め込めば追加可能

---

## 参考：この構築で使ったスタック
Python 標準ライブラリのみ（`urllib`/`json`/`datetime`）・GitHub Actions・GitHub Pages・macOS launchd。外部依存ゼロなので Actions 側も `pip install` 不要。
