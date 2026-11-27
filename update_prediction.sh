#!/bin/bash
# 予測レンジ専用ルーティン（launchd 毎日14:00）：
#   ope公式APIベースの翌日予測だけを作り直して公開する。折れ線グラフ本体(UPSTAR)は10:00の run.sh 側。
#   クラウドの自動更新コミットと衝突しないよう、最初に origin/main へ同期してから再生成する。
set -uo pipefail
cd "$(dirname "$0")"
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"
POCO="$HOME/Claude/pococha"

echo "===== $(date '+%Y-%m-%d %H:%M:%S') 予測レンジ更新 開始 ====="

# ope APIトークンが無ければ何もしない（履歴・予測は前回のコミット値のまま）
if [[ ! -f "$POCO/.token" ]]; then
  echo "⚠ $POCO/.token が無いため中止（前回のコミット値を維持）"; exit 0
fi

# 1) クラウドの最新を取り込む（生成物は後で作り直すので hard reset で確実に同期）
if ! git fetch origin -q; then echo "⚠ git fetch 失敗。中止"; exit 1; fi
git reset --hard origin/main -q
echo "origin/main へ同期: $(git log --oneline -1)"

# 2) ope履歴を直近まで更新（403等で失敗しても前回値で継続）
python3 "$POCO/borders_backfill.py" "$(date -v-3d +%Y%m%d)" "$(date +%Y%m%d)" \
  || echo "⚠ ボーダー履歴の更新に失敗（前回の履歴で予測を作成）"

# 3) 予測JSONを生成（ここが本体。失敗したら公開はしない）
if ! python3 "$POCO/borders_predict.py" --export-json data/prediction.json; then
  echo "⚠ 予測JSONの生成に失敗。中止"; exit 1
fi

# 4) 推移ページを再生成（予測カードに反映）
python3 build_trend.py

# 5) 差分があれば commit & push。
#    Pages は「ブランチ公開(main:/docs)」なので、push すれば GitHub 純正ビルドが自動配信する。
if [[ -n "$(git status --porcelain)" ]]; then
  git add -A
  git commit -q -m "chore(pred): 予測レンジ更新 $(date '+%Y-%m-%d %H:%M')"
  if git push origin main; then echo "push 完了（Pages 自動配信）"; else echo "⚠ push 失敗"; exit 1; fi
else
  echo "変更なし（push スキップ）"
fi

# 本体(UPSTAR)更新はクラウド update.yml が担当。GitHubのscheduleは不発しがちなので、
# 毎朝このMacジョブ(10:05)から確実に起動する（PCを閉じた朝はGitHub scheduleが保険）。
TOK=$(printf "protocol=https\nhost=github.com\n\n" | git credential fill 2>/dev/null | sed -n 's/^password=//p')
if [[ -n "$TOK" ]]; then
  code=$(curl -s -o /dev/null -w '%{http_code}' -X POST \
    -H "Authorization: token $TOK" -H "Accept: application/vnd.github+json" \
    https://api.github.com/repos/dcl-events/pococha-borders/actions/workflows/update.yml/dispatches \
    -d '{"ref":"main"}')
  echo "本体更新(update.yml)を起動 (HTTP $code)"
else
  echo "⚠ token取得不可：本体更新は未起動（GitHub scheduleの発火を待つ）"
fi
echo "===== 完了 ====="
