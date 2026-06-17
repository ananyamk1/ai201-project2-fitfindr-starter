"""
test_stretch.py

Tests for the four stretch features:
  - Price Comparison Tool      (compare_price)
  - Trend Awareness Tool       (get_trend_info + influence on suggest_outfit)
  - Style Profile Memory       (memory.py + run_agent(use_memory=True))
  - Retry Logic with Fallback  (agent._search_with_retry / run_agent)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import agent
import tools
from agent import _search_with_retry, run_agent
from memory import (
    clear_profile,
    load_profile,
    preferred_style_tags,
    update_profile,
)
from tools import compare_price, get_trend_info, search_listings
from utils.data_loader import get_example_wardrobe


# Reuse the fake-LLM client pattern from test_tools so suggest_outfit /
# create_fit_card don't make real API calls during agent tests.
class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, response_text):
        self.response_text = response_text
        self.last_request = None

    def create(self, **kwargs):
        self.last_request = kwargs
        return _FakeResponse(self.response_text)


class _FakeChat:
    def __init__(self, response_text):
        self.completions = _FakeCompletions(response_text)


class _FakeClient:
    def __init__(self, response_text):
        self.chat = _FakeChat(response_text)


def _fake_client_factory(response_text):
    def _factory():
        return _FakeClient(response_text)

    return _factory


# ── Price Comparison ────────────────────────────────────────────────────────

def test_compare_price_returns_assessment_and_reasoning():
    item = search_listings("vintage graphic tee", size=None, max_price=30)[0]
    result = compare_price(item)
    assert result["assessment"] in {
        "great deal", "fair price", "priced above market", "no comparison available"
    }
    assert isinstance(result["reasoning"], str) and result["reasoning"]
    assert result["comparable_count"] >= 1
    # reasoning must reference the comparison basis, not just a bare label
    assert "median" in result["reasoning"].lower()


def test_compare_price_flags_a_cheap_item_as_a_deal():
    # A synthetic ultra-cheap top should read as a great deal vs real comparables.
    cheap = {"id": "synthetic", "category": "tops", "style_tags": ["vintage"], "price": 1.0}
    result = compare_price(cheap)
    assert result["assessment"] == "great deal"


def test_compare_price_no_price_is_graceful():
    result = compare_price({"id": "x", "category": "tops", "style_tags": [], "price": None})
    assert result["assessment"] == "no comparison available"


# ── Trend Awareness ───────────────────────────────────────────────────────────

def test_get_trend_info_matches_style_tags():
    item = {"style_tags": ["vintage", "grunge"]}
    info = get_trend_info(item)
    assert "vintage" in info["matched_tags"]
    assert info["status"] in {"hot", "rising", "steady"}
    assert info["summary"]


def test_get_trend_info_falls_back_to_default():
    info = get_trend_info({"style_tags": ["no-such-tag-xyz"]})
    assert info["matched_tags"] == []
    assert info["summary"]  # default note still provided


def test_trend_context_reaches_suggest_outfit_prompt(monkeypatch):
    # Capture the prompt suggest_outfit sends so we can prove the trend influences it.
    fake = _FakeClient("Outfit text")
    monkeypatch.setattr(tools, "_get_groq_client", lambda: fake)

    item = search_listings("vintage graphic tee", size=None, max_price=30)[0]
    tools.suggest_outfit(item, get_example_wardrobe(), trend_context="Grunge is back in rotation.")

    sent = fake.chat.completions.last_request["messages"][-1]["content"]
    assert "Grunge is back in rotation." in sent


# ── Retry Logic with Fallback ───────────────────────────────────────────────

def test_retry_lifts_price_and_explains():
    results, note = _search_with_retry("vintage graphic tee", size=None, max_price=1.0)
    assert results, "retry should recover results after lifting the price ceiling"
    assert note is not None and "price" in note.lower()


def test_retry_returns_none_note_when_first_attempt_succeeds():
    results, note = _search_with_retry("vintage graphic tee", size=None, max_price=50.0)
    assert results
    assert note is None


def test_retry_gives_up_on_truly_absent_item():
    results, note = _search_with_retry("designer ballgown", size="XXS", max_price=5.0)
    assert results == []
    assert note is None  # falls through to the agent's standard no-results message


# ── Style Profile Memory ──────────────────────────────────────────────────────

def test_update_and_read_profile():
    profile = {"style_tags": {}, "interactions": 0}
    item = {"style_tags": ["vintage", "grunge"]}
    update_profile(profile, item, {"description": "vintage grunge band tee"})
    top = preferred_style_tags(profile)
    assert "vintage" in top
    assert profile["interactions"] == 1


def test_memory_biases_second_interaction(monkeypatch, tmp_path):
    # Point the profile store at a temp file so the test is isolated.
    profile_file = str(tmp_path / "profile.json")
    import memory
    monkeypatch.setattr(memory, "_PROFILE_PATH", profile_file)
    # run_agent imported load/save/etc by name; patch those bindings too.
    monkeypatch.setattr(agent, "load_profile", lambda: memory.load_profile(profile_file))
    monkeypatch.setattr(agent, "save_profile", lambda p: memory.save_profile(p, profile_file))

    monkeypatch.setattr(tools, "_get_groq_client", _fake_client_factory("outfit / caption"))

    first = run_agent("vintage grunge band tee under $30", get_example_wardrobe(), use_memory=True)
    assert first["selected_item"] is not None

    saved = load_profile(profile_file)
    assert preferred_style_tags(saved), "first interaction should have stored preferences"

    second = run_agent("a top", get_example_wardrobe(), use_memory=True)
    # The second query carries no style words, yet remembered tags get applied.
    assert second["profile_applied"], "second interaction should reuse stored style prefs"
