import requests

API_URL = "https://clarion-backend-glls.onrender.com"
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

print("STATUS:", res.status_code)
print("RAW RESPONSE:", res.text)