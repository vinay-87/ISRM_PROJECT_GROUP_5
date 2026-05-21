import re
import os

import requests


URL = os.getenv("LOGIN_URL", "http://127.0.0.1:5001/login")
USERNAME = "admin"
PASSWORDS = [
    "password",
    "admin",
    "123456",
    "Student@123",
    "wrong-again",
    "Admin@123",
]


def csrf_token(html):
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    if not match:
        raise RuntimeError("Could not find CSRF token on login page")
    return match.group(1)


session = requests.Session()

for password in PASSWORDS:
    login_page = session.get(URL, timeout=5)
    token = csrf_token(login_page.text)
    response = session.post(
        URL,
        data={"username": USERNAME, "password": password, "csrf_token": token},
        allow_redirects=False,
        timeout=5,
        proxies={"http": None, "https": None},
    )
    print(
        f"Tried {USERNAME}:{password} -> "
        f"status={response.status_code}, location={response.headers.get('Location')}"
    )
    if response.status_code == 429:
        print("Rate limit triggered: brute-force protection is working.")
        break
    if response.status_code == 302 and response.headers.get("Location") == "/dashboard":
        print("Login succeeded before rate limit. Move the real password later in the list for the demo.")
        break
