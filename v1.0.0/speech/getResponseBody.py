import json
import requests
from requests.exceptions import RequestException
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_dir, "config.json")
try:
    with open(config_path, "r", encoding="utf-8") as f:
        #------------------------用户自定义数据
        config = json.load(f)
        token = config.get("Token")
        base_url = config.get("fat_base_url")
        #------------------------用户自定义数据
    if not token or not base_url:
        raise ValueError("Token or base_url is missing in config.json")
except Exception as e:
    print(f"Error loading config: {e}")
    exit(1)
headers = {"Token": token,"Content-Type": "application/json"}

def getResponseBody(body):
    try:
        response = requests.post(url = base_url, headers=headers, json=body)
        response.raise_for_status()  # Raise an error for HTTP errors
        return response.json()
    except RequestException as e:
        print(f"Request failed: {e}")
        return {"error": str(e)}
