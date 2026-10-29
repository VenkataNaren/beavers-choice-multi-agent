# Agent Workflow & Architectural Description

## Overview

The Munder Difflin Multi-Agent System is a text-based, orchestrated pipeline that processes customer
paper-supply requests end-to-end: from raw email parsing to final sale confirmation. The system uses
**pydantic-ai** with an OpenAI-compatible proxy (Vocareum) and a **SQLite** ledger for all financial
and inventory state.

**Agent count: 4** (within the maximum of 5 allowed by the project specification).

---

## Architecture Diagram (Text Summary)

```
CUSTOMER
  |  request + date
  v
ORCHESTRATOR AGENT  (coordinates only, no tools)
  |  parses request into items, quantities, deadline, request date
  |  runs workers in order: Inventory -> Quoting -> Sales
  |
  +---> INVENTORY AGENT <----------------+
  |  |  check stock, decide restock     |
  |  |  verify cash & delivery time     |
  |  |  Out: fulfillable lines, ETA     |
  |  |  Out: rejected lines + reasons   |
  |  v                                  |
  +---> QUOTING AGENT  <----------------+
  |  |  price fulfillable lines         |
  |  |  apply bulk discount             |
  |  |  explain pricing rationale       |
  |  |  Out: itemised quote             |
  |  v                                  |
  +---> SALES AGENT   <----------------+
      |  finalize order or decline     |
      |  record sale or reject         |
      |  Out: confirmation or reason   |
      v
CUSTOMER REPLY  (quote, confirmation, or rejection with reason)
```

**Data flow**: Workers never call each other. The orchestrator passes each result to the next agent.
Solid two-way arrows = delegate and return results. Every tool receives the request date (YYYY-MM-DD)
so stock, cash, and delivery times match the day of the request.

---

## Agent Responsibilities

### 1. Orchestrator Agent (`process_customer_request`)
**Role**: Coordinates the four-stage pipeline. Does not call external business tools directly; it
invokes the other three agents sequentially and assembles the final response.

**Stages**:
1. **Triage** — delegates to `triage_agent` to parse the raw customer request into structured fields
   (request date, deadline, items, event type, job type, order size).
2. **Catalog Matching & Normalization** (code-level, not LLM-dependent):
   - Deduplicates items by name (merges quantities for duplicate SKUs).
   - Converts reams → sheets using `SHEETS_PER_REAM = 500` (code-level inspection of ream indicators).
   - Calls `match_catalog_item()` on every item. Unmatched items (e.g., "balloons", "A3 paper") are
     routed to `unavailable_items` and bypassed in quoting/sales.
3. **Inventory Check & Restock** — delegates to `inventory_agent`; also performs code-level pre-check
   of `check_stock_level()` for each line and builds a restock-needed summary for the agent.
4. **Quote** — delegates to `quoting_agent` for pricing on available items only.
5. **Sales** — performs code-level pre-sale stock validation via `check_stock_level()`; blocks oversells
   before calling `sales_agent`; delegates final sale recording to `sales_agent`.

**Output**: A structured dict containing `triage`, `inventory_report`, `quote`, `sales_report`,
`catalog_audit`, `stock_checks`, `blocked_sales_lines`, `request_date`, and `stage`.

---

### 2. Triage Agent
**Role**: Pure LLM parser (no tools). Converts unstructured customer text into a `TriageResult`
Pydantic model.

**Input**: Raw customer request string containing a parenthetical date, e.g.
`"(Date of request: 2025-04-01)"`.

**Output fields**:
| Field | Type | Description |
|-------|------|-------------|
| `request_date` | str | Date in the parenthetical (YYYY-MM-DD) |
| `customer_deadline` | str | Delivery deadline mentioned in the request (YYYY-MM-DD) |
| `items` | List[OrderLine] | `{item_name, quantity}` in SHEETS/UNITS (reams converted ×500) |
| `event_type` | str | Event (conference, party, festival, etc.) |
| `job_type` | str | Customer role (office manager, school teacher, etc.) |
| `order_size` | str | small / medium / large |
| `notes` | str | Special instructions |

**Tools**: None (pure LLM parsing).

**Helper functions used**: None directly (the LLM is instructed to use `SHEETS_PER_REAM = 500`).

---

### 3. Inventory Agent
**Role**: Ensure every requested item is in stock by the customer's deadline. Maps customer wording to
catalog names, checks stock, decides restock quantities, verifies cash and delivery time.

**Tools (mapped to starter helpers)**:

| Tool | Purpose | Starter Helper Function |
|------|---------|------------------------|
| `match_catalog_item(customer_phrase)` | Map customer wording to exact catalog item name | None (fuzzy match on `paper_supplies` list) |
| `check_stock_level(item, qty, date)` | Stock on hand, shortfall, restock quantity | `get_stock_level()` |
| `list_inventory_snapshot(date)` | Everything in stock; flags low-stock items | `get_all_inventory()` |
| `check_supplier_delivery(date, qty, deadline)` | Will restock arrive before customer deadline? | `get_supplier_delivery_date()` |
| `check_cash_available(cost, date)` | Confirm affordability while keeping cash reserve | `get_cash_balance()` |
| `place_restock_order(item, qty, date)` | Buy stock from supplier (cash goes down) | `create_transaction('stock_orders')` |

