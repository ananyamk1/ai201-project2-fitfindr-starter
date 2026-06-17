# FitFindr — Demo Video Script (~3 min)

> Spoken in first person. **[DO]** = what to show on screen. **[SAY]** = what to say out loud.
> Tight version — keep it moving, don't pause between sections.

---

## 1. Start + the three tools (about 30 sec)

**[DO]** VS Code open with `tools.py` showing. Briefly point at the three function headers.

**[SAY]**
"This is my Project 2, FitFindr — a little agent that finds secondhand clothes, styles them with what you already own, and writes a caption. It's three tools: `search_listings` finds items, `suggest_outfit` styles the one I pick using the user's wardrobe, and `create_fit_card` writes the final caption. Let me run a full interaction."

---

## 2. Run the full interaction (about 60 sec)

**[DO]** Open the terminal and run:
```
source .venv/bin/activate
python agent.py
```

**[SAY]** (while pointing at each block as it appears)
"My query is 'a vintage graphic tee under $30.' It parses that, catches the budget, and calls `search_listings` — top match is this Vintage Band Tee, nineteen dollars on depop. That becomes my selected item. Then `suggest_outfit` takes that item plus my wardrobe and styles it with my baggy jeans and chunky sneakers. And `create_fit_card` turns that into this caption — item, price, platform, done. That's all three tools end to end."

---

## 3. The state-passing moment (about 40 sec)

**[DO]** Open `agent.py`, scroll to `run_agent` (lines ~174–181), highlight:
```python
top_result = search_results[0]
session["selected_item"] = top_result
outfit_suggestion = suggest_outfit(top_result, wardrobe)
session["outfit_suggestion"] = outfit_suggestion
fit_card = create_fit_card(outfit_suggestion, top_result)
```

**[SAY]**
"Here's the state passing. I keep one session dictionary. The first search result is stored as `selected_item` and handed straight into `suggest_outfit`. What that returns is stored as `outfit_suggestion` and handed straight into `create_fit_card`. So each tool's output becomes the next one's input."

---

## 4. Trigger a failure (about 35 sec)

**[DO]** In the terminal, run:
```
python -c "from agent import run_agent; from utils.data_loader import get_example_wardrobe; print(run_agent('designer ballgown size XXS under \$5', get_example_wardrobe())['error'])"
```

**[SAY]** (point at the message)
"Now I'll break it — a designer ballgown, size XXS, under five dollars. Nothing matches, but it doesn't crash. It tells the user what failed and what to do: 'No listings matched designer ballgown size XXS under five dollars. Try loosening the filters.' It stops cleanly before styling instead of erroring out."

---

## 5. Wrap up (about 10 sec)

**[SAY]**
"So that's FitFindr — three tools chained through one session, state passing all the way through, and a graceful failure when there's nothing to find. Thanks for watching."

**[DO]** Stop recording.
