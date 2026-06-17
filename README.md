# FitFindr

FitFindr is a secondhand shopping agent that takes a natural language query, searches a mock listings dataset, and returns a styled outfit suggestion and a social-media-ready caption — all in one planning loop.

---

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root with your Groq API key (free at [console.groq.com](https://console.groq.com)):

```
GROQ_API_KEY=your_key_here
```

**Run the Gradio UI:**
```bash
python app.py
```

**Run the agent directly:**
```bash
python agent.py
```

**Run tests:**
```bash
pytest tests/test_tools.py -v
```

---

## Tool Inventory

### Tool 1 — `search_listings`

**Purpose:** Queries the mock listings dataset and returns up to 3 results sorted by keyword relevance. This is the only tool that does not call the LLM.

**Inputs:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `description` | `str` | Keywords describing the garment (e.g. `"vintage graphic tee"`). Matched against listing title, description, and style tags. |
| `size` | `str \| None` | Size to filter by (e.g. `"M"`). Case-insensitive substring match — `"M"` matches `"S/M"`. Pass `None` to skip size filtering. |
| `max_price` | `float \| None` | Maximum price in USD, inclusive. Listings priced above this value are excluded. Pass `None` to skip price filtering. |

**Output:** `list[dict]` — up to 3 listing dicts sorted from most to least relevant. Each dict contains: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, `platform`. Returns `[]` if nothing matches — does not raise.

---

### Tool 2 — `suggest_outfit`

**Purpose:** Takes the selected listing and the user's wardrobe and asks the LLM (Groq `llama-3.3-70b-versatile`) to suggest 1–2 complete, named outfits with concrete styling instructions.

**Inputs:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `new_item` | `dict` | The full listing dict returned by `search_listings` (the top result). |
| `wardrobe` | `dict` | A dict with an `"items"` key containing a list of wardrobe item dicts. Pass `{"items": []}` for a new user — the tool handles the empty case gracefully. |

**Output:** `str` — a non-empty string naming an aesthetic, specific pieces to pair, and at least one styling instruction (e.g. roll the sleeves, tuck the front corner). Never returns an empty string on a valid LLM response.

---

### Tool 3 — `create_fit_card`

**Purpose:** Takes the outfit suggestion and the listing and asks the LLM to generate a casual, first-person social caption — the kind a real user would post on Instagram or TikTok.

**Inputs:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `outfit` | `str` | The full suggestion string returned by `suggest_outfit`. |
| `new_item` | `dict` | The same listing dict passed to `suggest_outfit`. Used to pull `platform` and `price` into the caption. |

**Output:** `str` — 1–3 sentences in casual first-person voice, including at least one emoji, the platform, the price, and at least one named wardrobe piece from the outfit. Returns an error message string (not an exception) if `outfit` is empty or whitespace-only.

---

## Planning Loop

The planning loop in `run_agent()` (`agent.py`) runs as a linear sequence of guarded steps. Each step only runs if the previous step produced a usable result — the agent does not call all three tools unconditionally.

```
query
  │
  ▼
Step 2: Parse query (regex) → description, size, max_price → session["parsed"]
  │
  ▼
Step 3: search_listings(description, size, max_price) → session["search_results"]
  │
  ├── results == [] → set session["error"], return early (suggest_outfit never called)
  │
  ▼
Step 4: session["selected_item"] = search_results[0]
  │
  ▼
Step 5: suggest_outfit(selected_item, wardrobe) → session["outfit_suggestion"]
  │
  ├── empty/None → set session["error"] with item details, return early (create_fit_card never called)
  │
  ▼
Step 6: create_fit_card(outfit_suggestion, selected_item) → session["fit_card"]
  │
  ├── empty/error string → set session["error"] with outfit as plain text, return early
  │
  ▼
Step 7: return session (error=None, all fields populated)
```

**Query parsing** is done with regex — no LLM call needed at this step. A price pattern (`$30`, `30 dollars`) sets `max_price`; a size pattern (`size M`) sets `size`; the remainder becomes `description`. This keeps parsing fast and deterministic.

---

## State Management

All intermediate results are stored in a single `session` dict initialized by `_new_session()` at the start of each `run_agent()` call. No global state is used — each call gets a fresh session.

| Field | Set at | Used by |
|-------|--------|---------|
| `session["query"]` | step 1 | reference only |
| `session["parsed"]` | step 2 | step 3 (search call) |
| `session["search_results"]` | step 3 | step 3 branch check |
| `session["selected_item"]` | step 4 | steps 5 and 6 |
| `session["outfit_suggestion"]` | step 5 | step 6 |
| `session["fit_card"]` | step 6 | returned to caller |
| `session["error"]` | any early exit | caller checks this first |

The session is returned in full regardless of which path ran — the caller always checks `session["error"]` before reading `fit_card` or `outfit_suggestion`.

---

## Error Handling

### `search_listings` — no results

If no listings match all three criteria, the tool returns `[]`. The planning loop checks for this immediately and sets `session["error"]` with an actionable message before returning. `suggest_outfit` and `create_fit_card` are never called.

**Tested with:** `"designer ballgown size XXS under $5"`

```
session["search_results"] → []
session["selected_item"]  → None
session["outfit_suggestion"] → None
session["fit_card"]       → None
session["error"]          → "No listings matched your search. Try broadening
                             your description, raising your budget, or trying
                             a nearby size."
```

### `suggest_outfit` — empty wardrobe

If `wardrobe["items"]` is empty, the tool switches to a general styling prompt instead of referencing named wardrobe pieces. It still calls the LLM and returns a non-empty suggestion — the planning loop continues normally. The empty wardrobe case never produces an empty return value.

**Tested with:** `suggest_outfit(item, {"items": []})`

```
# Returns a full suggestion based on the item alone, e.g.:
"To create a complete outfit around this piece, I suggest going for a Soft
 Grunge aesthetic ... consider a flowy, high-waisted skirt ..."
```

If `suggest_outfit` returns an empty string (e.g. API failure), the loop sets `session["error"]` with the found item's title, price, and platform, and stops without calling `create_fit_card`.

### `create_fit_card` — empty outfit string

If `outfit` is empty or whitespace-only (guarded before the LLM call), the tool returns an error message string rather than raising. The planning loop detects this and sets `session["error"]` with the outfit suggestion as plain text so the user still gets value.

**Tested with:** `create_fit_card("", item)` and `create_fit_card("   ", item)`

```
# Returns:
"Error: outfit suggestion is empty — fit card could not be generated."
```

---

## Spec Reflection

**What I implemented as specified:**

- All three tools use the exact signatures and return types described in the spec.
- `search_listings` uses `load_listings()` from `utils/data_loader.py` — no re-implementation of file loading.
- `suggest_outfit` handles the empty wardrobe case without crashing, as required.
- `create_fit_card` takes both `outfit` and `new_item` as arguments and guards against an empty outfit string.
- The planning loop branches on `search_listings` results — `suggest_outfit` is not called when results are empty (verified with `unittest.mock`).
- `create_fit_card` uses `temperature=1.2` to ensure caption variation across runs (verified by running 3 times on the same input and confirming outputs differed).

**One deviation from the spec:**

The spec says `size` must match the listing's size field "exactly." I implemented a case-insensitive substring match instead — `"M"` matches `"S/M"`, `"XL"` matches `"XL/XXL"`. An exact match would return no results for most real queries because listing sizes use slash-separated ranges. This is a deliberate interpretation, not an oversight.

**What I would change with more time:**

- Replace regex query parsing with an LLM call to handle freeform phrasing more reliably (e.g. "something boxy around twenty bucks" would currently miss the price).
- Add relevance scoring that weights style tag matches more heavily than body text matches.
- Surface all 3 search results in the UI so the user can pick one rather than always using `results[0]`.

---

## AI Tool Usage

### Instance 1 — Implementing `search_listings`

**What I gave the AI:** The full Tool 1 block from `planning.md` — the parameter names and types, the return format (list of listing dicts), the failure mode ("returns `[]` if nothing matches — does NOT raise"), and the five TODO steps from the stub docstring. I also specified to use `load_listings()` from `utils/data_loader.py` rather than re-implementing file loading.

**What it produced:** A working implementation that loaded listings, filtered by `max_price` and `size`, scored by keyword overlap across `title`, `description`, and `style_tags`, dropped zero-score listings, and returned the top 3. The filtering and scoring logic were correct on the first pass.

**What I changed:** The initial size match used `==` (exact match). I overrode this to a case-insensitive substring check — `size.lower() in listing["size"].lower()` — because the dataset uses slash-separated ranges like `"S/M"` and an exact match on `"M"` would return nothing. This wasn't a mistake by the AI; the spec said "exact match," but testing against real data made clear that interpretation would break every size-filtered query. I made the call to deviate and documented it in the spec reflection.

---

### Instance 2 — Implementing `suggest_outfit`

**What I gave the AI:** The Tool 2 block from `planning.md` (what it does, both input parameters with their full dict shapes, the return format, and the failure mode), plus the explicit requirement that the empty wardrobe case must not crash and must still return a non-empty string. I specified the model (`llama-3.3-70b-versatile`) and that the API key comes from `.env` via the existing `_get_groq_client()` helper.

**What it produced:** An implementation with two prompt branches — one for an empty wardrobe (general styling advice) and one for a populated wardrobe (specific outfit combinations using named pieces). The prompt for the populated case formatted wardrobe items as a bulleted list including name, category, colors, tags, and notes. The LLM call used `temperature=0.7`.

**What I changed:** The original prompt for the non-empty wardrobe case asked the LLM to "suggest outfits that work with this item." I tightened it to explicitly say "call out the exact wardrobe pieces by name" — without that instruction the LLM sometimes described generic clothing types ("a pair of dark jeans") instead of referencing the actual named items from the wardrobe dict ("Baggy straight-leg jeans, dark wash"). The change was verified by checking that the output string contained names that appeared in the wardrobe's `name` fields.
