# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
Searches the mock listings dataset and returns only items that match the user’s query and filters. It uses the listing fields that matter for shopping: title, description, category, style_tags, size, condition, price, colors, brand, and platform.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): the main text query from the user, such as "vintage graphic tee" or "black boots".
- `size` (str): an optional size preference to filter by, such as "M", "W30 L30", or "US 8".
- `max_price` (float): the highest price the user is willing to pay.

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->
A list of matching listing dictionaries, sorted by best fit first. Each result includes the full listing record: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->
If nothing matches, the agent returns a short no-results message, relaxes the search only if the user asked for a narrow filter, and does not move on to outfit suggestion.

---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Builds an outfit around a new listing by comparing it to the user’s wardrobe. It tries to pick compatible pieces by category, color, style tags, and fit notes.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): the listing chosen from search_listings, with the same listing fields as above.
- `wardrobe` (dict): the user’s closet in the wardrobe schema format, with an `items` list of wardrobe pieces.

**What it returns:**
<!-- Describe the return value -->
A structured outfit suggestion that names the new item and the wardrobe pieces that go with it. The result should include the selected pieces, a short styling reason, and a summary of the overall vibe.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->
If the wardrobe is empty, the agent says it can still describe how to wear the new item alone, but it skips wardrobe matching and does not invent closet pieces. If no good outfit can be built, it returns a fallback suggestion using the new item plus the most neutral compatible pieces it can find.

---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Turns the outfit suggestion into a final fit card the user can read quickly. It presents the item, the matched wardrobe pieces, the style summary, and the buying details together.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (str): the outfit summary or structured outfit description returned by suggest_outfit.
- `new_item` (dict): the chosen listing record that the outfit is based on.

**What it returns:**
<!-- Describe the return value -->
A final fit card object or formatted string with the outfit title, item details, styling notes, and the callout that explains why the pieces work together.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
If the outfit data is incomplete, the agent still returns a partial card for the listing and clearly says which wardrobe match is missing instead of stopping with no output.

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

These are the stretch-feature tools I added beyond the required three. (See the Stretch Features section of the README for full write-ups.)

#### Stretch Tool A: compare_price (Price Comparison)

**What it does:** Assesses whether the selected listing is well-priced relative to comparable items in the dataset.

**Input parameters:**
- `new_item` (dict): the selected listing to evaluate.
- `listings` (list[dict] | None): the comparison pool, defaulting to the full dataset.

**What it returns:** A dict with `assessment` ("great deal" / "fair price" / "priced above market" / "no comparison available"), a `reasoning` string, `item_price`, `median_price`, `comparable_count`, and `price_range`. Comparables are other listings in the same category sharing at least one style tag (falling back to category-only when fewer than three match); the item is bucketed against the median of those comparables.

**What happens if it fails or returns nothing:** If the item has no price or there are no comparables, it returns the "no comparison available" assessment instead of raising.

#### Stretch Tool B: get_trend_info (Trend Awareness)

**What it does:** Looks up current trend notes for the selected listing's style tags so the outfit can lean into what's trending.

**Input parameters:**
- `new_item` (dict): the selected listing.
- `trends` (dict | None): the trend data, defaulting to `load_trends()` (data source: `data/trends.json`).

**What it returns:** A dict with `matched_tags`, `status` (strongest of hot > rising > steady), `notes`, and a combined `summary`. The agent passes the `summary` into `suggest_outfit` via its optional `trend_context` argument so the suggestion visibly reflects the trend.

**What happens if it fails or returns nothing:** If no style tag matches, it returns the data source's `default` trend note rather than an empty result.

---

## Planning Loop

**How does your agent decide which tool to call next?**
The agent starts by reading the user query and deciding whether the user is asking to shop, style, or both. If the query includes a search request, it calls `search_listings(description, size, max_price)` first. After that call, if the result list is empty, it stores `error_message = "No listings found"` in session state and stops. If at least one listing is found, it stores `selected_item = results[0]` and checks the wardrobe state next. If the wardrobe has items, it calls `suggest_outfit(new_item=selected_item, wardrobe=current_wardrobe)`; if the wardrobe is empty, it skips outfit matching and uses the fallback message path. Once `suggest_outfit` returns a usable outfit, it stores `outfit_suggestion` in session state and calls `create_fit_card(outfit=outfit_suggestion, new_item=selected_item)`. The loop ends after the fit card is built or any error branch returns an early response.

---

## State Management

