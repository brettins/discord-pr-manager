#!/bin/bash
# Pulls origin/main onto the droplet and restarts the bot, but only for commits
# whose GitHub Actions checks have all passed. Driven by prbot-deploy.timer.
set -euo pipefail

REPO_DIR=/home/prbot/discord-pr-manager
BRANCH=main
API=https://api.github.com/repos/brettins/discord-pr-manager

cd "$REPO_DIR"

current_branch=$(git symbolic-ref --short HEAD)
if [ "$current_branch" != "$BRANCH" ]; then
    echo "on '$current_branch', not '$BRANCH' - skipping"
    exit 0
fi

git fetch --quiet origin "$BRANCH"
local_sha=$(git rev-parse HEAD)
remote_sha=$(git rev-parse "origin/$BRANCH")

if [ "$local_sha" = "$remote_sha" ]; then
    exit 0
fi

if ! checks=$(curl -fsSL --max-time 20 "$API/commits/$remote_sha/check-runs"); then
    echo "could not reach GitHub check-runs API - will retry"
    exit 0
fi

verdict=$(printf '%s' "$checks" | python3 -c '
import json, sys
runs = json.load(sys.stdin).get("check_runs", [])
if not runs:
    print("none")
elif any(r.get("status") != "completed" for r in runs):
    print("pending")
elif all(r.get("conclusion") == "success" for r in runs):
    print("success")
else:
    print("failed")
')

if [ "$verdict" != "success" ]; then
    echo "checks for ${remote_sha:0:8} are '$verdict' - not deploying"
    exit 0
fi

echo "deploying ${local_sha:0:8} -> ${remote_sha:0:8}"
git merge --ff-only "origin/$BRANCH"
bot-env/bin/pip install --quiet --disable-pip-version-check -r requirements.txt
sudo /usr/bin/systemctl restart prbot.service
echo "deployed ${remote_sha:0:8}"
