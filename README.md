# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

## Setup

**macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows:**
```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_api_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Tool Inventory

Your README submission must document each tool's name, inputs, and return value. **These must exactly match your actual function signatures in `tools.py`.** Your documented interfaces will be checked against your actual function signatures in `tools.py` — if the parameter count or types contradict what's in the code, you may not receive full credit for that tool.

Here are my three tools, and these match my actual function signatures in `tools.py`.

### `search_listings`

- **Purpose:** This is my shopping tool. I use it to look through the 40 mock listings and pull back only the ones that actually match what the user asked for, filtered by their size and budget if they gave me those.
- **Inputs:**
  - `description` (`str`) — the text of what the user wants, like "vintage graphic tee".
  - `size` (`str | None`) — an optional size to filter by, like "M" or "US 8". If it's `None` I just skip size filtering.
  - `max_price` (`float | None`) — an optional price ceiling. If it's `None` I don't filter on price at all.
- **Output:** A `list[dict]`. Each dict is a full listing with `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`. I sort it so the best match is first, and if nothing matches I return an empty list `[]` instead of crashing.

### `suggest_outfit`

- **Purpose:** Once I've picked an item, I use this tool to build one or two real outfits around it using the pieces the user already owns, so the suggestion feels personal and not generic.
- **Inputs:**
  - `new_item` (`dict`) — the listing the user is thinking about buying (the top search result).
  - `wardrobe` (`dict`) — the user's closet in the wardrobe schema format, with an `items` list inside it.
- **Output:** A `str` with the outfit ideas written out. If the wardrobe is empty I still return a useful string with general styling advice instead of an empty string or an error.

### `create_fit_card`

- **Purpose:** This is the last step. I take the outfit and turn it into a short, casual caption the user could actually post — it names the item, price, and platform and captures the vibe.
- **Inputs:**
  - `outfit` (`str`) — the outfit text that `suggest_outfit` gave me.
  - `new_item` (`dict`) — the same listing the outfit was built around.
- **Output:** A `str` caption, usually 2–4 sentences. If the outfit string is empty I return a descriptive error message string instead of raising an exception.

---

## Interaction Walkthrough

<!-- Walk through a complete interaction step by step: natural language query → each tool call (and why) → final fit card.
     Walk through this carefully — it's how graders follow your agent's reasoning without a live demo.
     Use a specific example — do not leave this as a template. -->

**User query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1 — Tool called:**
- Tool: `search_listings`
- Input: `description="vintage graphic tee"`, `size=None`, `max_price=30.0` — I pulled these out of the query first. I caught the "$30" as the budget and left size empty because the user never gave me one.
- Why this tool: The user is shopping first, so before I can style anything I need a real item to work with. I think it makes no sense to suggest an outfit for something that isn't even for sale in their budget.
- Output: A ranked list of 22 matching listings, with `lst_033` "Vintage Band Tee — Faded Grey" ($19.0, depop) first.

**Step 2 — Tool called:**
- Tool: `suggest_outfit`
- Input: `new_item=` the top result (`lst_033`), `wardrobe=get_example_wardrobe()`
- Why this tool: Now that I have a concrete item, I want to style it with what the user actually owns. I take the first result as my selected item and pass it in with their wardrobe so the outfit feels personal.
- Output: A styling string that pairs the band tee with their baggy straight-leg jeans and chunky white sneakers, and explains why the look works together.

**Step 3 — Tool called:**
- Tool: `create_fit_card`
- Input: `outfit=` the string from Step 2, `new_item=lst_033`
- Why this tool: This is my final step. I take the outfit I just built and turn it into a short caption the user could actually post, mentioning the item, the $19 price, and that it's on depop.
- Output: A 2–4 sentence casual OOTD-style caption.

**Final output to user:** The user sees the top matching listing, the outfit suggestion built from their own wardrobe, and the finished fit card caption that ties it all together and points back to the listing.

---

## Planning Loop

Here's how I decide what to do at each step. I start by reading the user's query and parsing out a description, a size, and a max price. Then I always call `search_listings` first, because in my opinion I can't style or caption anything until I have a real item that's actually for sale and in budget. After that search, I check the results: if the list is empty, I stop right there, store a helpful error message, and return early — I don't want to feed nothing into the next tool. If I do have results, I take the first one as my `selected_item` and move on. Next I call `suggest_outfit` with that item and the wardrobe, and store the outfit it gives me. Finally I pass that outfit into `create_fit_card` to get the caption. The loop ends after the fit card is built, or earlier if the search came back empty.

---

## State Management

I keep one session dictionary that's the single source of truth for the whole interaction. It holds the original `query`, the `parsed` filters, the `search_results`, the `selected_item`, the `wardrobe`, the `outfit_suggestion`, the `fit_card`, and an `error` field that stays `None` unless something stops me early. Each tool reads what the earlier steps wrote into this dict instead of recalculating anything: `search_listings` fills `search_results`, the loop copies the first result into `selected_item`, `suggest_outfit` reads `selected_item` plus `wardrobe` and writes `outfit_suggestion`, and `create_fit_card` reads `selected_item` plus `outfit_suggestion` and writes `fit_card`. So the output of one tool literally becomes the input of the next, which is the moment where you can see my state passing actually happening.

---

## Error Handling and Fail Points

<!-- For each tool, describe the specific failure mode and what your agent does in response.
     This maps to the error handling section of the rubric (F5-C1). -->

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| `search_listings` | No listing matches the query | It returns an empty list `[]` instead of crashing, and my agent catches that, stops before styling, and tells the user what failed and what to try. |
| `suggest_outfit` | The wardrobe is empty | It doesn't error — it returns a useful string with general styling advice for the item on its own. |
| `create_fit_card` | The outfit string is empty | It returns a descriptive error message string instead of raising an exception. |

**A concrete example from my own testing (Milestone 5):**

I deliberately broke each tool to make sure my error handling actually works instead of just hoping it did. The clearest one: I ran the impossible query `search_listings('designer ballgown', size='XXS', max_price=5)` straight from the terminal, and it returned `[]` with no exception, exactly like I wanted. Then I ran the *full agent* on the same impossible query, and instead of a bare "no results found" it gave back:

> No listings matched designer ballgown size XXS under $5. Try loosening the filters.

That's the kind of response I was going for — it tells the user what failed *and* what they can do about it. Testing this is also how I caught and fixed a bug: my size parser was greedily grabbing the word "under" into the size, so the message used to read "...size XXS UNDER under $5", and I tightened the regex so it only captures real size forms.

---

## Spec Reflection

<!-- Answer both questions with at least 2–3 sentences each. -->

**One way planning.md helped during implementation:**

Writing out the planning loop and the architecture diagram before I coded anything saved me a lot of confusion. By the time I got to `agent.py`, I already knew the exact order — search first, stop early if empty, then style, then caption — and I knew which session field each tool was supposed to read and write. So instead of figuring out the control flow while coding, I was basically just translating my own diagram into Python, and the early-return-on-empty-results branch was already designed for me.

**One divergence from your spec, and why:**

In my planning.md I described `suggest_outfit` and `create_fit_card` as returning structured objects, but when I actually built them I had both tools return plain strings instead. I changed this because I'm using the LLM to write the outfit ideas and the caption in natural language, and a string is what the next tool and the user actually need — forcing it into a structured object would have added work without making anything more useful. My function signatures and the tool inventory above reflect what I really built (strings), not the original structured-object idea.

---

## AI Usage

I used an AI coding assistant while building this, and here are two specific times I did, including what I gave it and what I changed afterward.

**Instance 1 — generating `search_listings`.** I gave it the Tool 1 block from my planning.md (the description, the inputs with their types, and the empty-results behavior) plus my architecture diagram, and I told it to use `load_listings()` from `utils.data_loader`. It produced a working search that filtered by price and size and scored listings by keyword overlap. What I changed: the first version treated every query word equally, so weak matches ranked too high. I overrode the scoring so an exact title match and matched style tags get extra weight, and I made sure a score of 0 drops the listing entirely — I wanted the best match genuinely first, not just any match.

**Instance 2 — the query parser and a bug I caught in testing.** I gave it my Planning Loop and State Management sections and asked it to write the part of `agent.py` that pulls a description, size, and max price out of the raw user query with regex. It produced the parser, but during my Milestone 5 failure testing I found its size pattern was too greedy — for "designer ballgown size XXS under $5" it captured "XXS UNDER" as the size and garbled my error message. I overrode that regex so it only matches real size forms (XXS, M, US 8, W30 L30, S/M, numeric), re-ran all my tests, and confirmed the message came out clean. So I didn't just take the generated code — I tested it, found where it was wrong, and fixed it myself.

---

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.
