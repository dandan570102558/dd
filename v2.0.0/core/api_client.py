import json
from pathlib import Path
import requests
from requests.exceptions import RequestException

class APIClient:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.base_headers = {
            "Token": self.config["Token"],
            "Content-Type": "application/json"
        }
    
    def _load_config(self, config_path: str) -> dict:
        """安全加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                required_keys = ["Token", "fat_base_url", "bizName_2", "bizName_3"]
                if not all(k in config for k in required_keys):
                    raise ValueError(f"Missing required keys in config: {required_keys}")
                return config
        except Exception as e:
            raise RuntimeError(f"Config loading failed: {str(e)}")

    def post(self, endpoint: str, body: dict) -> dict:
        """发送API请求"""
        try:
            response = requests.post(
                url=f"{self.config['fat_base_url']}/{endpoint}",
                headers=self.base_headers,
                json=body,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            raise RuntimeError(f"API request failed: {str(e)}")