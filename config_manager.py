import os
import json
from typing import Dict, Any

class ConfigManager:
    """Manages configuration settings for the bot."""
    
    CONFIG_FILE = "bot_config.json"
    
    def __init__(self):
        """Initialize the ConfigManager with empty guild configs."""
        # Configuration storage - per guild settings
        self.guild_configs: Dict[int, Dict[str, Any]] = {}
    
    def load_config(self) -> None:
        """Load configuration from file."""
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r') as f:
                    # JSON stores keys as strings, convert back to int for guild IDs
                    loaded_config = json.load(f)
                    self.guild_configs = {int(k): v for k, v in loaded_config.items()}
                    print(f"Loaded configuration for {len(self.guild_configs)} guilds")
        except Exception as e:
            print(f"Error loading configuration: {e}")
    
    def save_config(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.guild_configs, f)
        except Exception as e:
            print(f"Error saving configuration: {e}")
    
    def get_guild_config(self, guild_id: int) -> Dict[str, Any]:
        """Get configuration for a specific guild."""
        return self.guild_configs.get(guild_id, {}) if guild_id else {}
    
    def update_guild_config(self, guild_id: int, key: str, value: Any) -> None:
        """Update a specific configuration value for a guild."""
        if guild_id not in self.guild_configs:
            self.guild_configs[guild_id] = {}
        
        self.guild_configs[guild_id][key] = value
        self.save_config()