**Decision rules (system prompt)**:
1. Always call `match_catalog_item` first for each product.
2. For each matched item, call `check_stock_level` with quantity and request date.
3. If shortfall > 0:
   a. Call `check_supplier_delivery` with restock quantity and deadline.
   b. If `meets_deadline` is false, report deadline cannot be met.
   c. Call `check_cash_available` with estimated restock cost. If `can_afford` is false, report
      insufficient cash.
   d. If both checks pass, call `place_restock_order`.
4. Never breach the $5,000 cash reserve.
5. Supplier cost is 70% of catalog price; lead time: ≤10=0d, ≤100=1d, ≤1000=4d, >1000=7d.

**Helper functions used**: `get_stock_level`, `get_all_inventory`, `get_supplier_delivery_date`,
`get_cash_balance`, `create_transaction`.

---

### 4. Quoting Agent
**Role**: Produce a professional, transparent quote with correct pricing and bulk discounts for
fulfillable lines.

**Tools (mapped to starter helpers)**:

| Tool | Purpose | Starter Helper Function |
|------|---------|------------------------|
| `find_similar_quotes(keywords)` | Pull past quotes for pricing and wording style | `search_quote_history()` |
| `lookup_unit_price(item)` | Get catalog price per unit | None (reads `CATALOG_PRICES` dict) |
| `calculate_bulk_discount(order_lines)` | Price order and apply tiered bulk discount | None (pure Python pricing rules) |

**Discount tiers** (enforced in code via `DISCOUNT_TIERS`):
| Total Units | Discount |
|-------------|----------|
| ≥1000 | 12% |
| ≥500 | 8% |
| ≥100 | 5% |
| <100 | 0% |

**Required `quote_explanation` content** (system prompt):
- Item-by-item breakdown (quantity × unit price = line total)
- Bulk discount tier applied and amount saved
- Subtotal → discount → final total
- Estimated delivery timeline
- Any unavailable items noted politely
- Customer-friendly, transparent, professional tone

**Helper functions used**: `search_quote_history`.

---

### 5. Sales Agent
**Role**: Finalize the order when feasible; otherwise decline with a clear reason. Record the sale,
validate stock one last time, and report financial health.

**Tools (mapped to starter helpers)**:

| Tool | Purpose | Starter Helper Function |
|------|---------|------------------------|
| `run_financial_health_check(date)` | Review cash and assets before large orders | `generate_financial_report()` |
| `record_sale(item, qty, price, date)` | Record the sale (cash goes up); refuses if stock too low | `create_transaction('sales')` |

**Decision rules (system prompt)**:
1. Input: quote JSON from Quoting Agent and sale date.
2. For each known item line, call `record_sale(item_name, quantity, line_total, sale_date)`.
   - `record_sale` refuses if stock is insufficient.
3. After all lines, call `run_financial_health_check(sale_date)` to report cash, inventory value,
   and top sellers.
4. Return summary: items sold, total revenue, updated cash balance, any refused lines.

**Helper functions used**: `generate_financial_report`, `create_transaction`.

---

## Starter Helper Function Coverage

| Helper Function | Used By | Status |
|-----------------|---------|--------|
| `create_transaction` | `place_restock_order`, `record_sale` | ✅ |
| `get_all_inventory` | `list_inventory_snapshot` | ✅ |
| `get_stock_level` | `check_stock_level` | ✅ |
| `get_supplier_delivery_date` | `check_supplier_delivery` | ✅ |
| `get_cash_balance` | `check_cash_available`, `generate_financial_report` | ✅ |
| `generate_financial_report` | `run_financial_health_check` | ✅ |
| `search_quote_history` | `find_similar_quotes` | ✅ |
| `match_catalog_item` | Inventory Agent (code + LLM) | ✅ |
| `calculate_bulk_discount` | Quoting Agent | ✅ |

All starter helper functions are utilized within the tool definitions.

---

## Orchestrator Routing

```
raw_request
    |
    v
triage_agent.run_sync()  --> TriageResult (structured)
    |
    v
[Code: dedupe + ream→sheets + match_catalog_item on every item]
    |
    v
available_items  --> inventory_agent.run_sync()  --> inventory_report
    |
    v
available_items  --> quoting_agent.run_sync()    --> quote_data
    |
    v
[Code: pre-sale check_stock_level per line; block oversells]
    |
    v
sales_lines --> sales_agent.run_sync()           --> sales_report
    |
    v
final structured dict (written to test_results.csv)
```

---

## Non-Overlapping Responsibilities

| Agent | Primary Responsibility | Does NOT do |
|-------|----------------------|-------------|
| Triage | Parse raw text → structured fields | Stock checks, pricing, sales |
| Inventory | Stock availability & restock decisions | Pricing, sale recording |
| Quoting | Price calculation & quote narrative | Stock checks, sale recording |
| Sales | Record transactions & financial health | Restock decisions, quote generation |

Each agent has a distinct, non-overlapping domain. The orchestrator is the only component that
sequences them and assembles the final response.