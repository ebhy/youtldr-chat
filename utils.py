import os
from supabase import create_client, Client
from datetime import date

# Get from environment
SUPABASE_URL: str = os.environ.get("SUPABASE_URL")
SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def increment_column_today(table_name: str = "daily_summary", column_name: str = "chat_ct"):
    """Increments a column in a table for today's date."""
    today = date.today().strftime("%m-%d-%Y")
    data = supabase.table(table_name).select("*").eq("today", today).execute()
    if len(data.data) > 0:
        # Update the existing row
        updated_data = supabase.table(table_name).update({column_name: data.data[0][column_name] + 1}).eq("today", today).execute()
    else:
        # Create a new row
        updated_data = supabase.table(table_name).insert({"today": today}).execute()

    if len(updated_data.data) <= 0:
        print(f"Error incrementing column {column_name} for {today}")
