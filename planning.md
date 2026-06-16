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
Queries the listings database using the provided description, size, and price ceiling and returns up to 3 matching listings sorted by relevance.

**Input parameters:**
- `description` (str):  The garment description parsed from the user's message (e.g., "vintage graphic tee"). Matched against listing titles and tags.
- `size` (str): The required size parsed from the user's message (e.g., "M"). Must match the listing's size field exactly.
- `max_price` (float): The maximum acceptable price in USD parsed from the user's message (e.g., 30.0). Listings priced strictly above this value are excluded.

**What it returns:**
A list of up to 3 listing objects sorted from most to least relevant (index 0 = best match). Each listing object contains:

- title (str): The listing name (e.g., "Faded Band Tee")
- price (float): Listed price in USD (e.g., 22.0)
- platform (str): The resale platform the listing lives on (e.g., "Depop")
- condition (str): Seller-reported condition (e.g., "Good condition")

If no listings match all three criteria, the tool returns an empty list [].

**What happens if it fails or returns nothing:**
FitFindr tells the user what to do differently for the prompt and stops. It does not call suggest_outfit with an empty input.
---

### Tool 2: suggest_outfit

**What it does:**
Takes the selected listing and the user's existing wardrobe items and generates a specific, styled outfit pairing. Including which pieces to combine, a named aesthetic, and at least one concrete styling instruction.

**Input parameters:**
- new_item (dict): The selected_item object set in Step 1 — the full listing object returned by search_listings, containing title, price, platform, and condition.
- wardrobe (dict): The user's wardrobe, passed as {"items": [...]} where each item is an object with id (str), name (str), category (str), colors (list of str), style_tags (list of str), and notes (str or null). If the user described no wardrobe items, pass {"items": []} — do not omit this parameter or pass null. If items is empty, suggest_outfit should still run and generate a suggestion based on the new item alone, without referencing any owned pieces. 

**What it returns:**
A single non-empty string containing: the specific wardrobe pieces to pair with the new item, a named aesthetic or vibe (e.g., "90s grunge"), and at least one concrete styling instruction (e.g., "roll the sleeves once and tuck the front corner slightly for shape").

**What happens if it fails or returns nothing:**
If the return value is empty, null, or the tool throws an error, do not call create_fit_card. Instead, show the user the found item (selected_item.title, selected_item.price, selected_item.platform) and tell them a styling suggestion is unavailable right now. Stop there — the session ends without a fit card.

---

### Tool 3: create_fit_card

**What it does:**
Takes the outfit suggestion and the selected listing and generates a short, social-media-ready caption written in a casual first-person voice, as if the user is posting it themselves.

**Input parameters:**
- outfit (str): The outfit_suggestion string set in Step 2 — the full suggestion returned by suggest_outfit, including the wardrobe pieces, named aesthetic, and styling instructions.
- new_item (dict): The selected_item object set in Step 1 — the full listing object returned by search_listings, containing title, price, platform, and condition.

**What it returns:**
A single string of 1–3 sentences written as a social post caption. It must include:
- Where the item was thrifted and for how much (drawn from new_item.platform and new_item.price)
- At least one wardrobe piece from the outfit pairing (drawn from outfit)
- A casual, first-person tone with at least one emoji
Example: "thrifted this faded band tee off depop for $22 and honestly it was made for my wide-legs 🖤 full look in my stories"

**What happens if it fails or returns nothing:**
If the return value is empty, null, or the tool throws an error, do not attempt to call it again. Instead, display the outfit_suggestion string as plain text and tell the user the fit card could not be generated. The session ends here regardless.

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | |
| suggest_outfit | Wardrobe is empty | |
| create_fit_card | Outfit input is missing or incomplete | |

---

## Architecture

User query
    │
    ▼
Planning Loop
    │
    ├─► search_listings(query, size, max_price)
    │       │ results=[]  or  ERROR
    │       ├──► "No results found. Try broader description, higher budget, or nearby size." → STOP
    │       │
    │       │ results=[item, ...]
    │       ▼
    │   Session: selected_item = results[0]
    │       │
    ├─► suggest_outfit(selected_item, wardrobe)
    │       │ null/empty  or  ERROR
    │       ├──► Show selected_item.title, .price, .platform — styling unavailable → STOP
    │       │
    │       │ outfit string
    │       ▼
    │   Session: outfit_suggestion = "..."
    │       │
    └─► create_fit_card(outfit_suggestion, selected_item)
            │ null/empty  or  ERROR
            ├──► Display outfit_suggestion as plain text — fit card unavailable → STOP
            │
            │ caption string
            ▼
        Session: fit_card = "..."
            │
            ▼
        Display fit card → STOP

---

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**
- For search_listings, I'll give Claude the Tool 1 block from planning.md and ask it to implement the function using load_listings() from the data loader. I'll verify it filters by all three parameters, returns listing objects with the correct fields, and returns [] when nothing matches — then test it with a query that returns results, one that returns nothing, and one with an invalid size.
- For suggest_outfit, I'll give Claude the Tool 2 block from planning.md (including the full wardrobe dict structure) and ask it to implement the function. I'll verify it accepts the correct input types, still runs when items is empty, and returns a string containing a named aesthetic and at least one styling instruction — then test it with a full wardrobe, an empty wardrobe, and a single-item wardrobe.
- For create_fit_card, I'll give Claude the Tool 3 block from planning.md and ask it to implement the function. I'll verify the returned string references new_item.platform, new_item.price, at least one piece from the outfit string, and contains an emoji — then test it with a normal outfit string and a minimal one.

**Milestone 4 — Planning loop and state management:**
- I'll give Claude the agent diagram and all three failure mode sections from planning.md and ask it to implement the planning loop and session state. I'll verify that each tool only runs if the previous step's session value is set, and that each error branch stops without calling the next tool — then test the full loop with a clean run, and with each of the three tools returning empty/null.
---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
The planning loop parses the query and calls search_listings(query="vintage graphic tee", size=None, max_price=30.0). The tool queries the listings database and returns 3 matching listing objects sorted by relevance. FitFindr sets selected_item = results[0]: {title: "Faded Band Tee", price: 22.0, platform: "Depop", condition: "Good condition"}. If the tool returns [], the agent says "No listings matched vintage graphic tee under $30. Try broadening your description, raising your budget, or trying a nearby size." and stops. If the tool throws an error, the agent says "Search is temporarily unavailable — please try again in a moment." and stops.

**Step 2:**
The planning loop calls suggest_outfit(new_item=selected_item, wardrobe={"items": [{baggy jeans}, {chunky sneakers}]}). The tool matches the listing's style tags against the wardrobe items and returns: "Pair this with your baggy jeans and chunky sneakers for a classic 90s grunge look. Tuck the front corner slightly and roll the sleeves once for shape." The planning loop sets outfit_suggestion to this string. If the tool returns null or empty, the agent says "Found your item but couldn't generate a styling suggestion right now. Here's what we found: Faded Band Tee — $22.00 on Depop, Good condition." and stops.

**Step 3:**
The planning loop calls create_fit_card(outfit=outfit_suggestion, new_item=selected_item). The tool uses selected_item.platform, selected_item.price, and the wardrobe pieces named in outfit_suggestion to generate the caption. If the tool returns null, empty, or throws an error, the agent displays outfit_suggestion as plain text and says "Here's your outfit: [outfit_suggestion]. Couldn't generate a fit card this time." and stops.

**Final output to user:**
"thrifted this faded band tee off depop for $22 and it was made for my baggy jeans 🖤 full look in my stories"
