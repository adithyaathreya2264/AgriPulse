import os
import json
import subprocess
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("AGMARKNET_API_KEY")

url = (
    "https://api.data.gov.in/resource/"
    "9ef84268-d588-465a-a308-a864a43d0070"
)

params = (
    f"api-key={API_KEY}"
    "&format=json"
    "&offset=0"
    "&limit=100"
    "&filters%5Bstate.keyword%5D=Karnataka"
)

full_url = f"{url}?{params}"

result = subprocess.run(
    [
        "curl.exe",
        "-s",
        full_url
    ],
    capture_output=True,
    text=True,
    timeout=120
)

if result.returncode != 0:
    print("Curl error:")
    print(result.stderr)
    exit()

data = json.loads(result.stdout)

print("Status:", data.get("status"))
print("Total:", data.get("total"))

for item in data.get("records", []):
    print(
        item["commodity"],
        "|",
        item["market"],
        "| ₹",
        item["modal_price"]
    )