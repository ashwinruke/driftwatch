import requests

API_KEY = "sk-live-51Hxyz1234567890abcdefghijklmno"


def fetch_data():
    return requests.get(
        "https://api.example.com/data",
        headers={"Authorization": f"Bearer {API_KEY}"},
    )
