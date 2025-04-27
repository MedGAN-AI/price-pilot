import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Get the Supabase URL and key from the environment
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

# Create the Supabase client
supabase: Client = create_client(url, key)

# Test connection by fetching data
def get_data():
    # Fetch data from a table
    data = supabase.table("data").select("*").execute()
    return data.data  # Return the data from the response

print(get_data())


