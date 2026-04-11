import json
import logging
import os

log = logging.getLogger(__name__)

# Cache for locales: { 'en': { ... }, 'tr': { ... } }
_locales = {}
# Guild language cache: { guild_id: 'en' | 'tr' }
_guild_languages = {}

def load_locales():
    """Load all JSON files from the locales directory into memory."""
    locales_dir = os.path.join(os.path.dirname(__file__), "..", "locales")
    if not os.path.exists(locales_dir):
        log.warning("Locales directory not found at %s", locales_dir)
        return

    for filename in os.listdir(locales_dir):
        if filename.endswith(".json"):
            lang = filename[:-5]
            try:
                with open(os.path.join(locales_dir, filename), "r", encoding="utf-8") as f:
                    _locales[lang] = json.load(f)
                log.info("Loaded locale: %s", lang)
            except Exception:
                log.exception("Failed to load locale: %s", lang)

def get(guild_id: int, key: str, **kwargs) -> str:
    """
    Get a translated string for a guild.
    Supports dot notation (e.g. "war.title").
    Fallbacks: guild_lang -> 'en' -> raw key.
    """
    lang = _guild_languages.get(guild_id, "en")
    
    # Try requested language
    text = _resolve_key(lang, key)
    
    # Fallback to English
    if text is None and lang != "en":
        text = _resolve_key("en", key)
        
    if text is None:
        log.warning("Translation key not found: %s", key)
        return key
        
    try:
        return text.format(**kwargs)
    except Exception:
        log.exception("Error formatting translation for key: %s", key)
        return text

def _resolve_key(lang: str, key: str):
    """Internal helper to resolve a dot-notation key in the locale dict."""
    if lang not in _locales:
        return None
        
    parts = key.split(".")
    data = _locales[lang]
    
    for part in parts:
        if isinstance(data, dict) and part in data:
            data = data[part]
        else:
            return None
    
    return data if isinstance(data, str) else None

def set_guild_language(guild_id: int, lang: str):
    """Set the language for a guild in the in-memory cache."""
    if lang in _locales:
        _guild_languages[guild_id] = lang
    else:
        log.warning("Attempted to set unknown language: %s", lang)

def get_guild_language(guild_id: int) -> str:
    """Get the currently cached language for a guild."""
    return _guild_languages.get(guild_id, "en")

# Auto-load on import
load_locales()
