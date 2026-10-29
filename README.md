# Munder Difflin Multi-Agent System Project

Welcome to the starter code repository for the **Munder Difflin Paper Company Multi-Agent System Project**! This repository contains the starter code and tools you will need to design, build, and test a multi-agent system that supports core business operations at a fictional paper manufacturing company.

## Project Context

You’ve been hired as an AI consultant by Munder Difflin Paper Company, a fictional enterprise looking to modernize their workflows. They need a smart, modular **multi-agent system** to automate:

- **Inventory checks** and restocking decisions
- **Quote generation** for incoming sales inquiries
- **Order fulfillment** including supplier logistics and transactions

Your solution must use a maximum of **5 agents** and process inputs and outputs entirely via **text-based communication**.

This project challenges your ability to orchestrate agents using modern Python frameworks like `smolagents`, `pydantic-ai`, or `npcsh`, and combine that with real data tools like `sqlite3`, `pandas`, and LLM prompt engineering.

---

## What’s Included

From the `project.zip` starter archive, you will find:

- `project_starter.py`: The main Python script you will modify to implement your agent system
- `quotes.csv`: Historical quote data used for reference by quoting agents
- `quote_requests.csv`: Incoming customer requests used to build quoting logic
- `quote_requests_sample.csv`: A set of simulated test cases to evaluate your system

---

## Workspace Instructions

All the files have been provided in the VS Code workspace on the Udacity platform. Please install the agent orchestration framework of your choice.

## Local setup instructions

1. Install dependencies

Make sure you have Python 3.8+ installed.

You can install all required packages using the provided requirements.txt file:

`pip install -r requirements.txt`

If you're using smolagents, install it separately:

`pip install smolagents`

For other options like pydantic-ai or npcsh[lite], refer to their documentation.

2. Create .env File

Add your OpenAI-compatible API key:

`UDACITY_OPENAI_API_KEY=your_openai_key_here`

This project uses a custom OpenAI-compatible proxy hosted at https://openai.vocareum.com/v1.

## How to Run the Project

Start by defining your agents in the `"YOUR MULTI AGENT STARTS HERE"` section inside `template.py`. Once your agent team is ready:

1. Run the `run_test_scenarios()` function at the bottom of the script.
2. This will simulate a series of customer requests.
3. Your system should respond by coordinating inventory checks, generating quotes, and processing orders.

Output will include:

- Agent responses
- Cash and inventory updates
- Final financial report
- A `test_results.csv` file with all interaction logs

---

## Tips for Success

- Start by sketching a **flow diagram** to visualize agent responsibilities and interactions.
- Test individual agent tools before full orchestration.
- Always include **dates** in customer requests when passing data between agents.
- Ensure every quote includes **bulk discounts** and uses past data when available.
- Use the **exact item names** from the database to avoid transaction failures.

---

## Submission Checklist

Make sure to submit the following files:

1. Your completed `template.py` or `project_starter.py` with all agent logic
2. A **workflow diagram** describing your agent architecture and data flow
3. A `README.txt` or `design_notes.txt` explaining how your system works
4. Outputs from your test run (like `test_results.csv`)

---

## Customer-Facing Output Examples

The system separates internal telemetry (`internal_audit`) from the customer-facing reply (`customer_reply`).
Only `customer_reply` is saved to `test_results.csv`; `internal_audit` is written to `internal_audit_log.jsonl`
(gitignored, developer-only).

### Example 1 — Fulfilled order with bulk discount (Request 1)

**Customer input:** "I would like to request the following paper supplies for the ceremony:
- 200 sheets of A4 glossy paper
- 100 sheets of heavy cardstock (white)
- 100 sheets of colored paper (assorted colors)
I need these supplies delivered by April 15, 2025." (2025-04-01)

**`customer_reply`:**

```json
{
  "request_date": "2025-04-01",
  "stage": "complete",
  "items_requested": [
    {"item_name": "A4 glossy paper", "quantity": 200},
    {"item_name": "heavy cardstock (white)", "quantity": 100},
    {"item_name": "colored paper (assorted colors)", "quantity": 100}
  ],
  "available_items": [
    {"item_name": "Glossy paper", "quantity": 200},
    {"item_name": "Cardstock", "quantity": 100},
    {"item_name": "Colored paper", "quantity": 100}
  ],
  "unavailable_items": [],
  "quote": {
    "lines": [
      {"item_name": "Glossy paper", "quantity": 200, "unit_price": 0.2, "line_total": 40.0},
      {"item_name": "Cardstock", "quantity": 100, "unit_price": 0.15, "line_total": 15.0},
      {"item_name": "Colored paper", "quantity": 100, "unit_price": 0.1, "line_total": 10.0}
    ],
    "unknown_items": [],
    "total_units": 400,
    "subtotal": 65.0,
    "discount_percent": 5,
    "discount_amount": 3.25,
    "total_price": 61.75,
    "quote_explanation": ""
  },
  "sales": {
    "status": "confirmed",
    "items": [
      {"item_name": "Glossy paper", "quantity": 200, "line_total": 40.0},
      {"item_name": "Cardstock", "quantity": 100, "line_total": 15.0},
      {"item_name": "Colored paper", "quantity": 100, "line_total": 10.0}
    ],
    "refused": [],
    "blocked": [],
    "delivery_date": null,
    "notes": ""
  },
  "notes": ""
}
```

