import os
from supabase import create_client, Client
from dotenv import load_dotenv


load_dotenv()

url: str = os.getenv('sb_url')
key: str = os.getenv('sb_api_key')  # Replace with your Supabase API key
supabase: Client = create_client(url, key)

##Arguments options
# action = add; remove
# role = admin; invited
# watchlist = [1]

def assign_user_role(action: str, role: str, email: str, watchlist: list = None):

    # Check if the email exists in the users table
    user_data = supabase.table("users").select("User_id").eq("Email", email).execute()
    if len(user_data.data) == 0:
        return "User is not registered yet"

    # Get user ID
    user_id = user_data.data[0]['User_id']

    if action.lower() == 'add':
        # Update user role in the users table
        role_update_response = supabase.table("users") \
            .update({"Role": role.capitalize()}) \
            .eq("User_id", user_id) \
            .execute()


        if role.lower() == 'admin':
            # Fetch all stocks from stocks_selection_plan
            stocks_data = supabase.table("stocks_selection_plan").select("*").execute()
        elif role.lower() == 'invite':
            # Fetch stocks from stocks_selection_plan based on watchlist (plan_id)
            stocks_data = supabase.table("stocks_selection_plan").select("*").in_("Plan_id", watchlist).execute()

        # Prepare data for batch insert
        batch_data = [
            {"User_id": user_id, "Stock_id": stock['Stock_id'], "Symbol": stock['Symbol'], "Plan_id": stock['Plan_id']}
            for stock in stocks_data.data
        ]

        # Insert data into users_watchlist
        insert_response = supabase.table("users_watchlist").insert(batch_data).execute()

    elif action.lower() == 'remove':
        # Remove specific stocks from users_watchlist based on Plan_id 1 and 3
        remove_response = supabase.table("users_watchlist") \
            .delete() \
            .eq("User_id", user_id) \
            .in_("Plan_id", [1, 3]) \
            .execute()


        # Reset the user role to 'User' in the users table
        role_reset_response = supabase.table("users") \
            .update({"Role": "User"}) \
            .eq("User_id", user_id) \
            .execute()

    return "Operation completed successfully"

assign_user_role("add", "Admin", "ysamkawi@gmail.com")