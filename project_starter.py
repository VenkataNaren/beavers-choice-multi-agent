import pandas as pd
import numpy as np
import os
import time
import dotenv
import ast
from sqlalchemy.sql import text
from datetime import datetime, timedelta
import re
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Union, Any, Literal
from sqlalchemy import create_engine, Engine
from pydantic import BaseModel, Field
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("munder_difflin")

# Create an SQLite database
db_engine = create_engine("sqlite:///munder_difflin.db")

# List containing the different kinds of papers
paper_supplies = [
    # Paper Types (priced per sheet unless specified)
    {"item_name": "A4 paper",                         "category": "paper",        "unit_price": 0.05},
    {"item_name": "Letter-sized paper",              "category": "paper",        "unit_price": 0.06},
    {"item_name": "Cardstock",                        "category": "paper",        "unit_price": 0.15},
    {"item_name": "Colored paper",                    "category": "paper",        "unit_price": 0.10},
    {"item_name": "Glossy paper",                     "category": "paper",        "unit_price": 0.20},
    {"item_name": "Matte paper",                      "category": "paper",        "unit_price": 0.18},
    {"item_name": "Recycled paper",                   "category": "paper",        "unit_price": 0.08},
    {"item_name": "Eco-friendly paper",               "category": "paper",        "unit_price": 0.12},
    {"item_name": "Poster paper",                     "category": "paper",        "unit_price": 0.25},
    {"item_name": "Banner paper",                     "category": "paper",        "unit_price": 0.30},
    {"item_name": "Kraft paper",                      "category": "paper",        "unit_price": 0.10},
    {"item_name": "Construction paper",               "category": "paper",        "unit_price": 0.07},
    {"item_name": "Wrapping paper",                   "category": "paper",        "unit_price": 0.15},
    {"item_name": "Glitter paper",                    "category": "paper",        "unit_price": 0.22},
    {"item_name": "Decorative paper",                 "category": "paper",        "unit_price": 0.18},
    {"item_name": "Letterhead paper",                 "category": "paper",        "unit_price": 0.12},
    {"item_name": "Legal-size paper",                 "category": "paper",        "unit_price": 0.08},
    {"item_name": "Crepe paper",                      "category": "paper",        "unit_price": 0.05},
    {"item_name": "Photo paper",                      "category": "paper",        "unit_price": 0.25},
    {"item_name": "Uncoated paper",                   "category": "paper",        "unit_price": 0.06},
    {"item_name": "Butcher paper",                    "category": "paper",        "unit_price": 0.10},
    {"item_name": "Heavyweight paper",                "category": "paper",        "unit_price": 0.20},
    {"item_name": "Standard copy paper",              "category": "paper",        "unit_price": 0.04},
    {"item_name": "Bright-colored paper",             "category": "paper",        "unit_price": 0.12},
    {"item_name": "Patterned paper",                  "category": "paper",        "unit_price": 0.15},

    # Product Types (priced per unit)
    {"item_name": "Paper plates",                     "category": "product",      "unit_price": 0.10},  # per plate
    {"item_name": "Paper cups",                       "category": "product",      "unit_price": 0.08},  # per cup
    {"item_name": "Paper napkins",                    "category": "product",      "unit_price": 0.02},  # per napkin
    {"item_name": "Disposable cups",                  "category": "product",      "unit_price": 0.10},  # per cup
    {"item_name": "Table covers",                     "category": "product",      "unit_price": 1.50},  # per cover
    {"item_name": "Envelopes",                        "category": "product",      "unit_price": 0.05},  # per envelope
    {"item_name": "Sticky notes",                     "category": "product",      "unit_price": 0.03},  # per sheet
    {"item_name": "Notepads",                         "category": "product",      "unit_price": 2.00},  # per pad
    {"item_name": "Invitation cards",                 "category": "product",      "unit_price": 0.50},  # per card
    {"item_name": "Flyers",                           "category": "product",      "unit_price": 0.15},  # per flyer
    {"item_name": "Party streamers",                  "category": "product",      "unit_price": 0.05},  # per roll
    {"item_name": "Decorative adhesive tape (washi tape)", "category": "product", "unit_price": 0.20},  # per roll
    {"item_name": "Paper party bags",                 "category": "product",      "unit_price": 0.25},  # per bag
    {"item_name": "Name tags with lanyards",          "category": "product",      "unit_price": 0.75},  # per tag
    {"item_name": "Presentation folders",             "category": "product",      "unit_price": 0.50},  # per folder

    # Large-format items (priced per unit)
    {"item_name": "Large poster paper (24x36 inches)", "category": "large_format", "unit_price": 1.00},
    {"item_name": "Rolls of banner paper (36-inch width)", "category": "large_format", "unit_price": 2.50},

    # Specialty papers
    {"item_name": "100 lb cover stock",               "category": "specialty",    "unit_price": 0.50},
    {"item_name": "80 lb text paper",                 "category": "specialty",    "unit_price": 0.40},
    {"item_name": "250 gsm cardstock",                "category": "specialty",    "unit_price": 0.30},
    {"item_name": "220 gsm poster paper",             "category": "specialty",    "unit_price": 0.35},
]

# Given below are some utility functions you can use to implement your multi-agent system

def generate_sample_inventory(paper_supplies: list, coverage: float = 0.4, seed: int = 137) -> pd.DataFrame:
    """
    Generate inventory for exactly a specified percentage of items from the full paper supply list.

    This function randomly selects exactly `coverage` × N items from the `paper_supplies` list,
    and assigns each selected item:
    - a random stock quantity between 200 and 800,
    - a minimum stock level between 50 and 150.

    The random seed ensures reproducibility of selection and stock levels.

    Args:
        paper_supplies (list): A list of dictionaries, each representing a paper item with
                               keys 'item_name', 'category', and 'unit_price'.
        coverage (float, optional): Fraction of items to include in the inventory (default is 0.4, or 40%).
        seed (int, optional): Random seed for reproducibility (default is 137).

    Returns:
        pd.DataFrame: A DataFrame with the selected items and assigned inventory values, including:
                      - item_name
                      - category
                      - unit_price
                      - current_stock
                      - min_stock_level
    """
    # Ensure reproducible random output
    np.random.seed(seed)

    # Calculate number of items to include based on coverage
    num_items = int(len(paper_supplies) * coverage)

    # Randomly select item indices without replacement
    selected_indices = np.random.choice(
        range(len(paper_supplies)),
        size=num_items,
        replace=False
    )

    # Extract selected items from paper_supplies list
    selected_items = [paper_supplies[i] for i in selected_indices]

    # Construct inventory records
    inventory = []
    for item in selected_items:
        inventory.append({
            "item_name": item["item_name"],
            "category": item["category"],
            "unit_price": item["unit_price"],
            "current_stock": np.random.randint(200, 800),  # Realistic stock range
            "min_stock_level": np.random.randint(50, 150)  # Reasonable threshold for reordering
        })

    # Return inventory as a pandas DataFrame
    return pd.DataFrame(inventory)

