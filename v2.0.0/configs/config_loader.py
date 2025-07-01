# config_loader.py
import json
from pathlib import Path

class ConfigLoader:
    @staticmethod
    def load(config_path: str) -> dict:
        with open(Path(config_path)) as f:
            return json.load(f)