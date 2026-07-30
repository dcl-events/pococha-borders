#!/bin/bash
# 毎日10:00 launchd から実行：取得 → 生成 → GitHub へ push（Pages自動デプロイ）
set -euo pipefail
cd "$(dirname "$0")"

export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"

echo "===== $(date '+%Y-%m-%d %H:%M:%S') 取得開始 ====="
python3 fetch.py
python3 build.py

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
