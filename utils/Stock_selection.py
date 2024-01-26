import pandas as pd
import math
import utils.Errors_logging
import utils.Sending_Email
import time
import os
from dotenv import load_dotenv
from supabase import create_client, Client

def measure_runtime(func):
    """
    A decorator to measure the runtime of a function.
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        runtime = end_time - start_time
        print(f"The function '{func.__name__}' took {runtime:.4f} seconds to complete.")
        return result
    return wrapper



load_dotenv()

url: str = os.getenv('sb_url')
key: str = os.getenv('sb_api_key')  # Replace with your Supabase API key
supabase: Client = create_client(url, key)


# @measure_runtime
def selection_by_fundamentals(num_companies_to_select):
    try:
        #Selection plan id
        selection_id = 1
        # Fetch data from 'stocks_ranking_data' and 'data_stocks' tables
        response_ranking = supabase.table('stocks_ranking_data').select('Stock_id','Score','Sector', 'Top 100').execute()
        response_fin = supabase.table('data_stocks').select('*').execute()


        df_ranking = pd.DataFrame(response_ranking.data)
        df_fin = pd.DataFrame(response_fin.data)

        # Join the tables on 'Stock_id'
        df = pd.merge(df_fin, df_ranking, on='Stock_id')


        # Filter the DataFrame based on the selection conditions
        selection_conditions = (
            (df['Debt to Equity'] >= 0) &
            (df['EPS average Growth'] > 0) &
            (df['EPS median Growth'] >= 0) &
            (df['ROE'] <= 150) &
            (df['Last Growth'] >= -0.5) &
            (df['Score'] >= 1)
        )

        # Filter the DataFrame based on the selection conditions
        filtered_df = df[selection_conditions]

        # Define sector weights
        sector_weights = {
            'Industrials': 0.12,
            'Health Care': 0.05,
            'Consumer Discretionary': 0.16,
            'Energy': 0.05,
            'Finance': 0.05,
            'Consumer Staples': 0.08,
            'Telecommunications': 0.08,
            'Technology': 0.17,
            'Basic Materials': 0.08,
            'Real Estate': 0.03,
            'Miscellaneous': 0.05,
            'Utilities': 0.08
        }
        # Calculate the number of companies to keep for each sector
        company_selection = {}
        selected_symbols = set()

        for sector, weight in sector_weights.items():
            num_companies = math.ceil(weight * num_companies_to_select)
            sector_df = filtered_df[filtered_df['Sector'] == sector]

            # Exclude already selected symbols from this sector
            sector_df = sector_df[~sector_df['Symbol'].isin(selected_symbols)]

            # Sort by 'Score' in descending order and select the top companies
            sector_df = sector_df.nlargest(num_companies, 'Score')

            # Update the selected_symbols set with the newly selected symbols
            selected_symbols.update(sector_df['Symbol'])

            company_selection[sector] = sector_df

        # Concatenate the selected companies for each sector
        final_selection = pd.concat(company_selection.values())

        # Check if the total number of selected companies is less than num_companies_to_select
        if final_selection.shape[0] < num_companies_to_select:
            # Calculate the number of additional companies needed
            additional_needed = num_companies_to_select - final_selection.shape[0]

            # Number of companies to be taken from 'Technology' and 'Consumer Discretionary'
            additional_from_technology = math.ceil(additional_needed * 0.6)
            additional_from_discretionary = math.ceil(additional_needed * 0.4)

            # Add additional companies from 'Technology' sector
            tech_companies = filtered_df[
                (filtered_df['Sector'] == 'Technology') &
                (~filtered_df['Symbol'].isin(selected_symbols))
            ][:additional_from_technology]

            # Add additional companies from 'Consumer Discretionary' sector
            discretionary_companies = filtered_df[
                (filtered_df['Sector'] == 'Consumer Discretionary') &
                (~filtered_df['Symbol'].isin(selected_symbols))
            ][:additional_from_discretionary]

            # Concatenate the additional selections
            additional_selection = pd.concat([tech_companies, discretionary_companies])

            # Add the additional selections to the final selection
            final_selection = pd.concat([final_selection, additional_selection])

        # Sort the final selection by 'Score' in descending order
        final_selection = final_selection.sort_values(by='Score', ascending=False)

        # Ensure the final selection contains at least num_companies_to_select companies
        if final_selection.shape[0] < num_companies_to_select:
            raise ValueError("Unable to select enough companies to meet the desired count.")

        # Trim the final selection to num_companies_to_select
        final_selection = final_selection.head(num_companies_to_select)

        # Update the 'TOP 100' column in Supabase for the selected stocks
        final_selection_dict = final_selection[['Stock_id', 'Symbol']].set_index('Stock_id').to_dict(orient='index')


        # remove entries that are no longer in the final selection
        current_selection = supabase.table('stocks_selection_plan') \
            .select('Stock_id', 'Plan_id') \
            .eq('Plan', 'Fundamentals') \
            .execute().data

        ids_to_remove = [item['Stock_id'] for item in current_selection if item['Stock_id'] not in final_selection_dict]

        if ids_to_remove:
            supabase.table('stocks_selection_plan') \
                .delete() \
                .in_('Stock_id', ids_to_remove) \
                .eq('Plan', 'Fundamentals') \
                .execute()

            supabase.table('stocks_ranking_data').update({'Top 100': False}).in_('Stock_id', ids_to_remove).execute()

        for stock_id, stock_info in final_selection_dict.items():
            # Execute update statement for each selected stock
            supabase.table('stocks_ranking_data').update({'Top 100': True}).eq('Stock_id', stock_id).execute()
            try:
                supabase.table('stocks_selection_plan') \
                    .upsert(
                    {'Plan_id': selection_id, 'Stock_id': stock_id, 'Symbol': stock_info['Symbol'], 'Plan': 'Fundamentals'}) \
                    .execute()
            except Exception as e:
                # Handle the exception (e.g., log it, send a notification, etc.)
                utils.Errors_logging.functions_error_log("update stocks selection db", e,
                                                         utils.Errors_logging.log_name_rundb)
                # You may choose to continue the loop or break based on your requirement
                continue

        # Send success email (if needed)
        error_log_path = 'errors_logs/update_db'
        # utils.Sending_Email.job_done_email("Selection by Fundamentals", error_log_path)

    except Exception as e:
        utils.Errors_logging.functions_error_log("selection_by_fundamentals", e, utils.Errors_logging.log_name_rundb)
        error_log_path = 'errors_logs/update_db'
        # utils.Sending_Email.db_error_email(e, "selection_by_fundamentals", error_log_path)


def add_manually_selection(symbol):
    """
    Add a stock's row to the final selection CSV by symbol.

    Args:
    final_selection_path (str): The file path to the final selection CSV.
    database_path (str): The file path to the database CSV where stocks are listed.
    symbol (str): The stock symbol to add to the final selection.

    Returns:
    str: Message indicating success or failure.
    """
    final_selection_path = 'stocks_data_csv/data_base/manual_selection.csv'
    database_path = 'stocks_data_csv/data_base/Data_Base.csv'

    # Load the final selection and database into DataFrames
    try:
        final_selection_df = pd.read_csv(final_selection_path)
        database_df = pd.read_csv(database_path)
    except Exception as e:
        return f"Error loading CSV files: {e}"

    # Check if the symbol already exists in the final selection
    if symbol in final_selection_df['Symbol'].values:
        return f"The symbol {symbol} already exists in the final selection."

    # Find the row with the given symbol in the database
    stock_row = database_df[database_df['Symbol'] == symbol]

    # Check if the symbol exists in the database
    if stock_row.empty:
        return f"The symbol {symbol} does not exist in the database."

    # Add the row to the final selection DataFrame
    final_selection_df = pd.concat([final_selection_df, stock_row], ignore_index=True)

    # Save the updated DataFrame to the final selection CSV file
    final_selection_df.to_csv(final_selection_path, index=False)

    return f"The symbol {symbol} has been added to the final selection."

# final_selection_path = 'App/BackEnd/stocks_data_csv/data_base/manual_selection.csv'
# database_path = './stocks_data_csv/data_base/Data_Base.csv'
# symbol_to_add = 'EXAS'  # Replace 'AAPL' with the symbol provided by the user
#
# # Call the function to add a stock to the final selection
# add_manually_selection(symbol_to_add)
