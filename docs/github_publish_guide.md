# GitHub Publish Guide

The repository already has a local release commit and tag. To publish to a GitHub repository:

```powershell
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin master
git push origin v1.0.0-harness
```

If `origin` already exists:

```powershell
git remote -v
git push
git push origin v1.0.0-harness
```

## Pre-Push Checks

```powershell
git status
git log -1 --oneline
git tag
git ls-files
git grep -n -i "api_key"
git grep -n -i "secret"
git grep -n -i "sk-"
git ls-files | Select-String -Pattern "\.env$|\.mp4$|\.wav$|data/raw|outputs/"
```

Do not push if `.env`, raw media, outputs, model caches, or real credentials appear in tracked files.

Do not use `git push --force`, `git reset --hard`, or rewrite tags unless explicitly required.
