from woocommerce import API
from supabase import create_client
import os
from dotenv import load_dotenv
load_dotenv()

wc = API(
    url=os.getenv("WC_URL"),
    consumer_key=os.getenv("WC_KEY"),
    consumer_secret=os.getenv("WC_SECRET"),
    version="wc/v3"
)
supa = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def fetch_and_load_wc_orders():
    orders = wc.get("orders").json()
    supa.table("orders_raw").insert(orders).execute()

if __name__ == "__main__":
    fetch_and_load_wc_orders()