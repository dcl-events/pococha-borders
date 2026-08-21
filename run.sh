#!/bin/bash
# 毎日10:00 launchd から実行：取得 → 生成 → GitHub へ push（Pages自動デプロイ）
set -euo pipefail
cd "$(dirname "$0")"

export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"

echo "===== $(date '+%Y-%m-%d %H:%M:%S') 取得開始 ====="
python3 fetch.py
python3 build.py

# ope公式APIベースの翌日予測（ローカルのみ・.token必須）。失敗しても本体更新は止めない。
# GitHub Actions ランナーには .token/履歴が無いので、生成物 data/prediction.json をコミットして共有する。
POCO="$HOME/Claude/pococha"
if [[ -f "$POCO/.token" ]]; then
  python3 "$POCO/borders_backfill.py" "$(date -v-3d +%Y%m%d)" "$(date +%Y%m%d)" || echo "⚠ ボーダー履歴の更新に失敗（予測は前回値を使用）"
  python3 "$POCO/borders_predict.py" --export-json data/prediction.json || echo "⚠ 予測JSONの生成に失敗"
else
  echo "⚠ $POCO/.token が無いため予測JSONは更新せず（前回のコミット値を使用）"
fi

python3 build_trend.py

# 変更があれば commit & push
if [[ -n "$(git status --porcelain)" ]]; then
  git add -A
  git commit -m "chore: update borders $(date '+%Y-%m-%d')"
  git push origin main
  echo "push 完了"
else
  echo "変更なし（push スキップ）"
fi
echo "===== 完了 ====="
