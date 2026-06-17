import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import tools
from tools import create_fit_card, search_listings, suggest_outfit
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe


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


def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0
    assert all(item["price"] <= 50 for item in results)


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_size_and_price_filters():
    results = search_listings("black combat boots", size="US 7", max_price=60)
    assert len(results) > 0
    assert all(item["price"] <= 60 for item in results)
    assert any(item["id"] == "lst_009" for item in results)


def test_suggest_outfit_with_example_wardrobe(monkeypatch):
    fake_text = "Pair the tee with baggy jeans and chunky sneakers for a relaxed streetwear look."
    monkeypatch.setattr(tools, "_get_groq_client", _fake_client_factory(fake_text))

    item = search_listings("vintage graphic tee", size=None, max_price=30)[0]
    result = suggest_outfit(item, get_example_wardrobe())

    assert isinstance(result, str)
    assert "tee" in result.lower()
    assert "jeans" in result.lower() or "sneakers" in result.lower()


def test_suggest_outfit_empty_wardrobe(monkeypatch):
    fake_text = "Try it with loose jeans, sneakers, and a jacket for a casual vintage vibe."
    monkeypatch.setattr(tools, "_get_groq_client", _fake_client_factory(fake_text))

    item = search_listings("vintage graphic tee", size=None, max_price=30)[0]
    result = suggest_outfit(item, get_empty_wardrobe())

    assert isinstance(result, str)
    assert result.strip() != ""
    assert "jeans" in result.lower() or "jacket" in result.lower() or "vibe" in result.lower()


def test_suggest_outfit_missing_api_key(monkeypatch):
    def _raise_missing_key():
        raise ValueError("GROQ_API_KEY not set. Add it to a .env file in the project root.")

    monkeypatch.setattr(tools, "_get_groq_client", _raise_missing_key)

    item = search_listings("vintage graphic tee", size=None, max_price=30)[0]
    result = suggest_outfit(item, get_example_wardrobe())

    assert "Could not generate an outfit suggestion" in result


def test_create_fit_card_with_text(monkeypatch):
    fake_text = "Vintage band tee on depop with baggy jeans and sneakers for a grunge streetwear fit."
    monkeypatch.setattr(tools, "_get_groq_client", _fake_client_factory(fake_text))

    item = search_listings("vintage graphic tee", size=None, max_price=30)[0]
    result = create_fit_card("Pair it with baggy jeans and sneakers.", item)

    assert isinstance(result, str)
    assert result == fake_text


def test_create_fit_card_empty_outfit():
    item = search_listings("vintage graphic tee", size=None, max_price=30)[0]
    result = create_fit_card("", item)

    assert result.startswith("Error:")


def test_create_fit_card_missing_api_key(monkeypatch):
    def _raise_missing_key():
        raise ValueError("GROQ_API_KEY not set. Add it to a .env file in the project root.")

    monkeypatch.setattr(tools, "_get_groq_client", _raise_missing_key)

    item = search_listings("vintage graphic tee", size=None, max_price=30)[0]
    result = create_fit_card("Pair it with baggy jeans and sneakers.", item)

    assert "Error: the fit card could not be generated" in result