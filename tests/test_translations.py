"""Translation file tests."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TRANSLATIONS = REPO_ROOT / "custom_components" / "g410_doorbell_event" / "translations"


def test_dutch_translation_has_same_keys_as_english() -> None:
    """Dutch translation should track the English key structure."""

    en = json.loads((TRANSLATIONS / "en.json").read_text())
    nl = json.loads((TRANSLATIONS / "nl.json").read_text())
    assert nl.keys() == en.keys()
    assert nl["config"].keys() == en["config"].keys()
    assert nl["config"]["step"].keys() == en["config"]["step"].keys()
    assert nl["config"]["abort"].keys() == en["config"]["abort"].keys()
