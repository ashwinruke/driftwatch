import os
import time

import httpx
import jwt


def load_private_key() -> str:
    if "GITHUB_PRIVATE_KEY" in os.environ:
        return os.environ["GITHUB_PRIVATE_KEY"].replace("\\n", "\n")

    key_path = os.environ["GITHUB_PRIVATE_KEY_PATH"]
    if "PRIVATE KEY" in key_path or len(key_path) > 512:
        # A misconfigured env var can put the actual key contents here
        # instead of a path. Fail with a clean message instead of letting
        # open()'s FileNotFoundError embed the key material in its error
        # string, which would then land in logs via logger.exception().
        raise RuntimeError(
            "GITHUB_PRIVATE_KEY_PATH appears to contain key material, not a "
            "file path. If you meant to provide the key contents directly, "
            "set GITHUB_PRIVATE_KEY instead."
        )
    with open(key_path, "r") as f:
        return f.read()


def get_installation_token(app_id: str, installation_id: str) -> str:
    private_key = load_private_key()
    now = int(time.time())
    payload = {"iat": now - 60, "exp": now + 600, "iss": app_id}
    encoded_jwt = jwt.encode(payload, private_key, algorithm="RS256")

    resp = httpx.post(
        f"https://api.github.com/app/installations/{installation_id}/access_tokens",
        headers={
            "Authorization": f"Bearer {encoded_jwt}",
            "Accept": "application/vnd.github+json",
        },
    )
    resp.raise_for_status()
    return resp.json()["token"]
