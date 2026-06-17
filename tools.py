"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re
from typing import Any

from dotenv import load_dotenv
from groq import (
    APIConnectionError,
    APIResponseValidationError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    Groq,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    UnprocessableEntityError,
)

from utils.data_loader import load_listings, load_trends

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


def _normalize_text(value: Any) -> str:
    """Lowercase text and collapse punctuation into spaces for matching."""
    if value is None:
        return ""
    text = str(value).lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _tokenize_query(description: str) -> list[str]:
    """Extract simple search tokens from the user query."""
    normalized = _normalize_text(description)
    if not normalized:
        return []

    stop_words = set([
        "a", "an", "and", "the", "for", "with", "to", "of", "in", "on",
        "under", "less", "than", "budget", "cheap", "looking", "need",
        "want", "wants", "i", "me", "my", "out", "there", "what", "is",
        "are", "style", "styled", "how", "would", "like", "some", "any",
        "please", "find", "show",
    ])
    tokens = [token for token in normalized.split() if token not in stop_words]

    phrase_boosts = [
        "graphic tee",
        "band tee",
        "baby tee",
        "track jacket",
        "cargo pants",
        "wide leg",
        "straight leg",
        "denim jacket",
        "combat boots",
        "chunky sneakers",
        "biker shorts",
        "crewneck sweatshirt",
        "flannel shirt",
    ]
    for phrase in phrase_boosts:
        if phrase in normalized:
            tokens.extend(phrase.split())

    return list(dict.fromkeys(tokens))


def _matches_size(listing_size: str, requested_size: str) -> bool:
    """Return True when the requested size looks compatible with the listing."""
    listing = _normalize_text(listing_size)
    requested = _normalize_text(requested_size)
    if not requested or not listing:
        return False
    if requested in listing:
        return True

    requested_tokens = requested.split()
    listing_tokens = listing.split()
    if not requested_tokens:
        return False

    # Let broad size tokens like M match S/M, M/L, or M fits oversized.
    broad_sizes = {"xxs", "xs", "s", "m", "l", "xl", "xxl", "xxxl"}
    if requested in broad_sizes:
        return requested in listing_tokens or requested in listing.replace(" ", "")

    # Numeric sizes can match exact size mentions in strings like W30 L30 or US 8.
    for token in requested_tokens:
        if token and token in listing_tokens:
            return True
    return False


