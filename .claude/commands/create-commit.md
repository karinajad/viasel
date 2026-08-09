---
description: Stage, commit, and push all current changes with a descriptive commit message
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git add:*), Bash(git commit:*), Bash(git push:*)
---

# Create Commit

## Current Status
!`git status`

## What Changed
!`git diff HEAD`

---

## Instructions

1. Review the diff above to understand what was changed and why.
2. Stage all changes:
   ```
   git add .
   ```
3. Write a concise, descriptive commit message based on the actual changes — not generic ("update files"). Lead with a verb: "Add", "Fix", "Update", "Remove". One line, under 72 characters.
4. Commit:
   ```
   git commit -m "[your message]"
   ```
5. Push:
   ```
   git push
   ```