def init_database(db_engine: Engine, seed: int = 137) -> Engine:
    """
    Set up the Munder Difflin database with all required tables and initial records.

    This function performs the following tasks:
    - Creates the 'transactions' table for logging stock orders and sales
    - Loads customer inquiries from 'quote_requests.csv' into a 'quote_requests' table
    - Loads previous quotes from 'quotes.csv' into a 'quotes' table, extracting useful metadata
    - Generates a random subset of paper inventory using `generate_sample_inventory`
    - Inserts initial financial records including available cash and starting stock levels

    Args:
        db_engine (Engine): A SQLAlchemy engine connected to the SQLite database.
        seed (int, optional): A random seed used to control reproducibility of inventory stock levels.
                              Default is 137.

    Returns:
        Engine: The same SQLAlchemy engine, after initializing all necessary tables and records.

    Raises:
        Exception: If an error occurs during setup, the exception is printed and raised.
    """
    try:
        # ----------------------------
        # 1. Create an empty 'transactions' table schema
        # ----------------------------
        transactions_schema = pd.DataFrame({
            "id": [],
            "item_name": [],
            "transaction_type": [],  # 'stock_orders' or 'sales'
            "units": [],             # Quantity involved
            "price": [],             # Total price for the transaction
            "transaction_date": [],  # ISO-formatted date
        })
        transactions_schema.to_sql("transactions", db_engine, if_exists="replace", index=False)

        # Set a consistent starting date
        initial_date = datetime(2025, 1, 1).isoformat()

        # ----------------------------
        # 2. Load and initialize 'quote_requests' table
        # ----------------------------
        quote_requests_df = pd.read_csv("quote_requests.csv")
        quote_requests_df["id"] = range(1, len(quote_requests_df) + 1)
        quote_requests_df.to_sql("quote_requests", db_engine, if_exists="replace", index=False)

        # ----------------------------
        # 3. Load and transform 'quotes' table
        # ----------------------------
        quotes_df = pd.read_csv("quotes.csv")
        quotes_df["request_id"] = range(1, len(quotes_df) + 1)
        quotes_df["order_date"] = initial_date

        # Unpack metadata fields (job_type, order_size, event_type) if present
        if "request_metadata" in quotes_df.columns:
            quotes_df["request_metadata"] = quotes_df["request_metadata"].apply(
                lambda x: ast.literal_eval(x) if isinstance(x, str) else x
            )
            quotes_df["job_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("job_type", ""))
            quotes_df["order_size"] = quotes_df["request_metadata"].apply(lambda x: x.get("order_size", ""))
            quotes_df["event_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("event_type", ""))

        # Retain only relevant columns
        quotes_df = quotes_df[[
            "request_id",
            "total_amount",
            "quote_explanation",
            "order_date",
            "job_type",
            "order_size",
            "event_type"
        ]]
        quotes_df.to_sql("quotes", db_engine, if_exists="replace", index=False)

        # ----------------------------
        # 4. Generate inventory and seed stock
        # ----------------------------
        inventory_df = generate_sample_inventory(paper_supplies, seed=seed)

        # Seed initial transactions
        initial_transactions = []

        # Add a starting cash balance via a dummy sales transaction
        initial_transactions.append({
            "item_name": None,
            "transaction_type": "sales",
            "units": None,
            "price": 50000.0,
            "transaction_date": initial_date,
        })

        # Add one stock order transaction per inventory item
        for _, item in inventory_df.iterrows():
            initial_transactions.append({
                "item_name": item["item_name"],
                "transaction_type": "stock_orders",
                "units": item["current_stock"],
                "price": item["current_stock"] * item["unit_price"],
                "transaction_date": initial_date,
            })

        # Commit transactions to database
        pd.DataFrame(initial_transactions).to_sql("transactions", db_engine, if_exists="append", index=False)

        # Save the inventory reference table
        inventory_df.to_sql("inventory", db_engine, if_exists="replace", index=False)

        return db_engine

    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

def create_transaction(
    item_name: str,
    transaction_type: str,
    quantity: int,
    price: float,
    date: Union[str, datetime],
) -> int:
    """
    This function records a transaction of type 'stock_orders' or 'sales' with a specified
    item name, quantity, total price, and transaction date into the 'transactions' table of the database.

    Args:
        item_name (str): The name of the item involved in the transaction.
        transaction_type (str): Either 'stock_orders' or 'sales'.
        quantity (int): Number of units involved in the transaction.
        price (float): Total price of the transaction.
        date (str or datetime): Date of the transaction in ISO 8601 format.

    Returns:
        int: The ID of the newly inserted transaction.

    Raises:
        ValueError: If `transaction_type` is not 'stock_orders' or 'sales'.
        Exception: For other database or execution errors.
    """
    try:
        # Convert datetime to ISO string if necessary
        date_str = date.isoformat() if isinstance(date, datetime) else date

        # Validate transaction type
        if transaction_type not in {"stock_orders", "sales"}:
            raise ValueError("Transaction type must be 'stock_orders' or 'sales'")

        # Prepare transaction record as a single-row DataFrame
        transaction = pd.DataFrame([{
            "item_name": item_name,
            "transaction_type": transaction_type,
            "units": quantity,
            "price": price,
            "transaction_date": date_str,
        }])

        # Insert the record into the database
        transaction.to_sql("transactions", db_engine, if_exists="append", index=False)

        # Fetch and return the ID of the inserted row
        result = pd.read_sql("SELECT last_insert_rowid() as id", db_engine)
        return int(result.iloc[0]["id"])

    except Exception as e:
        print(f"Error creating transaction: {e}")
        raise

def get_all_inventory(as_of_date: str) -> Dict[str, int]:
    """
    Retrieve a snapshot of available inventory as of a specific date.

    This function calculates the net quantity of each item by summing
    all stock orders and subtracting all sales up to and including the given date.

    Only items with positive stock are included in the result.

    Args:
        as_of_date (str): ISO-formatted date string (YYYY-MM-DD) representing the inventory cutoff.

    Returns:
        Dict[str, int]: A dictionary mapping item names to their current stock levels.
    """
    # SQL query to compute stock levels per item as of the given date
    query = """
        SELECT
            item_name,
            SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END) as stock
        FROM transactions
        WHERE item_name IS NOT NULL
        AND transaction_date <= :as_of_date
        GROUP BY item_name
        HAVING stock > 0
    """

    # Execute the query with the date parameter
    result = pd.read_sql(query, db_engine, params={"as_of_date": as_of_date})

    # Convert the result into a dictionary {item_name: stock}
    return dict(zip(result["item_name"], result["stock"]))

def get_stock_level(item_name: str, as_of_date: Union[str, datetime]) -> pd.DataFrame:
    """
    Retrieve the stock level of a specific item as of a given date.

    This function calculates the net stock by summing all 'stock_orders' and
    subtracting all 'sales' transactions for the specified item up to the given date.

    Args:
        item_name (str): The name of the item to look up.
        as_of_date (str or datetime): The cutoff date (inclusive) for calculating stock.

    Returns:
        pd.DataFrame: A single-row DataFrame with columns 'item_name' and 'current_stock'.
    """
    # Convert date to ISO string format if it's a datetime object
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    # SQL query to compute net stock level for the item
    stock_query = """
        SELECT
            item_name,
            COALESCE(SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END), 0) AS current_stock
        FROM transactions
        WHERE item_name = :item_name
        AND transaction_date <= :as_of_date
    """

    # Execute query and return result as a DataFrame
    return pd.read_sql(
        stock_query,
        db_engine,
        params={"item_name": item_name, "as_of_date": as_of_date},
    )

def get_supplier_delivery_date(input_date_str: str, quantity: int) -> str:
    """
    Estimate the supplier delivery date based on the requested order quantity and a starting date.

    Delivery lead time increases with order size:
        - ≤10 units: same day
        - 11–100 units: 1 day
        - 101–1000 units: 4 days
        - >1000 units: 7 days

    Args:
        input_date_str (str): The starting date in ISO format (YYYY-MM-DD).
        quantity (int): The number of units in the order.

    Returns:
        str: Estimated delivery date in ISO format (YYYY-MM-DD).
    """
    # Debug log (comment out in production if needed)
    print(f"FUNC (get_supplier_delivery_date): Calculating for qty {quantity} from date string '{input_date_str}'")

    # Attempt to parse the input date
    try:
        input_date_dt = datetime.fromisoformat(input_date_str.split("T")[0])
    except (ValueError, TypeError):
        # Fallback to current date on format error
        print(f"WARN (get_supplier_delivery_date): Invalid date format '{input_date_str}', using today as base.")
        input_date_dt = datetime.now()

    # Determine delivery delay based on quantity
    if quantity <= 10:
        days = 0
    elif quantity <= 100:
        days = 1
    elif quantity <= 1000:
        days = 4
    else:
        days = 7

    # Add delivery days to the starting date
    delivery_date_dt = input_date_dt + timedelta(days=days)

    # Return formatted delivery date
    return delivery_date_dt.strftime("%Y-%m-%d")

def get_cash_balance(as_of_date: Union[str, datetime]) -> float:
    """
    Calculate the current cash balance as of a specified date.

    The balance is computed by subtracting total stock purchase costs ('stock_orders')
    from total revenue ('sales') recorded in the transactions table up to the given date.

    Args:
        as_of_date (str or datetime): The cutoff date (inclusive) in ISO format or as a datetime object.

    Returns:
        float: Net cash balance as of the given date. Returns 0.0 if no transactions exist or an error occurs.
    """
    try:
        # Convert date to ISO format if it's a datetime object
        if isinstance(as_of_date, datetime):
            as_of_date = as_of_date.isoformat()

        # Query all transactions on or before the specified date
        transactions = pd.read_sql(
            "SELECT * FROM transactions WHERE transaction_date <= :as_of_date",
            db_engine,
            params={"as_of_date": as_of_date},
        )

        # Compute the difference between sales and stock purchases
        if not transactions.empty:
            total_sales = transactions.loc[transactions["transaction_type"] == "sales", "price"].sum()
            total_purchases = transactions.loc[transactions["transaction_type"] == "stock_orders", "price"].sum()
            return float(total_sales - total_purchases)

        return 0.0

    except Exception as e:
        print(f"Error getting cash balance: {e}")
        return 0.0


def generate_financial_report(as_of_date: Union[str, datetime]) -> Dict:
    """
    Generate a complete financial report for the company as of a specific date.

    This includes:
    - Cash balance
    - Inventory valuation
    - Combined asset total
    - Itemized inventory breakdown
    - Top 5 best-selling products

    Args:
        as_of_date (str or datetime): The date (inclusive) for which to generate the report.

    Returns:
        Dict: A dictionary containing the financial report fields:
            - 'as_of_date': The date of the report
            - 'cash_balance': Total cash available
            - 'inventory_value': Total value of inventory
            - 'total_assets': Combined cash and inventory value
            - 'inventory_summary': List of items with stock and valuation details
            - 'top_selling_products': List of top 5 products by revenue
    """
    # Normalize date input
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    # Get current cash balance
    cash = get_cash_balance(as_of_date)

    # Get current inventory snapshot
    inventory_df = pd.read_sql("SELECT * FROM inventory", db_engine)
    inventory_value = 0.0
    inventory_summary = []

    # Compute total inventory value and summary by item
    for _, item in inventory_df.iterrows():
        stock_info = get_stock_level(item["item_name"], as_of_date)
        stock = stock_info["current_stock"].iloc[0]
        item_value = stock * item["unit_price"]
        inventory_value += item_value

        inventory_summary.append({
            "item_name": item["item_name"],
            "stock": stock,
            "unit_price": item["unit_price"],
            "value": item_value,
        })

    # Identify top-selling products by revenue
    top_sales_query = """
        SELECT item_name, SUM(units) as total_units, SUM(price) as total_revenue
        FROM transactions
        WHERE transaction_type = 'sales' AND transaction_date <= :date
        GROUP BY item_name
        ORDER BY total_revenue DESC
        LIMIT 5
    """
    top_sales = pd.read_sql(top_sales_query, db_engine, params={"date": as_of_date})
    top_selling_products = top_sales.to_dict(orient="records")

    return {
        "as_of_date": as_of_date,
        "cash_balance": cash,
        "inventory_value": inventory_value,
        "total_assets": cash + inventory_value,
        "inventory_summary": inventory_summary,
        "top_selling_products": top_selling_products,
    }


def search_quote_history(search_terms: List[str], limit: int = 5) -> List[Dict]:
    """
    Retrieve a list of historical quotes that match any of the provided search terms.

    The function searches both the original customer request (from `quote_requests`) and
    the explanation for the quote (from `quotes`) for each keyword. Results are sorted by
    most recent order date and limited by the `limit` parameter.

    Args:
        search_terms (List[str]): List of terms to match against customer requests and explanations.
        limit (int, optional): Maximum number of quote records to return. Default is 5.

    Returns:
        List[Dict]: A list of matching quotes, each represented as a dictionary with fields:
            - original_request
            - total_amount
            - quote_explanation
            - job_type
            - order_size
            - event_type
            - order_date
    """
    conditions = []
    params = {}

    # Build SQL WHERE clause using LIKE filters for each search term
    for i, term in enumerate(search_terms):
        param_name = f"term_{i}"
        conditions.append(
            f"(LOWER(qr.response) LIKE :{param_name} OR "
            f"LOWER(q.quote_explanation) LIKE :{param_name})"
        )
        params[param_name] = f"%{term.lower()}%"

    # Combine conditions; fallback to always-true if no terms provided
    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Final SQL query to join quotes with quote_requests
    query = f"""
        SELECT
            qr.response AS original_request,
            q.total_amount,
            q.quote_explanation,
            q.job_type,
            q.order_size,
            q.event_type,
            q.order_date
        FROM quotes q
        JOIN quote_requests qr ON q.request_id = qr.id
        WHERE {where_clause}
        ORDER BY q.order_date DESC
        LIMIT {limit}
    """

    # Execute parameterized query
    with db_engine.connect() as conn:
        result = conn.execute(text(query), params)
        return [dict(row._mapping) for row in result]

########################
########################
########################
# YOUR MULTI AGENT STARTS HERE
########################
########################
########################


# ---------------------------------------------------------------------------
# Configuration: model, proxy and business rules
# ---------------------------------------------------------------------------
dotenv.load_dotenv()

MODEL_NAME = "gpt-4o-mini"                           # model expected by the Udacity proxy
VOCAREUM_BASE_URL = "https://openai.vocareum.com/v1"  # OpenAI-compatible proxy

SUPPLIER_COST_RATIO = 0.70   # we pay suppliers 70% of the catalog unit price
CASH_RESERVE = 5000.0        # never let a restock push cash below this amount
DEFAULT_MIN_STOCK = 100      # reorder buffer for items with no minimum on file
SHEETS_PER_REAM = 500        # used when customers order paper by the ream

# Bulk discount tiers as (minimum total units in the order, discount rate).
# The best discount (12%) still leaves a margin above the 70% supplier cost.
DISCOUNT_TIERS = [(1000, 0.12), (500, 0.08), (100, 0.05)]

# Catalog price lookup built from the starter's paper_supplies list.
CATALOG_PRICES: Dict[str, float] = {
    item["item_name"]: item["unit_price"] for item in paper_supplies
}


def build_model() -> OpenAIChatModel:
    """Create the pydantic-ai chat model that talks to the Vocareum proxy.

    The API key is read from the UDACITY_OPENAI_API_KEY environment variable
    (loaded from .env) so it never appears in the source code.
    """
    api_key = os.getenv("UDACITY_OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("UDACITY_OPENAI_API_KEY is not set. Add it to your .env file.")
    provider = OpenAIProvider(base_url=VOCAREUM_BASE_URL, api_key=api_key)
    return OpenAIChatModel(MODEL_NAME, provider=provider)


# ---------------------------------------------------------------------------
# Small shared helpers (not agent tools)
# ---------------------------------------------------------------------------
class OrderLine(BaseModel):
    """One line of a customer order: a catalog item name and a quantity."""

    item_name: str
    quantity: int


def _clean_date(date_str: str) -> str:
    """Return a date as YYYY-MM-DD, or raise ValueError if it cannot be parsed."""
    return datetime.strptime(str(date_str).strip()[:10], "%Y-%m-%d").strftime("%Y-%m-%d")


def _stock_on_hand(item_name: str, as_of_date: str) -> int:
    """Net stock of one item on a date, using the starter's get_stock_level."""
    stock_df = get_stock_level(item_name, as_of_date)
    return int(stock_df["current_stock"].iloc[0])


def _min_stock_level(item_name: str) -> int:
    """Minimum stock level on file for an item (falls back to DEFAULT_MIN_STOCK)."""
    rows = pd.read_sql(
        "SELECT min_stock_level FROM inventory WHERE item_name = :name",
        db_engine,
        params={"name": item_name},
    )
    return int(rows["min_stock_level"].iloc[0]) if not rows.empty else DEFAULT_MIN_STOCK


def _has_ream_indicator(item_name: str) -> bool:
    """Check if item name suggests quantity is in reams rather than sheets."""
    lowered = item_name.lower()
    ream_keywords = {"ream", "reams", "box", "boxes", "pack", "packs", "bundle", "bundles"}
    return any(kw in lowered for kw in ream_keywords)


def _convert_reams_to_sheets(item_name: str, quantity: int) -> tuple:
    """Convert ream-based quantities to sheets using SHEETS_PER_REAM.

    Returns (cleaned_item_name, quantity_in_sheets).
    """
    if _has_ream_indicator(item_name):
        cleaned = item_name
        for kw in ["ream", "reams", "box", "boxes", "pack", "packs", "bundle", "bundles"]:
            cleaned = re.sub(rf"\b{kw}\b", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned, quantity * SHEETS_PER_REAM
    return item_name, quantity


def _deduplicate_items(items: List[OrderLine]) -> List[OrderLine]:
    """Merge duplicate OrderLines by item_name, summing quantities."""
    merged: Dict[str, int] = {}
    for line in items:
        name = line.item_name.strip()
        merged[name] = merged.get(name, 0) + line.quantity
    return [OrderLine(item_name=name, quantity=qty) for name, qty in merged.items()]


# ---------------------------------------------------------------------------
# Catalog name matching (customer wording -> exact database item name)
# ---------------------------------------------------------------------------
# Common customer phrases mapped to catalog names. These are design assumptions
# (for example "printer paper" is treated as "Standard copy paper").
ITEM_ALIASES = {
    "glossy": "Glossy paper",
    "matte": "Matte paper",
    "cardstock": "Cardstock",
    "card stock": "Cardstock",
    "heavy cardstock": "Cardstock",
    "colored paper": "Colored paper",
    "coloured paper": "Colored paper",
    "colorful paper": "Colored paper",
    "colored": "Colored paper",
    "poster paper": "Poster paper",
    "colorful poster paper": "Poster paper",
    "poster board": "Poster paper",
    "streamers": "Party streamers",
    "printer paper": "Standard copy paper",
    "copy paper": "Standard copy paper",
    "standard paper": "Standard copy paper",
    "plates": "Paper plates",
    "cups": "Paper cups",
    "napkins": "Paper napkins",
    "tablecloths": "Table covers",
    "table cloths": "Table covers",
    "washi tape": "Decorative adhesive tape (washi tape)",
    "decorative tape": "Decorative adhesive tape (washi tape)",
    "name tags": "Name tags with lanyards",
    "lanyards": "Name tags with lanyards",
    "folders": "Presentation folders",
    "invitations": "Invitation cards",
    "party bags": "Paper party bags",
    "banner": "Banner paper",
    "banners": "Banner paper",
    "eco friendly paper": "Eco-friendly paper",
    "recycled": "Recycled paper",
    "kraft": "Kraft paper",
    "glitter": "Glitter paper",
    "legal paper": "Legal-size paper",
    "letter paper": "Letter-sized paper",
    "sticky notes": "Sticky notes",
    "notepads": "Notepads",
}

_FILLER_WORDS = {"of", "the", "a", "an", "for", "and", "in", "sheet", "roll", "pack", "ream", "box"}


def _canonical(text: str) -> str:
    """Lower-case, drop brackets and punctuation, and strip plural 's' from each word."""
    text = re.sub(r"\([^)]*\)", " ", text.lower())
    text = re.sub(r"[^a-z0-9 ]", " ", text.replace("-", " "))
    words = []
    for word in text.split():
        if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
            word = word[:-1]
        words.append(word)
    return " ".join(words)


CATALOG_CANONICAL = {_canonical(name): name for name in CATALOG_PRICES}
# Longest aliases first so "colorful poster paper" wins over "colored".
ALIAS_CANONICAL = sorted(
    ((_canonical(phrase), name) for phrase, name in ITEM_ALIASES.items()),
    key=lambda pair: len(pair[0]),
    reverse=True,
)


def _match_result(item_name: Optional[str], method: str, note: str, suggestions=None) -> Dict:
    """Build the dictionary returned by match_catalog_item."""
    return {
        "matched": item_name is not None,
        "item_name": item_name,
        "unit_price": CATALOG_PRICES.get(item_name) if item_name else None,
        "match_method": method,
        "suggestions": suggestions or [],
        "note": note,
    }


# ---------------------------------------------------------------------------
# TOOLS FOR THE INVENTORY AGENT
# ---------------------------------------------------------------------------
def match_catalog_item(customer_phrase: str) -> Dict:
    """Map the customer's wording for a product to the exact catalog item name.

    Always call this first for every requested product. If matched is false the
    product is not sold by the company and must be reported as unavailable.
    """
    canon = _canonical(customer_phrase)

    # 1. Exact catalog name.
    if canon in CATALOG_CANONICAL:
        return _match_result(CATALOG_CANONICAL[canon], "exact", "Exact catalog match.")

    # 2. Paper size codes (A3, A5, B4...) must exist in the catalog, otherwise
    #    "A3 paper" would wrongly fuzzy-match "A4 paper".
    for size_code in re.findall(r"\b[abc]\d\b", canon):
        if not any(size_code in name.split() for name in CATALOG_CANONICAL):
            return _match_result(None, "none", f"Paper size '{size_code.upper()}' is not in our catalog.")

    # 3. Known customer phrases (whole-word match, longest phrase first).
    for alias, item_name in ALIAS_CANONICAL:
        if re.search(rf"\b{re.escape(alias)}\b", canon):
            return _match_result(item_name, "alias", f"Interpreted '{customer_phrase}' as '{item_name}'.")

    # 4. Fuzzy fallback on the words left after removing filler words.
    query_words = {w for w in canon.split() if w not in _FILLER_WORDS}
    scored = []
    for name_canon, item_name in CATALOG_CANONICAL.items():
        name_words = {w for w in name_canon.split() if w not in _FILLER_WORDS}
        overlap = len(query_words & name_words) / max(len(query_words | name_words), 1)
        similarity = SequenceMatcher(None, canon, name_canon).ratio()
        scored.append((max(overlap, similarity * 0.9), item_name))
    scored.sort(reverse=True)
    suggestions = [name for score, name in scored[:3] if score >= 0.5]
    if scored and scored[0][0] >= 0.8:
        return _match_result(scored[0][1], "fuzzy", f"Closest catalog item to '{customer_phrase}'.", suggestions)
    return _match_result(None, "none", "No matching catalog item.", suggestions)


def check_stock_level(item_name: str, quantity_requested: int, as_of_date: str) -> Dict:
    """Check stock for one catalog item and say whether a restock is needed.

    Uses the stock level on as_of_date (YYYY-MM-DD). restock_quantity_to_order
    is the amount needed to cover the request AND keep stock at its minimum level.
    """
    try:
        as_of_date = _clean_date(as_of_date)
    except ValueError:
        return {"error": "as_of_date must look like YYYY-MM-DD"}
    if item_name not in CATALOG_PRICES:
        return {"error": f"'{item_name}' is not a catalog item name. Call match_catalog_item first."}

    current_stock = _stock_on_hand(item_name, as_of_date)
    min_level = _min_stock_level(item_name)
    shortfall = max(0, quantity_requested - current_stock)
    restock_quantity = max(0, quantity_requested + min_level - current_stock)
    return {
        "item_name": item_name,
        "current_stock": current_stock,
        "quantity_requested": quantity_requested,
        "shortfall": shortfall,
        "can_fulfil_from_stock": shortfall == 0,
        "min_stock_level": min_level,
        "restock_quantity_to_order": restock_quantity,
        "estimated_restock_cost": round(restock_quantity * CATALOG_PRICES[item_name] * SUPPLIER_COST_RATIO, 2),
    }


def list_inventory_snapshot(as_of_date: str) -> Dict:
    """List every item currently in stock on a date and flag the low-stock ones."""
    try:
        as_of_date = _clean_date(as_of_date)
    except ValueError:
        return {"error": "as_of_date must look like YYYY-MM-DD"}

    in_stock = {name: int(units) for name, units in get_all_inventory(as_of_date).items()}
    minimums = pd.read_sql("SELECT item_name, min_stock_level FROM inventory", db_engine)
    min_by_item = dict(zip(minimums["item_name"], minimums["min_stock_level"]))
    low_stock = [
        name for name, units in in_stock.items() if units < min_by_item.get(name, DEFAULT_MIN_STOCK)
    ]
    return {"as_of_date": as_of_date, "items_in_stock": in_stock, "low_stock_items": low_stock}


def check_supplier_delivery(order_date: str, quantity: int, deadline: str = "") -> Dict:
    """Estimate when a supplier restock of `quantity` units ordered on order_date arrives.

    If the customer gave a deadline (YYYY-MM-DD), also say whether it can be met.
    """
    try:
        order_date = _clean_date(order_date)
        deadline_date = _clean_date(deadline) if deadline else ""
    except ValueError:
        return {"error": "Dates must look like YYYY-MM-DD"}

    delivery_date = get_supplier_delivery_date(order_date, quantity)
    result = {"order_date": order_date, "quantity": quantity, "delivery_date": delivery_date}
    result["meets_deadline"] = (delivery_date <= deadline_date) if deadline_date else None
    return result


def check_cash_available(estimated_cost: float, as_of_date: str) -> Dict:
    """Check whether the company can afford a purchase while keeping its cash reserve."""
    try:
        as_of_date = _clean_date(as_of_date)
    except ValueError:
        return {"error": "as_of_date must look like YYYY-MM-DD"}

    cash = get_cash_balance(as_of_date)
    spendable = max(0.0, cash - CASH_RESERVE)
    return {
        "cash_balance": round(cash, 2),
        "spendable_after_reserve": round(spendable, 2),
        "estimated_cost": round(estimated_cost, 2),
        "can_afford": estimated_cost <= spendable,
    }


def place_restock_order(item_name: str, quantity: int, order_date: str) -> Dict:
    """Buy `quantity` units of a catalog item from the supplier and record the purchase.

    Refuses if the item is unknown or the purchase would break the cash reserve.
    """
    try:
        order_date = _clean_date(order_date)
    except ValueError:
        return {"error": "order_date must look like YYYY-MM-DD"}
    if item_name not in CATALOG_PRICES:
        return {"error": f"'{item_name}' is not a catalog item name."}
    if quantity <= 0:
        return {"error": "quantity must be greater than zero."}

    cost = round(quantity * CATALOG_PRICES[item_name] * SUPPLIER_COST_RATIO, 2)
    if not check_cash_available(cost, order_date)["can_afford"]:
        return {"status": "refused", "reason": "Not enough spendable cash for this restock."}

    transaction_id = create_transaction(item_name, "stock_orders", quantity, cost, order_date)
    return {
        "status": "ordered",
        "transaction_id": transaction_id,
        "item_name": item_name,
        "quantity": quantity,
        "cost": cost,
        "expected_delivery_date": get_supplier_delivery_date(order_date, quantity),
    }


# ---------------------------------------------------------------------------
# TOOLS FOR THE QUOTING AGENT
# ---------------------------------------------------------------------------
def find_similar_quotes(keywords: List[str], max_results: int = 3) -> List[Dict]:
    """Find past quotes related to the customer's request, for pricing and wording style.

    Pass short keywords such as the event type or a product name. Each keyword is
    searched separately because the starter search needs ALL terms to match.
    """
    found, seen = [], set()
    for keyword in keywords:
        if not keyword.strip():
            continue
        for quote in search_quote_history([keyword.strip()], limit=max_results):
            key = (quote["total_amount"], quote["quote_explanation"][:60])
            if key in seen:
                continue
            seen.add(key)
            found.append(
                {
                    "total_amount": quote["total_amount"],
                    "order_size": quote["order_size"],
                    "event_type": quote["event_type"],
                    "quote_explanation": quote["quote_explanation"][:300],
                }
            )
    return found[:max_results]


def lookup_unit_price(item_name: str) -> Dict:
    """Return the catalog price per unit (per sheet, per piece or per roll)."""
    if item_name not in CATALOG_PRICES:
        return {"error": f"'{item_name}' is not a catalog item name."}
    return {"item_name": item_name, "unit_price": CATALOG_PRICES[item_name]}


def calculate_bulk_discount(order_lines: List[OrderLine]) -> Dict:
    """Price an order at catalog prices and apply the bulk discount for its size.

    Always use this tool for the arithmetic instead of calculating by hand.
    Discount is 5% from 100 units, 8% from 500 units, 12% from 1000 units.
    """
    priced_lines, unknown_items, subtotal, total_units = [], [], 0.0, 0
    for line in order_lines:
        if line.item_name not in CATALOG_PRICES:
            unknown_items.append(line.item_name)
            continue
        line_total = round(line.quantity * CATALOG_PRICES[line.item_name], 2)
        priced_lines.append(
            {
                "item_name": line.item_name,
                "quantity": line.quantity,
                "unit_price": CATALOG_PRICES[line.item_name],
                "line_total": line_total,
            }
        )
        subtotal += line_total
        total_units += line.quantity

    discount_rate = next((rate for minimum, rate in DISCOUNT_TIERS if total_units >= minimum), 0.0)
    discount_amount = round(subtotal * discount_rate, 2)
    return {
        "lines": priced_lines,
        "unknown_items": unknown_items,
        "total_units": total_units,
        "subtotal": round(subtotal, 2),
        "discount_percent": int(discount_rate * 100),
        "discount_amount": discount_amount,
        "total_price": round(subtotal - discount_amount, 2),
    }


# ---------------------------------------------------------------------------
# TOOLS FOR THE SALES AGENT
# ---------------------------------------------------------------------------
def run_financial_health_check(as_of_date: str) -> Dict:
    """Summarise cash, inventory value and top sellers (internal use, before large orders)."""
    try:
        as_of_date = _clean_date(as_of_date)
    except ValueError:
        return {"error": "as_of_date must look like YYYY-MM-DD"}

    report = generate_financial_report(as_of_date)
    # The starter books the opening cash as a "sale" with no item name; skip it
    # so only real products appear in the top sellers.
    top_sellers = [
        {
            "item_name": row["item_name"],
            "total_units": int(row["total_units"]),
            "total_revenue": round(float(row["total_revenue"]), 2),
        }
        for row in report["top_selling_products"]
        if row["item_name"] and pd.notna(row["total_units"])
    ][:3]
    return {
        "as_of_date": as_of_date,
        "cash_balance": round(float(report["cash_balance"]), 2),
        "inventory_value": round(float(report["inventory_value"]), 2),
        "total_assets": round(float(report["total_assets"]), 2),
        "top_selling_products": top_sellers,
    }


def record_sale(item_name: str, quantity: int, total_price: float, sale_date: str) -> Dict:
    """Record one sale line in the ledger (cash goes up, stock goes down).

    Safety check: refuses if the item is unknown or stock on sale_date is too low.
    """
    try:
        sale_date = _clean_date(sale_date)
    except ValueError:
        return {"error": "sale_date must look like YYYY-MM-DD"}
    if item_name not in CATALOG_PRICES:
        return {"error": f"'{item_name}' is not a catalog item name."}
    if quantity <= 0 or total_price <= 0:
        return {"error": "quantity and total_price must be greater than zero."}
    if _stock_on_hand(item_name, sale_date) < quantity:
        return {"status": "refused", "reason": f"Not enough stock of {item_name} to complete this sale."}

    transaction_id = create_transaction(item_name, "sales", quantity, round(total_price, 2), sale_date)
    return {"status": "recorded", "transaction_id": transaction_id, "item_name": item_name,
            "quantity": quantity, "total_price": round(total_price, 2)}


# Tool lists handed to each agent (agents are defined in the next section).
INVENTORY_TOOLS = [
    match_catalog_item, check_stock_level, list_inventory_snapshot,
    check_supplier_delivery, check_cash_available, place_restock_order,
]
QUOTING_TOOLS = [find_similar_quotes, lookup_unit_price, calculate_bulk_discount]
SALES_TOOLS = [run_financial_health_check, record_sale]


# ---------------------------------------------------------------------------
# AGENTS AND ORCHESTRATOR
# ---------------------------------------------------------------------------
from pydantic_ai import Agent
from typing import Any, List, Dict
import json


# ---------------------------------------------------------------------------
# 1. INVENTORY AGENT
# ---------------------------------------------------------------------------
inventory_agent = Agent(
    model=build_model(),
    tools=INVENTORY_TOOLS,
    system_prompt=(
        "You are the Inventory Agent for Munder Difflin Paper Company.\n"
        "Your job: ensure every requested item is in stock by the customer's deadline.\n\n"
        "RULES:\n"
        "1. ALWAYS call match_catalog_item FIRST for each product the customer mentions.\n"
        "   If matched=false, the item is NOT sold by us – report it as unavailable.\n"
        "2. For each matched item, call check_stock_level with the requested quantity and the request date.\n"
        "3. If shortfall > 0:\n"
        "   a) Call check_supplier_delivery(order_date=request_date, quantity=restock_quantity_to_order, deadline=customer_deadline).\n"
        "   b) If meets_deadline is false, report the deadline cannot be met.\n"
        "   c) Call check_cash_available(estimated_restock_cost, request_date). If can_afford=false, report insufficient cash.\n"
        "   d) If both checks pass, call place_restock_order(item_name, restock_quantity_to_order, request_date).\n"
        "4. The company keeps a $5,000 cash reserve – never breach it.\n"
        "5. Supplier cost is 70 % of catalog price; lead time: ≤10=0d, ≤100=1d, ≤1000=4d, >1000=7d.\n"
        "6. Return a concise summary: items in stock, items restocked (with delivery dates), items unavailable, any deadline/cash issues."
    ),
)


# ---------------------------------------------------------------------------
# 2. QUOTING AGENT
# ---------------------------------------------------------------------------
quoting_agent = Agent(
    model=build_model(),
    tools=QUOTING_TOOLS,
    system_prompt=(
        "You are the Quoting Agent for Munder Difflin Paper Company.\n"
        "Your job: produce a professional, transparent quote with correct pricing and bulk discounts.\n\n"
        "RULES:\n"
        "1. Input: list of OrderLine objects (item_name, quantity). Quantities may be in reams – convert using 500 sheets/ream.\n"
        "2. Call calculate_bulk_discount with the full list – it handles catalog prices, unknown items, and tiered discounts:\n"
        "   • ≥100 total units: 5 %\n"
        "   • ≥500 total units: 8 %\n"
        "   • ≥1000 total units: 12 %\n"
        "3. Optionally call find_similar_quotes with keywords (event type, product names) for context.\n"
        "4. Output a JSON object with:\n"
        "   {\n"
        "     \"lines\": [{\"item_name\", \"quantity\", \"unit_price\", \"line_total\"}, ...],\n"
        "     \"unknown_items\": [],\n"
        "     \"total_units\": int,\n"
        "     \"subtotal\": float,\n"
        "     \"discount_percent\": int,\n"
        "     \"discount_amount\": float,\n"
        "     \"total_price\": float,\n"
        "     \"quote_explanation\": \"string\"\n"
        "   }\n"
        "5. The quote_explanation MUST be customer-friendly and include:\n"
        "   - Item-by-item breakdown (quantity × unit price = line total)\n"
        "   - Bulk discount tier applied and amount saved\n"
        "   - Subtotal → discount → final total\n"
        "   - Estimated delivery timeline based on order quantities\n"
        "   - Any items that are unavailable or not in our catalog, noted politely\n"
        "   - Be customer-friendly, transparent, and professional\n"
        "Write as a professional business quote, not just raw numbers."
    ),
)


# ---------------------------------------------------------------------------
# 3. SALES AGENT
# ---------------------------------------------------------------------------
sales_agent = Agent(
    model=build_model(),
    tools=SALES_TOOLS,
    system_prompt=(
        "You are the Sales Agent for Munder Difflin Paper Company.\n"
        "Your job: finalize the sale – validate stock one last time, record the transaction, and confirm financial health.\n\n"
        "RULES:\n"
        "1. Input: the quote JSON from the Quoting Agent and the sale date.\n"
        "2. For each line with a known item, call record_sale(item_name, quantity, line_total, sale_date).\n"
        "   – record_sale will refuse if stock is insufficient.\n"
        "3. After all lines, call run_financial_health_check(sale_date) to report cash, inventory value, and top sellers.\n"
        "4. Return a summary: items sold, total revenue, updated cash balance, any refused lines."
    ),
)


# ---------------------------------------------------------------------------
# 4. TRIAGE / ORCHESTRATOR AGENT
# ---------------------------------------------------------------------------
class TriageResult(BaseModel):
    """Structured output from the Triage Agent."""
    request_date: str          # YYYY-MM-DD
    customer_deadline: str     # YYYY-MM-DD
    items: List[OrderLine]     # catalog item names + quantities (in sheets)
    event_type: str
    job_type: str
    order_size: str
    notes: str = ""


triage_agent = Agent(
    model=build_model(),
    tools=[],  # no external tools – pure LLM parsing
    output_type=TriageResult,
    system_prompt=(
        "You are the Triage Agent for Munder Difflin Paper Company.\n"
        "Parse the raw customer request and extract structured data.\n\n"
        "INPUT: A customer email/request string that includes a date like \"(Date of request: 2025-04-01)\".\n\n"
        "OUTPUT: A TriageResult with:\n"
        "  • request_date: the date in the parenthetical (YYYY-MM-DD)\n"
        "  • customer_deadline: the delivery deadline mentioned in the request (YYYY-MM-DD)\n"
        "  • items: list of {item_name, quantity} where quantity is in SHEETS/UNITS (not reams).\n"
        "    – Convert reams → sheets using 500 sheets/ream.\n"
        "    – Use the customer's wording for item_name; the Inventory Agent will canonicalize.\n"
        "  • event_type: the event (e.g., conference, party, festival)\n"
        "  • job_type: the customer's role (e.g., office manager, school teacher)\n"
        "  • order_size: small / medium / large (from context)\n"
        "  • notes: any special instructions\n\n"
        "IMPORTANT: If the customer says \"500 reams of A4 paper\", quantity = 500 * 500 = 250000.\n"
        "If they say \"500 sheets of A4 paper\", quantity = 500.\n"
        "Return ONLY the JSON object matching TriageResult."
    ),
)


# ---------------------------------------------------------------------------
# 5. MAIN ORCHESTRATOR FUNCTION
# ---------------------------------------------------------------------------
def process_customer_request(raw_request: str) -> Dict[str, Any]:
    """
    Full end-to-end pipeline for one customer request.
    Returns a JSON-serializable dict with triage, inventory, quote, and sales stages.
    Includes structured logging at every handoff, code-level catalog matching,
    ream-to-sheet conversion, pre-sale stock/cash guards, and cash-reserve enforcement.
    """
    log.info("=" * 70)
    log.info("NEW REQUEST RECEIVED")

    # --- Step 1: Triage ---
    log.info("[HANDOFF] Triage Agent: parsing raw request")
    try:
        triage_result = triage_agent.run_sync(raw_request).output
    except Exception as exc:
        log.exception("[Triage] Agent failed")
        return {
            "error": f"Triage failed: {type(exc).__name__}: {exc}",
            "stage": "triage",
            "raw_request": raw_request,
        }

    # --- Robust triage result guarding ---
    if triage_result is None:
        log.error("[Triage] Agent returned None output")
        return {
            "error": "Triage agent returned no output",
            "stage": "triage",
            "raw_request": raw_request,
        }

    try:
        request_date = triage_result.request_date
        deadline = triage_result.customer_deadline
        raw_items = triage_result.items or []
        event_type = triage_result.event_type
        job_type = triage_result.job_type
        order_size = triage_result.order_size
    except AttributeError as exc:
        log.exception("[Triage] Output missing expected fields")
        return {
            "error": f"Triage output missing fields: {exc}",
            "stage": "triage",
            "raw_request": raw_request,
        }

    log.info(
        "[Triage] parsed | date=%s deadline=%s event=%s job=%s size=%s items=%d",
        request_date, deadline, event_type, job_type, order_size, len(raw_items),
    )
    for line in raw_items:
        log.info("[Triage]   item=%s qty=%s", line.item_name, line.quantity)

    # --- Step 1b: Deduplicate, convert reams to sheets, match catalog ---
    log.info("[HANDOFF] Catalog matching & unit normalization")

    # 1. Deduplicate items by name (merge quantities)
    deduped_items = _deduplicate_items(raw_items)

    # 2. Convert reams -> sheets (code-level, not LLM-dependent)
    normalized_items = []
    for line in deduped_items:
        clean_name, sheet_qty = _convert_reams_to_sheets(line.item_name, line.quantity)
        normalized_items.append(OrderLine(item_name=clean_name, quantity=sheet_qty))

    # 3. Explicit catalog matching for every item
    available_items: List[OrderLine] = []
    unavailable_items: List[Dict[str, Any]] = []
    match_audit: List[Dict[str, Any]] = []

    for line in normalized_items:
        match = match_catalog_item(line.item_name)
        matched_name = match.get("item_name")

        audit_entry = {
            "requested_name": line.item_name,
            "match_method": match.get("match_method"),
            "resolved_to": matched_name,
            "unit_price": match.get("unit_price"),
            "note": match.get("note"),
            "suggestions": match.get("suggestions", []),
        }
        match_audit.append(audit_entry)

        if not match.get("matched") or matched_name is None:
            unavailable_items.append({
                "item_name": line.item_name,
                "quantity": line.quantity,
                "reason": match.get("note", "Not a catalog item."),
                "suggestions": match.get("suggestions", []),
            })
            continue

        available_items.append(OrderLine(item_name=matched_name, quantity=line.quantity))

    log.info("[Catalog] available=%d unavailable=%d", len(available_items), len(unavailable_items))

    # --- Step 2: Pre-check stock + Inventory Agent restock (available items only) ---
    log.info("[HANDOFF] Inventory Agent: stock check & restock")

    # Code-level pre-check: identify items needing restock
    stock_checks: Dict[str, Dict] = {}
    restock_needed: List[Dict[str, Any]] = []

    for line in available_items:
        stock_info = check_stock_level(line.item_name, line.quantity, request_date)
        stock_checks[line.item_name] = stock_info

        if stock_info.get("error"):
            log.warning("[Stock] %s: %s", line.item_name, stock_info["error"])
            continue

        if stock_info.get("shortfall", 0) > 0:
            restock_needed.append({
                "item_name": line.item_name,
                "quantity_requested": line.quantity,
                "current_stock": stock_info.get("current_stock", 0),
                "shortfall": stock_info.get("shortfall", 0),
                "restock_quantity_to_order": stock_info.get("restock_quantity_to_order", 0),
                "estimated_restock_cost": stock_info.get("estimated_restock_cost", 0),
            })

    # Delegate restock decisions to the Inventory Agent
    inventory_lines_text = (
        "\n".join(
            f"  - {r['item_name']}: need {r['restock_quantity_to_order']} more "
            f"(have {r['current_stock']}, requested {r['quantity_requested']})"
            for r in restock_needed
        )
        if restock_needed else "  (all items in stock)"
    )

    inventory_prompt = (
        f"Customer request date: {request_date}\n"
        f"Delivery deadline: {deadline}\n"
        f"Items needing restock:\n{inventory_lines_text}\n"
        f"Event: {event_type}, Role: {job_type}, Size: {order_size}\n"
        "Check supplier delivery dates and cash availability. Place restock orders only if:\n"
        "  1. Delivery meets customer deadline\n"
        "  2. Cash reserve ($5,000) is not breached\n"
        "HARD STOP: Never place a restock that would push cash below the $5,000 reserve. "
        "If a restock is needed but cannot be afforded, report the shortfall explicitly."
    )

    try:
        inventory_report = inventory_agent.run_sync(inventory_prompt).output
    except Exception as exc:
        log.exception("[Inventory] Agent failed")
        inventory_report = {"_error": f"{type(exc).__name__}: {exc}"}

    log.info("[Inventory] report received | type=%s", type(inventory_report).__name__)

    # --- Step 3: Quote (available items only; unmatched items bypassed) ---
    log.info("[HANDOFF] Quoting Agent: price & discount calculation")

    quote_items = available_items
    quote_lines_text = (
        "\n".join(f"  - {line.item_name}: {line.quantity}" for line in quote_items)
        if quote_items else "  (none)"
    )

    quoting_prompt = (
        f"Generate a professional quote for the following order lines:\n{quote_lines_text}\n"
        f"Event type: {event_type}\n"
        "Requirements for the quote_explanation field:\n"
        "  • List each item with quantity, unit price, and line total\n"
        "  • State the total units and which bulk discount tier applies (>=100: 5%%, >=500: 8%%, >=1000: 12%%) \n"
        "  • Show subtotal, discount amount, and final total price\n"
        "  • Mention estimated delivery timeline based on order quantities\n"
        "  • Note any items that are unavailable or not in our catalog\n"
        "  • Be customer-friendly, transparent, and professional\n"
        "Return the complete quote as a JSON object."
    )
    try:
        quote_result = quoting_agent.run_sync(quoting_prompt).output
    except Exception as exc:
        log.exception("[Quoting] Agent failed")
        quote_result = {"_error": f"{type(exc).__name__}: {exc}"}

    if isinstance(quote_result, dict):
        quote_data = quote_result
    elif isinstance(quote_result, str):
        stripped = quote_result.strip()
        if not stripped:
            log.warning("[Quoting] Agent returned empty string; using empty quote")
            quote_data = {}
        else:
            try:
                quote_data = json.loads(stripped)
            except (json.JSONDecodeError, ValueError) as exc:
                log.warning("[Quoting] Agent returned non-JSON string: %s", exc)
                quote_data = {"raw_output": quote_result}
    else:
        quote_data = {"raw_output": str(quote_result)}

    total_price = quote_data.get("total_price", 0)
    discount_pct = quote_data.get("discount_percent", 0)
    log.info(
        "[Quote] generated | total_units=%s subtotal=$%.2f discount=%s%% total=$%.2f unknown=%s",
        quote_data.get("total_units"), quote_data.get("subtotal", 0),
        discount_pct, total_price, quote_data.get("unknown_items", []),
    )
    log.info("[Quote] explanation: %s", quote_data.get("quote_explanation", "")[:300])

    # --- Step 4: Pre-sale stock & cash guards, then Sales Agent ---
    log.info("[HANDOFF] Sales Agent: record sale & financial health")

    # Code-level pre-sale stock validation: block oversells before calling Sales Agent
    sales_lines: List[Dict[str, Any]] = []
    blocked_lines: List[Dict[str, Any]] = []

    for line in quote_items:
        stock_info = check_stock_level(line.item_name, line.quantity, request_date)
        if stock_info.get("error"):
            blocked_lines.append({
                "item_name": line.item_name,
                "quantity": line.quantity,
                "reason": stock_info["error"],
            })
            continue

        if not stock_info.get("can_fulfil_from_stock", False):
            blocked_lines.append({
                "item_name": line.item_name,
                "quantity": line.quantity,
                "current_stock": stock_info.get("current_stock", 0),
                "shortfall": stock_info.get("shortfall", 0),
                "reason": "Insufficient stock after restock attempt",
            })
            continue

        # Resolve line total from quote data
        line_total = 0.0
        for ql in quote_data.get("lines", []):
            if ql.get("item_name") == line.item_name:
                line_total = ql.get("line_total", 0)
                break

        sales_lines.append({
            "item_name": line.item_name,
            "quantity": line.quantity,
            "line_total": line_total,
        })

    if blocked_lines:
        log.warning("[Sales] %d lines blocked due to stock/cash issues", len(blocked_lines))

    sales_prompt = (
        f"Record the sale for the following validated order lines on {request_date}:\n"
        f"{json.dumps(sales_lines, indent=2)}\n"
        "Only record lines for catalog items that are in stock. "
        "Skip unknown items and report any refusals.\n"
        "After recording, run a financial health check and report cash balance, "
        "inventory value, and top sellers."
    )

    try:
        sales_report = sales_agent.run_sync(sales_prompt).output
    except Exception as exc:
        log.exception("[Sales] Agent failed")
        sales_report = {"_error": f"{type(exc).__name__}: {exc}"}

    log.info("[Sales] report received | type=%s", type(sales_report).__name__)

    # --- Compose final structured response ---
    return {
        "triage": (
            triage_result.model_dump()
            if hasattr(triage_result, "model_dump")
            else dict(triage_result)
        ),
        "inventory_report": inventory_report,
        "quote": quote_data,
        "sales_report": sales_report,
        "catalog_audit": {
            "available_items": [{"item_name": l.item_name, "quantity": l.quantity} for l in available_items],
            "unavailable_items": unavailable_items,
            "match_details": match_audit,
        },
        "stock_checks": stock_checks,
        "blocked_sales_lines": blocked_lines,
        "request_date": request_date,
        "stage": "complete",
    }


# ---------------------------------------------------------------------------
# UPDATED TEST RUNNER
# ---------------------------------------------------------------------------
def run_test_scenarios():

    print("Initializing Database...")
    init_database(db_engine)
    try:
        quote_requests_sample = pd.read_csv("quote_requests_sample.csv")
        quote_requests_sample["request_date"] = pd.to_datetime(
            quote_requests_sample["request_date"], format="%m/%d/%y", errors="coerce"
        )
        quote_requests_sample.dropna(subset=["request_date"], inplace=True)
        quote_requests_sample = quote_requests_sample.sort_values("request_date")
    except Exception as e:
        print(f"FATAL: Error loading test data: {e}")
        return

    # Get initial state
    initial_date = quote_requests_sample["request_date"].min().strftime("%Y-%m-%d")
    report = generate_financial_report(initial_date)
    current_cash = report["cash_balance"]
    current_inventory = report["inventory_value"]

    log.info(
        "[RUN] Starting test suite | initial_date=%s cash=$%.2f inventory=$%.2f",
        initial_date, current_cash, current_inventory,
    )

    results = []
    reserve_breaches = 0
    for idx, row in quote_requests_sample.iterrows():
        request_date = row["request_date"].strftime("%Y-%m-%d")

        print(f"\n=== Request {idx+1} ===")
        print(f"Context: {row['job']} organizing {row['event']}")
        print(f"Request Date: {request_date}")
        print(f"Cash Balance: ${current_cash:.2f}")
        print(f"Inventory Value: ${current_inventory:.2f}")

        # Process request
        request_with_date = f"{row['request']} (Date of request: {request_date})"

        # --- Process via multi-agent system ---
        response = process_customer_request(request_with_date)

        # Update state from actual ledger
        report = generate_financial_report(request_date)
        current_cash = report["cash_balance"]
        current_inventory = report["inventory_value"]

        # --- Financial audit: cash reserve check ---
        if current_cash < 5000.0:
            reserve_breaches += 1
            log.warning(
                "[AUDIT] CASH RESERVE BREACH after request %d | cash=$%.2f (below $5,000)",
                idx + 1, current_cash,
            )
        else:
            log.info(
                "[AUDIT] Request %d OK | cash=$%.2f (reserve intact) inventory=$%.2f",
                idx + 1, current_cash, current_inventory,
            )

        print(f"Response: {json.dumps(response, default=str)[:300]}...")
        print(f"Updated Cash: ${current_cash:.2f}")
        print(f"Updated Inventory: ${current_inventory:.2f}")

        results.append(
            {
                "request_id": idx + 1,
                "request_date": request_date,
                "cash_balance": current_cash,
                "inventory_value": current_inventory,
                "response": json.dumps(response, default=str),
            }
        )

        time.sleep(1)

    # Final report
    final_date = quote_requests_sample["request_date"].max().strftime("%Y-%m-%d")
    final_report = generate_financial_report(final_date)
    print("\n===== FINAL FINANCIAL REPORT =====")
    print(f"Final Cash: ${final_report['cash_balance']:.2f}")
    print(f"Final Inventory: ${final_report['inventory_value']:.2f}")
    print(f"Reserve breaches: {reserve_breaches}")

    log.info(
        "[RUN] Complete | final_cash=$%.2f final_inventory=$%.2f breaches=%d",
        final_report['cash_balance'], final_report['inventory_value'], reserve_breaches,
    )

    # Save results
    pd.DataFrame(results).to_csv("test_results.csv", index=False)
    return results


if __name__ == "__main__":
    results = run_test_scenarios()
