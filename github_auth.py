import time
import jwt
import httpx
import os


def load_private_key() -> str:
    if "GITHUB_PRIVATE_KEY" in os.environ:
        return os.environ["GITHUB_PRIVATE_KEY"].replace("\\n", "\n")
    with open(os.environ["GITHUB_PRIVATE_KEY_PATH"], "r") as f:
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