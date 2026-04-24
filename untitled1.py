import requests

API = "https://clarion-backend-g1ls.onrender.com"

ADMIN_KEY = "supersecret123"

headers = {
    "x-admin-key": ADMIN_KEY,
    "Content-Type": "application/json"
}

clients = [
    {"email": "client1@test.com", "password": "pass123"},
    {"email": "client2@test.com", "password": "pass123"},
    {"email": "client3@test.com", "password": "pass123"},
]

for c in clients:
    res = requests.post(f"{API}/create-user", json=c, headers=headers)
    print(c["email"], res.json())