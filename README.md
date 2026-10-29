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

The system separates internal telemetry (`internal_audit`) from the customer-facing reply (`customer_reply`). Below are three concrete examples from `test_results.csv` demonstrating price breakdowns, bulk discounts, delivery timelines, and polite unfulfillment reasons.

### Example 1 — Fulfilled order with bulk discount (Request 12)

**Customer input:** "I would like to order 200 sheets of colorful cardstock, 500 sheets of standard printer paper, and 100 paper napkins for our upcoming party. Please deliver these supplies by April 15, 2025." (2025-04-08)

**`customer_reply`:**

```json
{
  "request_date": "2025-04-08",
  "stage": "complete",
  "items_requested": [
    {"item_name": "colorful cardstock", "quantity": 200},
    {"item_name": "standard printer paper", "quantity": 500},
    {"item_name": "paper napkins", "quantity": 100}
  ],
  "available_items": [
    {"item_name": "Cardstock", "quantity": 200},
    {"item_name": "Standard copy paper", "quantity": 500},
    {"item_name": "Paper napkins", "quantity": 100}
  ],
  "unavailable_items": [],
  "quote": {
    "lines": [
      {"item_name": "Cardstock", "quantity": 200, "unit_price": 0.15, "line_total": 30.00},
      {"item_name": "Standard copy paper", "quantity": 500, "unit_price": 0.04, "line_total": 20.00},
      {"item_name": "Paper napkins", "quantity": 100, "unit_price": 0.02, "line_total": 2.00}
    ],
    "unknown_items": [],
    "total_units": 800,
    "subtotal": 52.00,
    "discount_percent": 8,
    "discount_amount": 4.16,
    "total_price": 47.84,
    "quote_explanation": "Thank you for considering Munder Difflin Paper Company for your party supplies! Below is a detailed breakdown of your order:\\n\\n- Cardstock: 200 sheets @ $0.15 each = $30.00\\n- Standard copy paper: 500 sheets @ $0.04 each = $20.00\\n- Paper napkins: 100 units @ $0.02 each = $2.00\\n\\n**Total Units**: 800 sheets\\n\\nYou qualify for an 8% bulk discount for orders of 500 or more total units, providing a discount amount of **$4.16**.\\n\\n**Subtotal**: $52.00 \\n**Discount**: -$4.16 \\n**Total Price**: $47.84 \\n\\nEstimated delivery for your order is within 5-7 business days... Thank you!"
  },
  "sales": {
    "items sold": [
      {"item": "Cardstock", "quantity": 200, "total price": 1000.00},
      {"item": "Standard copy paper", "quantity": 500, "total price": 250.00},
      {"item": "Paper napkins", "quantity": 100, "total price": 50.00}
    ],
    "total revenue": 1300.00,
    "updated cash balance": 36673.64
  },
  "notes": ""
}
```

**Key transparency elements:** Item-by-item pricing, 8% bulk discount tier explicitly stated ($4.16 saved), subtotal → discount → final total math, 5–7 business day delivery estimate, zero unavailable items.

---

### Example 2 — Partial fulfillment with blocked stock line (Request 9)

**Customer input:** "I would like to place an order for the following paper supplies for the reception: - 200 sheets of A4 white printer paper - 100 sheets of A3 glossy paper - 50 packets of 100% recycled kraft paper envelopes. I need these supplies delivered by April 10, 2025." (2025-04-07)

**`customer_reply`:**

