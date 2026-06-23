import requests

CLIENT_ID = "APP-EX4LO9JF529CG4F0"
CLIENT_SECRET = "tu_secret"

token_url = "https://sandbox.orcid.org/oauth/token"

data = {
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "grant_type": "client_credentials",
    "scope": "/read-public"
}

r = requests.post(token_url, data=data)

print(r.status_code)
print(r.text)