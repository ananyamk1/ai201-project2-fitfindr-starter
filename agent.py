"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


def _parse_query(query: str) -> dict:
    """Extract a rough shopping description, size, and max price from text."""
    text = query.strip()
    lower_text = text.lower()

    max_price = None
    price_match = re.search(r"(?:under|below|less than|up to|max(?:imum)?)\s*\$?\s*(\d+(?:\.\d+)?)", lower_text)
    if price_match:
        max_price = float(price_match.group(1))
    else:
        standalone_price_match = re.search(r"\$\s*(\d+(?:\.\d+)?)", lower_text)
        if standalone_price_match:
            max_price = float(standalone_price_match.group(1))

    size = None
    size_patterns = [
        r"\bsize\s*(w\d+\s*l\d+|us\s*\d+(?:\.\d+)?|xxs|xs|s|m|l|xl|xxl|xxxl|\d{1,3}|[a-z]{1,3}\s*/\s*[a-z]{1,3})\b",
        r"\b(us\s*\d+(?:\.\d+)?)\b",
        r"\b(w\d+\s*l\d+)\b",
        r"\b(xxs|xs|s|m|l|xl|xxl|xxxl)\b",
    ]
    for pattern in size_patterns:
        size_match = re.search(pattern, lower_text)
        if size_match:
            candidate = size_match.group(1).strip()
            if candidate.startswith("size"):
                candidate = candidate.replace("size", "", 1).strip()
            candidate = candidate.rstrip(".,!?")
            if candidate:
                size = candidate.upper() if candidate.lower() in {"s", "m", "l", "xl", "xxl", "xxxl", "xs", "xxs"} else candidate.upper()
                break

    if size is None:
        size_match = re.search(r"\b(us\s*\d+(?:\.\d+)?|w\d+\s*l\d+|xxs|xs|s|m|l|xl|xxl|xxxl)\b", lower_text)
        if size_match:
            size = size_match.group(1).strip().upper()

    description = text
    if max_price is not None:
        description = re.sub(r"(?:under|below|less than|up to|max(?:imum)?)\s*\$?\s*\d+(?:\.\d+)?", "", description, flags=re.IGNORECASE)
        description = re.sub(r"\$\s*\d+(?:\.\d+)?", "", description, flags=re.IGNORECASE)
    if size:
        description = re.sub(rf"\bsize\s*{re.escape(size)}\b", "", description, flags=re.IGNORECASE)
        description = re.sub(rf"\b{re.escape(size)}\b", "", description, flags=re.IGNORECASE)

    description = re.sub(r"\s+", " ", description).strip(" ,.-")
    if not description:
        description = text

    return {
        "description": description,
        "size": size,
        "max_price": max_price,
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.

    TODO — implement this function using the planning loop you designed in planning.md:

        Step 1: Initialize the session with _new_session().

        Step 2: Parse the user's query to extract a description, size, and
                max_price. You can use regex, string splitting, or ask the LLM
                to parse it — document your choice in planning.md.
                Store the result in session["parsed"].

        Step 3: Call search_listings() with the parsed parameters.
                Store results in session["search_results"].
                If no results: set session["error"] to a helpful message and
                return the session early. Do NOT proceed to suggest_outfit
                with empty input.

        Step 4: Select the item to use (e.g., the top result).
                Store it in session["selected_item"].

        Step 5: Call suggest_outfit() with the selected item and wardrobe.
                Store the result in session["outfit_suggestion"].

        Step 6: Call create_fit_card() with the outfit suggestion and selected item.
                Store the result in session["fit_card"].

        Step 7: Return the session.

    Before writing code, complete the Planning Loop and State Management sections
    of planning.md — your implementation should match what you described there.
    """
    session = _new_session(query, wardrobe)

    parsed = _parse_query(query)
    session["parsed"] = parsed

    search_results = search_listings(
        description=parsed["description"],
        size=parsed["size"],
        max_price=parsed["max_price"],
    )
    session["search_results"] = search_results

    if not search_results:
        session["error"] = (
            f'No listings matched {parsed["description"]}'
            + (f' size {parsed["size"]}' if parsed["size"] else "")
            + (f' under ${parsed["max_price"]:.0f}' if parsed["max_price"] is not None else "")
            + ". Try loosening the filters."
        )
        return session

    top_result = search_results[0]
    session["selected_item"] = top_result

    outfit_suggestion = suggest_outfit(top_result, wardrobe)
    session["outfit_suggestion"] = outfit_suggestion

    fit_card = create_fit_card(outfit_suggestion, top_result)
    session["fit_card"] = fit_card

    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== Happy path: graphic tee ===\n")
    result = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if result["error"]:
        print(f"Error: {result['error']}")
    else:
        found_item = result["selected_item"]
        if isinstance(found_item, dict):
            title = found_item.get("title", "<untitled listing>")
            print(f"Found: {title}")
        else:
            print("Found: <no listing returned>")
        print(f"\nOutfit: {result['outfit_suggestion']}")
        print(f"\nFit card: {result['fit_card']}")

    print("\n\n=== No-results path ===\n")
    result2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {result2['error']}")
