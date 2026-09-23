from driftwatch.github.client import post


def post_pr_comment(owner: str, repo: str, pr_number: int, token: str, body: str) -> dict:
    return post(f"/repos/{owner}/{repo}/issues/{pr_number}/comments", token, json={"body": body})


def post_review_comment(
    owner: str,
    repo: str,
    pr_number: int,
    token: str,
    commit_id: str,
    path: str,
    line: int,
    body: str,
) -> dict:
    """Post a line-anchored PR review comment. `line` must be a line that's
    actually part of the diff (see ast.parser.find_anchor_line), or GitHub
    rejects the request."""
    return post(
        f"/repos/{owner}/{repo}/pulls/{pr_number}/comments",
        token,
        json={
            "commit_id": commit_id,
            "path": path,
            "line": line,
            "side": "RIGHT",
            "body": body,
        },
    )
