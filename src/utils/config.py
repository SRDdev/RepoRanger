"""
Docstring for src.utils.config
"""
import yaml
import os
from typing import Dict, Any

class Config:
    _instance = None
    _config_data = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        config_path = os.getenv("CONFIG_PATH", "config.yaml")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found at: {config_path}")
        
        with open(config_path, "r") as f:
            self._config_data = yaml.safe_load(f)

    def get(self, path: str, default: Any = None) -> Any:
        """
        Access config using dot notation, e.g., config.get('llm.default.model')
        """
        keys = path.split(".")
        value = self._config_data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

# Global instance for easy import
cfg = Config()