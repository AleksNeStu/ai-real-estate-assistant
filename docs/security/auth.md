# AI Real Estate Assistant — Authentication

**FastAPI JWT (stateless Bearer tokens)** per the standard Large-SaaS pattern.
- `python-jose[cryptography]` + `passlib[bcrypt]` (rounds=12, 72-byte truncation).
- FastAPI `Depends(get_current_user)` in `apps/api/auth.py`.
- Conversation session tokens (longer-lived than access tokens) for chat continuity.

## Env vars

See [docs/env.md](../configuration/env.md): `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`.
