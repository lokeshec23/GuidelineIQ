import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request("http://127.0.0.1:8003/auth/register", method="POST")
req.add_header('Content-Type', 'application/json')
data = json.dumps({
    "username": "lokesh",
    "email": "lokesh_test_verify@loandna.com",
    "password": "password123",
    "role": "user"
}).encode('utf-8')

try:
    with urllib.request.urlopen(req, data=data, context=ctx) as response:
        print("SUCCESS:", response.read().decode())
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.read().decode()}")
except Exception as e:
    print("Error:", e)
