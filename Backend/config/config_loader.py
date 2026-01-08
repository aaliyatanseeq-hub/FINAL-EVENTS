"""
Configuration Loader
Loads configuration from JSON files instead of hardcoding values
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Any

def load_config(config_file: str = "attendee_config.json") -> Dict[str, Any]:
    """
    Load configuration from JSON file
    Falls back to empty dict if file not found (graceful degradation)
    """
    try:
        # Get the config directory path
        current_dir = Path(__file__).parent
        config_path = current_dir / config_file
        
        if not config_path.exists():
            print(f"⚠️ Config file not found: {config_path}")
            print(f"   Using empty configuration (some features may not work)")
            return {}
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"✅ Loaded configuration from {config_file}")
        return config
    
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing config file {config_file}: {e}")
        return {}
    except Exception as e:
        print(f"❌ Error loading config file {config_file}: {e}")
        return {}

def get_config_value(config: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Get a configuration value with fallback to default"""
    return config.get(key, default)

# Load configuration at module level
_config = load_config()

# Export configuration values
COUNTRY_KEYWORDS = _config.get('country_keywords', {})
SPORTS_VENUES = _config.get('sports_venues', {})
COUNTRY_NAMES = _config.get('country_names', {})
ENGAGEMENT_PHRASES = _config.get('engagement_phrases', [])
STRONG_ENGAGEMENT = _config.get('strong_engagement', [])
MEDIUM_ENGAGEMENT = _config.get('medium_engagement', [])
STOP_WORDS = set(_config.get('stop_words', []))
PREFIXES = _config.get('prefixes', [])
INVALID_VALUES = _config.get('invalid_values', [])
INVALID_PATTERNS = _config.get('invalid_patterns', [])
LOCATION_KEYWORDS = _config.get('location_keywords', [])
LOCATION_PATTERNS = _config.get('location_patterns', [])
BIO_NONSENSE_PATTERNS = _config.get('bio_nonsense_patterns', [])






