from fastapi import Header, HTTPException

from app.config import settings


def require_token(x_api_key: str | None = Header(default=None)) -> None:
    """Shared-key auth for the API. Closes the open-backend hole.

    Not per-user auth — a single key the frontend sends as X-API-Key. Swap for
    real user auth when there are real users.
    """
    if x_api_key != settings.API_TOKEN:
        raise HTTPException(status_code=401, detail="invalid or missing API key")
