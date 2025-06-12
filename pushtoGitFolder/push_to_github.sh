#!/bin/bash

# Set these values
REPO_NAME="Capstone"
# === File Info ===

REMOTE_FILE_PATH="index.html"
COMMIT_MESSAGE="Add or update file via API"
COMMITTER_NAME="odl-user-1750231"
COMMITTER_EMAIL="odl_user_1750231@sandboxailabs1011.onmicrosoft.com"
GITHUB_USERNAME="odl-user-1750231"
GITHUB_REPO="Capstone"
FILE_PATH="local-file.txt"
LOCAL_FILE_PATH="C:\Users\demouser\Desktop\github_test\htmlfile\index.html"
GITHUB_TOKEN="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"
COMMIT_MESSAGE="Add file via API"
BRANCH="main"
REMOTE_PATH="index.html"
COMMIT_MESSAGE="Upload file via GitHub API"


ENCODED_CONTENT=$(base64 -w 0 "$LOCAL_FILE_PATH")

# === GitHub API endpoint ===
API_URL="https://api.github.com/repos/$GITHUB_USERNAME/$REPO_NAME/contents/$REMOTE_FILE_PATH"

# === Get existing file SHA (if file already exists) ===
EXISTING_SHA=$(curl -s -H "Authorization: Bearer $GITHUB_TOKEN" "$API_URL" | grep '"sha"' | head -n 1 | cut -d '"' -f 4)

# === Create JSON payload ===
if [[ -z "$EXISTING_SHA" ]]; then
  # New file
  JSON_PAYLOAD=$(cat <<EOF
{
  "message": "$COMMIT_MESSAGE",
  "committer": {
    "name": "$COMMITTER_NAME",
    "email": "$COMMITTER_EMAIL"
  },
  "content": "$ENCODED_CONTENT",
  "branch": "$BRANCH"
}
EOF
)
else
  # Existing file (update)
  JSON_PAYLOAD=$(cat <<EOF
{
  "message": "$COMMIT_MESSAGE",
  "committer": {
    "name": "$COMMITTER_NAME",
    "email": "$COMMITTER_EMAIL"
  },
  "content": "$ENCODED_CONTENT",
  "sha": "$EXISTING_SHA",
  "branch": "$BRANCH"
}
EOF
)
fi

# === Make the API request ===
curl -L \
  -X PUT \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "$API_URL" \
  -d "$JSON_PAYLOAD"