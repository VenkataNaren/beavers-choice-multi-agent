"""Offline smoke test for the agent tools. Makes NO API calls and costs no budget.

Run from the project folder:  python smoke_test_tools.py
Delete this file before zipping the submission (only one .py file is allowed).
"""
import os

# Start from a clean database so the numbers are repeatable.
if os.path.exists("munder_difflin.db"):
    os.remove("munder_difflin.db")

import project_starter as ps  # noqa: E402

ps.init_database(ps.db_engine)
DAY = "2025-04-04"
failures = []


def check(label, condition, detail=""):
    """Print PASS/FAIL for one expectation."""
    print(f"[{'PASS' if condition else 'FAIL'}] {label} {detail}")
    if not condition:
        failures.append(label)


print("\n--- 1. Name matching ---")
expected = {
    "A4 glossy paper": "Glossy paper",
    "heavy cardstock (white)": "Cardstock",
    "colored paper (assorted colors)": "Colored paper",
    "colorful poster paper": "Poster paper",
    "streamers": "Party streamers",
    "printer paper": "Standard copy paper",
    "A4 paper": "A4 paper",
    "250 gsm cardstock": "250 gsm cardstock",
    "paper cups": "Paper cups",
    "balloons": None,
    "A3 paper": None,
}
for phrase, want in expected.items():
    got = ps.match_catalog_item(phrase)["item_name"]
    check(f"'{phrase}' -> {want}", got == want, f"(got {got})")

print("\n--- 2. Stock, delivery, cash ---")
stock = ps.check_stock_level("Glossy paper", 200, DAY)
check("Glossy paper 200 can ship from stock", stock["can_fulfil_from_stock"], str(stock))
short = ps.check_stock_level("A4 paper", 10000, DAY)
check("A4 paper 10,000 needs a restock", short["shortfall"] > 0, str(short))
check("Unknown name is rejected", "error" in ps.check_stock_level("Balloons", 5, DAY))
check("Bad date is rejected", "error" in ps.check_stock_level("A4 paper", 5, "04/04/25"))
snap = ps.list_inventory_snapshot(DAY)
print("    in stock:", len(snap["items_in_stock"]), "| low stock:", snap["low_stock_items"])
delivery = ps.check_supplier_delivery(DAY, 10000, "2025-04-15")
check("10,000 units ordered 04-04 arrive 04-11, deadline met",
      delivery["delivery_date"] == "2025-04-11" and delivery["meets_deadline"] is True, str(delivery))
check("Impossible deadline detected",
      ps.check_supplier_delivery(DAY, 10000, "2025-04-06")["meets_deadline"] is False)

print("\n--- 3. Restock changes cash ---")
cash_before = ps.get_cash_balance(DAY)
order = ps.place_restock_order("A4 paper", 10000, DAY)
cash_after = ps.get_cash_balance(DAY)
check("Restock recorded", order.get("status") == "ordered", str(order))
check("Cash went down", cash_after < cash_before, f"({cash_before:.2f} -> {cash_after:.2f})")
check("Stock went up", ps.check_stock_level("A4 paper", 1, DAY)["current_stock"] > 9000)
huge = ps.place_restock_order("Table covers", 1_000_000, DAY)
check("Restock beyond cash reserve refused", huge.get("status") == "refused", str(huge))

print("\n--- 4. Quote arithmetic ---")
quote = ps.calculate_bulk_discount([
    ps.OrderLine(item_name="Glossy paper", quantity=200),
    ps.OrderLine(item_name="Cardstock", quantity=100),
    ps.OrderLine(item_name="Balloons", quantity=200),
])
print("   ", quote)
check("Subtotal 200*0.20 + 100*0.15 = 55.00", quote["subtotal"] == 55.0)
check("300 units get 5% discount", quote["discount_percent"] == 5 and quote["total_price"] == 52.25)
check("Unknown item flagged", quote["unknown_items"] == ["Balloons"])
history = ps.find_similar_quotes(["meeting", "ceremony"])
print("    similar quotes found:", len(history))

print("\n--- 5. Sales change cash ---")
cash_before = ps.get_cash_balance(DAY)
sale = ps.record_sale("Glossy paper", 200, 38.0, DAY)
check("Sale recorded", sale.get("status") == "recorded", str(sale))
check("Cash went up", ps.get_cash_balance(DAY) > cash_before)
oversell = ps.record_sale("Glossy paper", 5000, 900.0, DAY)
check("Overselling refused", oversell.get("status") == "refused", str(oversell))

print("\n--- 6. Financial health check ---")
health = ps.run_financial_health_check(DAY)
print("   ", health)
check("Report has cash and assets", health["total_assets"] > 0)

print("\nRESULT:", "ALL PASSED" if not failures else f"{len(failures)} FAILED: {failures}")
