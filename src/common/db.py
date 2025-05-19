import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv(override=True)

# Get the Supabase URL and key from the environment
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")


# Create the Supabase client
supabase: Client = create_client(url, key)

# Test connection by fetching data
def get_data():
    response = supabase.table("g").select("*").execute()  # Set a higher limit
    print(response.data)
    print(response)


get_data()

