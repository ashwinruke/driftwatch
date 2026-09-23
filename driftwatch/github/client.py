"""Thin shared helpers for calling the GitHub API, factored out of the
near-identical httpx calls that used to be duplicated across the diff
extractor, doc indexer, and PR commenter."""

import httpx

GITHUB_API = "https://api.github.com"


def auth_headers(token: str, accept: str = "application/vnd.github+json") -> dict:
    return {"Authorization": f"Bearer {token}", "Accept": accept}


def get(path: str, token: str) -> httpx.Response:
    """GET a GitHub API path (relative to api.github.com), raising on error."""
    resp = httpx.get(f"{GITHUB_API}{path}", headers=auth_headers(token))
    resp.raise_for_status()
    return resp


def get_optional(path: str, token: str) -> httpx.Response:
    """GET a GitHub API path without raising, so callers can inspect status_code."""
    return httpx.get(f"{GITHUB_API}{path}", headers=auth_headers(token))


def get_content(download_url: str, token: str) -> str:
    """GET raw text content from an absolute URL (e.g. a file's download_url)."""
    return httpx.get(download_url, headers={"Authorization": f"Bearer {token}"}).text


def post(path: str, token: str, json: dict) -> dict:
    resp = httpx.post(f"{GITHUB_API}{path}", headers=auth_headers(token), json=json)
    resp.raise_for_status()
    return resp.json()