def _listing_score(listing: dict, query_tokens: list[str], raw_query: str) -> int:
    """Score a listing by overlap with the search query."""
    if not query_tokens:
        return 1

    haystack_parts = [
        listing.get("title", ""),
        listing.get("description", ""),
        listing.get("category", ""),
        " ".join(listing.get("style_tags", []) or []),
        " ".join(listing.get("colors", []) or []),
        listing.get("brand", "") or "",
        listing.get("platform", ""),
        listing.get("size", ""),
        listing.get("condition", ""),
    ]
    haystack = _normalize_text(" ".join(haystack_parts))
    score = 0

    raw_query_normalized = _normalize_text(raw_query)
    title = _normalize_text(listing.get("title", ""))
    description = _normalize_text(listing.get("description", ""))

    if raw_query_normalized and raw_query_normalized in title:
        score += 8
    if raw_query_normalized and raw_query_normalized in description:
        score += 4

    for token in query_tokens:
        if token in haystack:
            score += 2

    # Give style/category/brand matches a little extra weight.
    category = _normalize_text(listing.get("category", ""))
    styles = _normalize_text(" ".join(listing.get("style_tags", []) or []))
    colors = _normalize_text(" ".join(listing.get("colors", []) or []))
    if any(token in category for token in query_tokens):
        score += 2
    if any(token in styles for token in query_tokens):
        score += 2
    if any(token in colors for token in query_tokens):
        score += 1

    return score


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()
    query_tokens = _tokenize_query(description)

    filtered: list[tuple[int, dict]] = []
    for listing in listings:
        listing_price = listing.get("price")
        if max_price is not None and listing_price is not None and listing_price > max_price:
            continue
        if size and not _matches_size(listing.get("size", ""), size):
            continue

        score = _listing_score(listing, query_tokens, description)
        if score <= 0:
            continue
        filtered.append((score, listing))

    filtered.sort(key=lambda item: (-item[0], item[1].get("price", float("inf")), item[1].get("title", "")))
    return [listing for _, listing in filtered]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict, trend_context: str | None = None) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.
        trend_context: Optional trend note (from the get_trend_info stretch tool).
                  When provided it is added to the prompt so the suggestion can
                  lean into what is currently trending. Defaults to None, which
                  keeps the original (new_item, wardrobe) behavior unchanged.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    wardrobe_items = (wardrobe or {}).get("items", []) or []

    item_summary = (
        f"Item: {new_item.get('title', 'Unknown item')}\n"
        f"Category: {new_item.get('category', 'unknown')}\n"
        f"Colors: {', '.join(new_item.get('colors', []) or []) or 'none listed'}\n"
        f"Style tags: {', '.join(new_item.get('style_tags', []) or []) or 'none listed'}\n"
        f"Size: {new_item.get('size', 'unknown')}\n"
        f"Condition: {new_item.get('condition', 'unknown')}\n"
    )

    if not wardrobe_items:
        user_prompt = (
            "You are FitFindr. Give short, practical styling advice for a thrift item when the user has no wardrobe items saved. "
            "Return 1-2 outfit ideas that do not depend on specific closet pieces. Keep it casual and useful.\n\n"
            f"{item_summary}"
        )
    else:
        wardrobe_lines = []
        for item in wardrobe_items:
            wardrobe_lines.append(
                f"- {item.get('name', 'Unnamed item')} | category: {item.get('category', 'unknown')} | colors: {', '.join(item.get('colors', []) or []) or 'none listed'} | style_tags: {', '.join(item.get('style_tags', []) or []) or 'none listed'} | notes: {item.get('notes') or 'none'}"
            )

        user_prompt = (
            "You are FitFindr. Suggest 1-2 complete outfits using the thrift item and the user's wardrobe. "
            "Name specific wardrobe pieces, explain why they work together, and keep the answer concise but specific.\n\n"
            f"{item_summary}\n"
            "Wardrobe items:\n"
            + "\n".join(wardrobe_lines)
        )

    if trend_context and trend_context.strip():
        user_prompt += (
            "\n\nCurrent trend context (lean into this where it fits naturally):\n"
            f"{trend_context.strip()}"
        )

    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0.8,
            messages=[
                {
                    "role": "system",
                    "content": "You are a fashion assistant that writes concise outfit suggestions with practical styling advice.",
                },
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content or ""
        return content.strip() or "No outfit suggestion could be generated."
    except ValueError as exc:
        return f"Could not generate an outfit suggestion: {exc}"
    except (
        APIConnectionError,
        APITimeoutError,
        AuthenticationError,
        BadRequestError,
        ConflictError,
        InternalServerError,
        NotFoundError,
        PermissionDeniedError,
        RateLimitError,
        UnprocessableEntityError,
        APIResponseValidationError,
        APIStatusError,
    ) as exc:  # pragma: no cover - defensive fallback for API failures
        return (
            "Could not generate an outfit suggestion right now. "
            f"Reason: {exc}"
        )


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    if not outfit or not outfit.strip():
        return "Error: outfit is empty, so FitFindr cannot build a fit card yet."

    item_summary = (
        f"Title: {new_item.get('title', 'Unknown item')}\n"
        f"Price: ${new_item.get('price', 'unknown')}\n"
        f"Platform: {new_item.get('platform', 'unknown')}\n"
        f"Condition: {new_item.get('condition', 'unknown')}\n"
        f"Category: {new_item.get('category', 'unknown')}\n"
        f"Colors: {', '.join(new_item.get('colors', []) or []) or 'none listed'}\n"
        f"Style tags: {', '.join(new_item.get('style_tags', []) or []) or 'none listed'}\n"
    )

    prompt = (
        "Write a 2-4 sentence casual fit card caption for FitFindr. "
        "Make it sound like a real OOTD post, not a product listing. "
        "Mention the item name, price, and platform naturally once each. "
        "Use the outfit details to explain the vibe, but do not copy this prompt.\n\n"
        f"Item details:\n{item_summary}\n"
        f"Outfit details:\n{outfit}\n"
    )

    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=1.0,
            messages=[
                {
                    "role": "system",
                    "content": "You write short, stylish, natural-sounding outfit captions.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content or ""
        return content.strip() or "Error: the fit card could not be generated."
    except ValueError as exc:
        return f"Error: the fit card could not be generated. Reason: {exc}"
    except (
        APIConnectionError,
        APITimeoutError,
        AuthenticationError,
        BadRequestError,
        ConflictError,
        InternalServerError,
        NotFoundError,
        PermissionDeniedError,
        RateLimitError,
        UnprocessableEntityError,
        APIResponseValidationError,
        APIStatusError,
    ) as exc:  # pragma: no cover - defensive fallback for API failures
        return f"Error: the fit card could not be generated right now. Reason: {exc}"


# ── Stretch Tool: compare_price (Price Comparison) ──────────────────────────────

def _median(values: list[float]) -> float:
    """Return the median of a non-empty list of numbers."""
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def compare_price(new_item: dict, listings: list[dict] | None = None) -> dict:
    """
    Assess whether a listing is well-priced compared to similar items in the
    dataset. (Stretch feature: Price Comparison Tool.)

    Comparables are other listings in the SAME category that share at least one
    style tag with the item. If fewer than three such matches exist, the
    comparison falls back to all other listings in the same category so the
    assessment still has a meaningful basis.

    Args:
        new_item: The listing dict to evaluate (typically the selected item).
        listings: The pool to compare against. Defaults to the full dataset
                  loaded with load_listings().

    Returns:
        A dict describing the assessment:
            {
              "assessment": "great deal" | "fair price" | "priced above market"
                            | "no comparison available",
              "reasoning":  str — a human-readable explanation,
              "item_price": float | None,
              "median_price": float | None,
              "comparable_count": int,
              "price_range": [min, max] | None,
            }
        Never raises — returns the "no comparison available" assessment if the
        item has no price or no comparable listings exist.
    """
    pool = listings if listings is not None else load_listings()
    item_price = new_item.get("price")
    item_id = new_item.get("id")
    item_category = (new_item.get("category") or "").lower()
    item_tags = {t.lower() for t in (new_item.get("style_tags") or [])}

    no_comparison = {
        "assessment": "no comparison available",
        "reasoning": "There aren't enough similar listings to compare this item against.",
        "item_price": item_price,
        "median_price": None,
        "comparable_count": 0,
        "price_range": None,
    }

    if item_price is None:
        return no_comparison

    same_category = [
        l for l in pool
        if l.get("id") != item_id and (l.get("category") or "").lower() == item_category
        and l.get("price") is not None
    ]
    comparables = [
        l for l in same_category
        if item_tags & {t.lower() for t in (l.get("style_tags") or [])}
    ]
    # Fall back to category-only comparison when style overlap is too thin.
    if len(comparables) < 3:
        comparables = same_category

    if not comparables:
        return no_comparison

    prices = [l["price"] for l in comparables]
    median_price = _median(prices)
    low, high = min(prices), max(prices)

    if item_price <= median_price * 0.85:
        assessment = "great deal"
        verdict = "well below"
    elif item_price <= median_price * 1.10:
        assessment = "fair price"
        verdict = "right around"
    else:
        assessment = "priced above market"
        verdict = "above"

    reasoning = (
        f"At ${item_price:.0f}, this is {verdict} the ${median_price:.0f} median "
        f"of {len(comparables)} comparable {item_category or 'listing'}(s) "
        f"(which range ${low:.0f}–${high:.0f}). Verdict: {assessment}."
    )

    return {
        "assessment": assessment,
        "reasoning": reasoning,
        "item_price": item_price,
        "median_price": median_price,
        "comparable_count": len(comparables),
        "price_range": [low, high],
    }


# ── Stretch Tool: get_trend_info (Trend Awareness) ──────────────────────────────

def get_trend_info(new_item: dict, trends: dict | None = None) -> dict:
    """
    Look up current trend notes for a listing's style tags. (Stretch feature:
    Trend Awareness Tool.)

    Data source: data/trends.json — a curated map of style_tag -> {status, note}
    whose tags mirror the style_tags used in the listings dataset, so any listing
    can be matched to a trend note.

    Args:
        new_item: The listing dict whose style tags should be looked up.
        trends:   The trend data to use. Defaults to load_trends().

    Returns:
        A dict:
            {
              "matched_tags": list[str],   — item tags that had a trend note
              "status": str,               — strongest status found (hot > rising > steady)
              "notes": list[str],          — the matched trend notes
              "summary": str,              — a single combined trend line for prompting
            }
        Falls back to the data source's "default" note when no tag matches.
    """
    data = trends if trends is not None else load_trends()
    trend_map = data.get("trends", {})
    default = data.get("default", {"status": "steady", "note": ""})

    item_tags = [t.lower() for t in (new_item.get("style_tags") or [])]
    matched_tags, notes, statuses = [], [], []
    for tag in item_tags:
        entry = trend_map.get(tag)
        if entry:
            matched_tags.append(tag)
            notes.append(entry.get("note", ""))
            statuses.append(entry.get("status", "steady"))

    if not matched_tags:
        return {
            "matched_tags": [],
            "status": default.get("status", "steady"),
            "notes": [default.get("note", "")],
            "summary": default.get("note", ""),
        }

    rank = {"hot": 3, "rising": 2, "steady": 1}
    top_status = max(statuses, key=lambda s: rank.get(s, 0))
    summary = " ".join(n for n in notes if n)

    return {
        "matched_tags": matched_tags,
        "status": top_status,
        "notes": notes,
        "summary": summary,
    }
