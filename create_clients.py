import requests

API_URL = "https://clarion-backend-g1ls.onrender.com"
ADMIN_KEY = "clarion_super_secret_928374982374"

email = input("Email: ")
password = input("Password: ")

res = requests.post(
    f"{API_URL}/create-user",
    headers={
        "Content-Type": "application/json",
        "x-admin-key": ADMIN_KEY
    },
    json={
        "email": email,
        "password": password
    }
)

print(res.json())