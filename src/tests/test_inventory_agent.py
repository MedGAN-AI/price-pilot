import sys
import os
from pathlib import Path
import pytest

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Now import using the correct path
from src.agents.InventoryAgent.agent import answer_inventory_question

from src.agents.InventoryAgent.connectors.sql_connector import (
    get_product_by_sku,
    search_product_by_name,
    get_inventory_by_product_id
)

# Mark these tests as requiring Supabase data. Make sure your Supabase instance is running and seeded.

def test_get_product_by_sku():
    # Existing SKU from our seed data:
    product = get_product_by_sku("SHOES-RED-001")
    assert product is not None
    assert product["sku"] == "SHOES-RED-001"
    assert "name" in product

def test_search_product_by_name():
    # Partial name search
    product = search_product_by_name("Red Running Shoes")
    assert product is not None
    assert product["sku"] == "SHOES-RED-001"
    assert "id" in product

def test_get_inventory_by_product_id():
    product = get_product_by_sku("SHOES-RED-001")
    product_id = product["id"]
    stock = get_inventory_by_product_id(product_id)
    assert isinstance(stock, int)
    assert stock >= 0

@pytest.mark.parametrize("question, expected_phrase", [
    ("How many SHOES-RED-001 do we have?", "There are"),
    ("Do you have Red Running Shoes available?", "There are"),
    ("Inventory for SHOES-BLU-002?", "There are"),
    ("Is TSHIRT-BLK-004 in stock?", "There are"),
])
def test_answer_inventory_question_exists(question, expected_phrase):
    # As long as product exists and is not 0 stock, answer should start with "There are"
    response = answer_inventory_question(question)
    assert expected_phrase in response

def test_answer_inventory_question_not_found():
    # Nonexistent SKU
    response = answer_inventory_question("How many SHOES-XYZ-999 do we have?")
    assert "could not find any product" in response.lower()

def test_inventory_agent():
    # Example test
    result = answer_inventory_question("How many SHOES-RED-001 do we have?")
    assert isinstance(result, str)
    assert "SHOES-RED-001" in result
