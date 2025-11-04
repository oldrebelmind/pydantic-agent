#!/bin/bash
# Workaround for WSL /mnt/d path resolution issue
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" > /dev/null 2>&1
ORIG_PWD="$PWD"
# If we're in a /mnt/* directory, change to home to avoid path resolution issues
# but preserve the original directory in an env var for claude to use
if [[ "$ORIG_PWD" =~ ^/mnt/ ]]; then
    cd ~ 2>/dev/null || cd /tmp
    # Set PWD to safe directory to avoid Node.js realpathSync issues
    export PWD="$HOME"
    # If claude needs the original directory, it can use ORIG_PWD env var
    export CLAUDE_ORIGINAL_DIR="$ORIG_PWD"
fi
nvm use 22.18.0 > /dev/null 2>&1 || true
# Use full path to claude to avoid PATH resolution issues
CLAUDE_PATH="$HOME/.nvm/versions/node/v22.18.0/bin/claude"
# Run claude from safe directory - it will access files via absolute paths
exec "$CLAUDE_PATH" "$@"