**Key transparency elements:** Item-by-item pricing, 5% bulk discount tier explicitly stated ($3.25 saved),
subtotal → discount → final total math, zero unavailable items.

---

### Example 2 — Partial fulfillment with blocked stock line (Request 14)

**Customer input:** "I would like to place a large order for the following paper supplies for an upcoming
performance:
- 5,000 sheets of A4 paper
- 2,000 sheets of poster paper in various colors
- 500 sheets of cardstock
I need these supplies delivered by April 15, 2025." (2025-04-09)

**`customer_reply`:**

```json
{
  "request_date": "2025-04-09",
  "stage": "complete",
  "items_requested": [
    {"item_name": "A4 paper", "quantity": 5000},
    {"item_name": "poster paper in various colors", "quantity": 2000},
    {"item_name": "cardstock", "quantity": 500}
  ],
  "available_items": [
    {"item_name": "A4 paper", "quantity": 5000},
    {"item_name": "Poster paper", "quantity": 2000},
    {"item_name": "Cardstock", "quantity": 500}
  ],
  "unavailable_items": [],
  "quote": {
    "lines": [
      {"item_name": "A4 paper", "quantity": 5000, "unit_price": 0.05, "line_total": 250.0},
      {"item_name": "Poster paper", "quantity": 2000, "unit_price": 0.25, "line_total": 500.0},
      {"item_name": "Cardstock", "quantity": 500, "unit_price": 0.15, "line_total": 75.0}
    ],
    "unknown_items": [],
    "total_units": 7500,
    "subtotal": 825.0,
    "discount_percent": 12,
    "discount_amount": 99.0,
    "total_price": 726.0,
    "quote_explanation": ""
  },
  "sales": {
    "status": "partially_fulfilled",
    "items": [
      {"item_name": "A4 paper", "quantity": 5000, "line_total": 250.0}
    ],
    "refused": [],
    "blocked": [
      {"item_name": "Poster paper", "quantity": 2000, "reason": "Out of stock; expected delivery on 2025-04-16"},
      {"item_name": "Cardstock", "quantity": 500, "reason": "Out of stock; expected delivery on 2025-04-13"}
    ],
    "delivery_date": "2025-04-13",
    "notes": ""
  },
  "notes": "The following items could not be sold due to stock constraints: Poster paper (qty 2000): Out of stock; expected delivery on 2025-04-16; Cardstock (qty 500): Out of stock; expected delivery on 2025-04-13. "
}
```

**Key transparency elements:** Item-by-item pricing, 12% bulk discount tier ($99.00 saved), blocked lines
explicitly named with expected delivery dates, no internal stock counts or cash balances exposed.

---

### Example 3 — Unavailable items politely refused (Request 20)

**Customer input:** "I would like to place a large order for the following paper supplies for our upcoming
concert: 5,000 flyers, 2,000 posters, and 10,000 tickets. We need these items delivered by May 15, 2025."
(2025-04-17)

**`customer_reply`:**

```json
{
  "request_date": "2025-04-17",
  "stage": "complete",
  "items_requested": [
    {"item_name": "flyers", "quantity": 5000},
    {"item_name": "posters", "quantity": 2000},
    {"item_name": "tickets", "quantity": 10000}
  ],
  "available_items": [
    {"item_name": "Flyers", "quantity": 5000}
  ],
  "unavailable_items": [
    {"item_name": "posters", "quantity": 2000, "reason": "No matching catalog item.", "suggestions": ["Poster paper", "Photo paper"]},
    {"item_name": "tickets", "quantity": 10000, "reason": "No matching catalog item.", "suggestions": ["Sticky notes"]}
  ],
  "quote": {
    "lines": [
      {"item_name": "Flyers", "quantity": 5000, "unit_price": 0.15, "line_total": 750.0}
    ],
    "unknown_items": [],
    "total_units": 5000,
    "subtotal": 750.0,
    "discount_percent": 12,
    "discount_amount": 90.0,
    "total_price": 660.0,
    "quote_explanation": ""
  },
  "sales": {
    "status": "confirmed",
    "items": [
      {"item_name": "Flyers", "quantity": 5000, "line_total": 750.0}
    ],
    "refused": [],
    "blocked": [],
    "delivery_date": null,
    "notes": ""
  },
  "notes": "The following items could not be fulfilled: posters (qty 2000): No matching catalog item; tickets (qty 10000): No matching catalog item. "
}
```

**Key transparency elements:** `posters` and `tickets` explicitly listed as unavailable with polite reasons
and suggestions ("Poster paper", "Photo paper", "Sticky notes"). Available item (`Flyers`) still quoted
with 12% bulk discount. Customer is not left guessing why items were declined.

---

### Data Safety: What Customers Never See

The `internal_audit` dictionary (kept separate from `customer_reply`) contains raw telemetry that is
**never** shown to customers:

- Raw `_error` traces and exception messages
- Supplier cost ratio (70% of catalog price) — internal margin
- Exact cash balance and reserve threshold calculations
- Raw SQL query results and stock check internals
- Database schema and table names
- Exact stock counts (`current_stock`)

If any agent stage fails, the customer receives a polite fallback: *"We could not complete this request.
Please contact customer support."* — never a raw stack trace.

The `internal_audit` data is written to `internal_audit_log.jsonl` (developer-only, gitignored) and is
excluded from version control via `.gitignore`.

---