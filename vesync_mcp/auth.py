"""Login: exchange your VeSync email + password for a token (saved locally).

Uses the `pyvesync` library for the authentication flow. Your password is only
used to obtain the token and is never stored — only the token and account id
are written to the credentials file.
"""
from __future__ import annotations

import asyncio
import json
import os


def login(email: str, password: str, *, country_code: str = "US",
          time_zone: str = "UTC", out_path: str) -> str:
    """Authenticate and write the token to ``out_path``. Returns the path."""
    try:
        from pyvesync import VeSync
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("pyvesync is required for login: pip install pyvesync") from e

    async def _run():
        async with VeSync(email, password, country_code=country_code, time_zone=time_zone) as m:
            ok = await m.login()
            if not ok:
                raise RuntimeError(
                    "VeSync rejected the login. Check email/password. "
                    "VeSync sometimes rate-limits logins (Cloudflare) — if so, wait and retry."
                )
            return m.token, m.account_id

    token, account_id = asyncio.run(_run())
    data = {"token": token, "account_id": account_id,
            "time_zone": time_zone, "country_code": country_code}
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    try:
        os.chmod(out_path, 0o600)
    except OSError:
        pass
    return out_path