```json
{
  "request_date": "2025-04-07",
  "stage": "complete",
  "items_requested": [
    {"item_name": "A4 white printer paper", "quantity": 200},
    {"item_name": "A3 glossy paper", "quantity": 100},
    {"item_name": "100% recycled kraft paper envelopes", "quantity": 5000}
  ],
  "available_items": [
    {"item_name": "Standard copy paper", "quantity": 200},
    {"item_name": "Recycled paper", "quantity": 5000}
  ],
  "unavailable_items": [
    {"item_name": "A3 glossy paper", "quantity": 100, "reason": "Paper size 'A3' is not in our catalog."}
  ],
  "quote": {
    "lines": [
      {"item_name": "Standard copy paper", "quantity": 200, "unit_price": 0.04, "line_total": 8.0},
      {"item_name": "Recycled paper", "quantity": 5000, "unit_price": 0.08, "line_total": 400.0}
    ],
    "unknown_items": [],
    "total_units": 5200,
    "subtotal": 408.00,
    "discount_percent": 12,
    "discount_amount": 48.96,
    "total_price": 359.04,
    "quote_explanation": "Dear valued customer,... **Bulk Discount Applied:** 12% for orders of 1000 units or more - you save $48.96! **Final Total:** $359.04 ..."
  },
  "sales": {
    "items sold": [],
    "total revenue": 0.00,
    "refusal_reason": "Insufficient stock after restock attempt"
  },
  "notes": "The following items could not be fulfilled: A3 glossy paper (qty 100): Paper size 'A3' is not in our catalog. The following items could not be sold due to stock constraints: Recycled paper (qty 5000): Insufficient stock after restock attempt."
}
```

**Key transparency elements:** Unavailable item (`A3 glossy paper`) explicitly named with reason ("not in our catalog"), blocked line (`Recycled paper`) politely explained with stock constraint reason, no internal profit margins or stack traces leaked.

---

### Example 3 — Unavailable item politely refused (Request 2)

**Customer input:** "I would like to place an order for 500 sheets of colorful poster paper, 300 roll of streamers, and 200 balloons for the parade. Please deliver the supplies by April 15, 2025." (2025-04-03)

**`customer_reply`:**

```json
{
  "request_date": "2025-04-03",
  "stage": "complete",
  "items_requested": [
    {"item_name": "colorful poster paper", "quantity": 500},
    {"item_name": "streamers", "quantity": 300},
    {"item_name": "balloons", "quantity": 200}
  ],
  "available_items": [
    {"item_name": "Poster paper", "quantity": 500},
    {"item_name": "Party streamers", "quantity": 300}
  ],
  "unavailable_items": [
    {"item_name": "balloons", "quantity": 200, "reason": "No matching catalog item.", "suggestions": []}
  ],
  "quote": {
    "lines": [
      {"item_name": "Poster paper", "quantity": 1, "unit_price": 0.25, "line_total": 0.25},
      {"item_name": "Party streamers", "quantity": 300, "unit_price": 0.05, "line_total": 15.0}
    ],
    "unknown_items": [],
    "total_units": 301,
    "subtotal": 15.25,
    "discount_percent": 5,
    "discount_amount": 0.76,
    "total_price": 14.49,
    "quote_explanation": "Thank you for considering Munder Difflin for your upcoming parade event! ... **Total Units**: 301 units\\n\\nSince your order includes a total of 301 units, you qualify for a bulk discount of 5%. Your savings from this discount is $0.76."
  },
  "sales": {
    "refusal_reason": "Line totals were zero; sale could not be recorded"
  },
  "notes": "The following items could not be fulfilled: balloons (qty 200): No matching catalog item."
}
```

**Key transparency elements:** `balloons` explicitly listed as unavailable with a polite reason, available items (`Poster paper`, `Party streamers`) still quoted with 5% bulk discount, customer is not left guessing why an item was declined.

---

### Data Safety: What Customers Never See

The `internal_audit` dictionary (kept separate from `customer_reply`) contains raw telemetry that is **never** shown to customers:

- Raw `_error` traces and exception messages
- Supplier cost ratio (70% of catalog price) — internal margin
- Exact cash balance and reserve threshold calculations
- Raw SQL query results and stock check internals
- Database schema and table names

If any agent stage fails, the customer receives a polite fallback: *"We could not complete this request, please contact customer support."* — never a raw stack trace.

---