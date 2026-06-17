"""
memory.py

Style Profile Memory (stretch feature).

Stores a user's style preferences across interactions so a later query can
benefit from earlier ones without the user re-entering anything. The profile is
a small JSON file on disk (style_profile.json) holding the style tags FitFindr
has seen the user gravitate toward, with a count for each so stronger
preferences rank higher.

Flow:
    profile = load_profile()                      # read prior preferences (or empty)
    update_profile(profile, item, parsed)         # learn from this interaction
    save_profile(profile)                         # persist for next time
    preferred_style_tags(profile)                 # read top tags to bias next search
"""

import json
import os

_PROFILE_PATH = os.path.join(os.path.dirname(__file__), "style_profile.json")

# Words a user commonly types that are also style_tags worth remembering.
_KNOWN_STYLE_WORDS = {
    "vintage", "y2k", "90s", "2000s", "grunge", "cottagecore", "streetwear",
    "minimal", "preppy", "goth", "boho", "athletic", "western", "denim",
    "floral", "graphic", "earth tones", "classic", "feminine", "dark academia",
}


def load_profile(path: str | None = None) -> dict:
    """Load the saved style profile, or return a fresh empty one."""
    path = path or _PROFILE_PATH
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data.setdefault("style_tags", {})
            data.setdefault("interactions", 0)
            return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"style_tags": {}, "interactions": 0}


def save_profile(profile: dict, path: str | None = None) -> None:
    """Persist the style profile to disk."""
    path = path or _PROFILE_PATH
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)


def update_profile(profile: dict, selected_item: dict | None, parsed: dict | None) -> dict:
    """
    Learn style preferences from one interaction.

    Counts the style tags of the item the user actually engaged with, plus any
    style words found in their raw query/description. Mutates and returns the
    profile.
    """
    counts = profile.setdefault("style_tags", {})

    if selected_item:
        for tag in (selected_item.get("style_tags") or []):
            key = tag.lower().strip()
            if key:
                counts[key] = counts.get(key, 0) + 1

    description = ((parsed or {}).get("description") or "").lower()
    for word in _KNOWN_STYLE_WORDS:
        if word in description:
            counts[word] = counts.get(word, 0) + 1

    profile["interactions"] = profile.get("interactions", 0) + 1
    return profile


def preferred_style_tags(profile: dict, limit: int = 3) -> list[str]:
    """Return the user's most-preferred style tags, strongest first."""
    counts = (profile or {}).get("style_tags", {})
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [tag for tag, _ in ranked[:limit]]


def clear_profile(path: str | None = None) -> None:
    """Delete the saved profile (used to reset between demos/tests)."""
    path = path or _PROFILE_PATH
    if os.path.exists(path):
        os.remove(path)
