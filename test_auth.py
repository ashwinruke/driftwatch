import os
import httpx
from dotenv import load_dotenv
from github_auth import get_installation_token

load_dotenv()

token = get_installation_token(
    app_id=os.environ["GITHUB_APP_ID"],
    private_key_path=os.environ["GITHUB_PRIVATE_KEY_PATH"],
    installation_id=os.environ["GITHUB_INSTALLATION_ID"],
)

print("Got token:", token[:15] + "...")

# Replace with your actual test repo and a real PR number from it
owner = "ashwinruke"
repo = "Multithreaded_Web_Server"
pr_number = 2

resp = httpx.get(
    f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files",
    headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
)
resp.raise_for_status()

for f in resp.json():
    print(f["filename"])