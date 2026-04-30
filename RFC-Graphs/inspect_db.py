import requests

url = "https://mailarchive.ietf.org/api/v1/stats/msg_counts/"

params = {
    "start": "20250101",
    "end": "20251231",
}

r = requests.get(url, params=params)
print(r.status_code)
print(r.json())