**How does information from one tool get passed to the next?**
The agent keeps a small session object with `user_query`, `search_filters`, `search_results`, `selected_item`, `wardrobe`, `outfit_suggestion`, `fit_card`, and `error_message`. `search_listings` writes `search_results`, the loop copies the first result into `selected_item`, `suggest_outfit` reads `selected_item` plus `wardrobe` and writes `outfit_suggestion`, and `create_fit_card` reads `selected_item` plus `outfit_suggestion` and writes `fit_card`. Each later step uses the stored session values instead of re-reading the files or recalculating previous results.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Say, "No listings matched vintage graphic tee under $30." Then offer to loosen the price, remove the size filter, or broaden the category, and stop before outfit generation. |
| suggest_outfit | Wardrobe is empty | Say, "I found a listing, but I do not have any wardrobe items to style it with yet." Then offer a listing-only styling note and suggest adding wardrobe items or using the empty-wardrobe fallback. |
| create_fit_card | Outfit input is missing or incomplete | Say, "I have the listing, but the outfit is incomplete." Then return a partial fit card with the item details that are available and mark the missing wardrobe match as unresolved. |

---

## Architecture

```text
User query
     |
     v
Planning loop
     |
     +--> build search filters from query
     |
     +--> search_listings(description, size, max_price)
     |         |
     |         +--> results = [] --------------> [ERROR] No listings found -> return early
     |         |
     |         +--> results = [item, ...]
     |                    |
     |                    v
     |            Session: selected_item = results[0]
     |                    |
     |                    +--> wardrobe empty ----> [FALLBACK] skip matching and return listing-only note
     |                    |
     |                    +--> wardrobe has items
     |                              |
     |                              v
     |                  suggest_outfit(new_item, wardrobe)
     |                              |
     |                              +--> outfit missing -> [ERROR] partial styling note
     |                              |
     |                              +--> outfit ready
     |                                       |
     |                                       v
     |                           Session: outfit_suggestion = ...
     |                                       |
     |                                       v
     |                   create_fit_card(outfit_suggestion, selected_item)
     |                                       |
     |                                       v
     |                           Session: fit_card = ...
     |                                       |
     v                                       v
Return final answer                    Session state
```

---

## AI Tool Plan

I will use Copilot for the first pass on the tool functions and the planning loop. For `search_listings`, I will give it the Tool 1 block plus the architecture diagram and ask it to use `load_listings()` from `utils.data_loader`; I will check that it filters by description, size, and max price, and I will test it with three queries, including one that should return nothing. For `suggest_outfit`, I will give it the Tool 2 block and the wardrobe schema section, then verify that it reads the wardrobe `items` list, handles an empty wardrobe, and returns a structured outfit suggestion. For `create_fit_card`, I will give it the Tool 3 block and ask it to format the final recommendation; I will verify that it includes the outfit summary, the new item details, and a clear message when data is missing.

**Milestone 3 — Individual tool implementations:**

I will ask Copilot to write each tool one at a time, starting with `search_listings`, then `suggest_outfit`, then `create_fit_card`. After each tool, I will run a small test case and compare the output to the exact return shape and failure behavior I wrote above before moving on.

**Milestone 4 — Planning loop and state management:**

I will use Copilot again for the planning loop and session state wiring. I will give it the Planning Loop, State Management, Error Handling, and Architecture sections, then verify that the code follows the branches in the diagram, stores the right session values, and stops early on empty search results or missing wardrobe data.

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
<!-- What does the agent do first? Which tool is called? With what input? -->
The agent reads the query, extracts `description="vintage graphic tee"`, keeps `size=None`, sets `max_price=30.0`, and calls `search_listings(description="vintage graphic tee", size=None, max_price=30.0)`.

**Step 2:**
<!-- What happens next? What was returned from step 1? What tool is called now? -->
`search_listings` returns a ranked list with `lst_033` first, so the agent stores `selected_item = results[0]` and calls `suggest_outfit(new_item=selected_item, wardrobe=get_example_wardrobe())`.

**Step 3:**
<!-- Continue until the full interaction is complete -->
`suggest_outfit` returns an outfit with the band tee, the user's baggy jeans, and chunky white sneakers, and then the agent calls `create_fit_card(outfit=<suggested_outfit>, new_item=selected_item)`.

**Final output to user:**
<!-- What does the user actually see at the end? -->
The user sees the top matching listing, a short outfit suggestion based on the wardrobe, and a final fit card that explains why the look works and points back to the listing source.
