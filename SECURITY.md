# Security Policy

## Reporting a secret leak

If an API Key, object-storage credential, access token, database, or user media is exposed, revoke or rotate it immediately in the provider console. Do not post the secret in an issue.

## Repository rules

- Never commit `backend/.env`, `backend/db.sqlite3`, `backend/media/`, logs, screenshots containing keys, or production exports.
- Keep all provider keys on the Django server. The Vue app may call only `/api`.
- Review `git status --ignored` and `git diff --cached` before every push.
- Treat voice samples as sensitive personal information; collect explicit authorization before cloning and delete them when no longer required.
