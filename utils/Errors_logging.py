import pandas as pd
import os
from datetime import datetime

def functions_error_log(function_name, error_message, log_name, symbol=None):
    error_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    error_data = {
        'Time': [error_time],
        'Function': [function_name],
        'Symbol': [symbol] if symbol else [""],  # Include symbol if provided
        'Error': [str(error_message)]
    }

    error_df = pd.DataFrame(error_data)

    # Ensure the directory exists
    error_log_dir = '.stocks_data_csv/errors_logs/'
    if not os.path.exists(error_log_dir):
        os.makedirs(error_log_dir)

    error_log_path = f'{error_log_dir}{log_name}'

    try:
        # If it exists, append the new error to the existing file
        with open(error_log_path, 'a') as f:
            error_df.to_csv(f, index=False, header=f.tell()==0)
    except FileNotFoundError:
        # If the file doesn't exist, we'll create a new one with the current error
        error_df.to_csv(error_log_path, index=False)


log_name_rundb = "Create_update_selection.csv"
log_name_weekly_signals = "Weekly_signals.csv"
log_name_monthly_signals = "Monthly_signals.csv"
log_name_emails = "Emails.csv"


def clear_csv_data(file_path):
    """
    Clears all data from a CSV file, leaving the headers intact.

    :param file_path: Path to the CSV file to be cleared.
    """
    try:
        # Read the CSV file, but only the headers
        df = pd.read_csv(file_path, nrows=0)

        # Write the empty DataFrame (headers only) back to the file
        df.to_csv(file_path, index=False)
        print(f"Data in {file_path} has been cleared, headers retained.")

    except Exception as e:
        print(f"An error occurred: {e}")


monthly_signals_log = '/home/ubuntu/Stock_screener/stocks_data_csv/errors_logs/Monthly_signals.csv'
weekly_signals_log = '/home/ubuntu/Stock_screener/stocks_data_csv/errors_logs/Weekly_signals.csv'
emails_log = '/home/ubuntu/Stock_screener/stocks_data_csv/errors_logs/Emails.csv'
db_log = '/home/ubuntu/Stock_screener/stocks_data_csv/errors_logs/db_update.csv'
portfolio = '/home/ubuntu/Stock_screener/stocks_data_csv/data_base/portfolio.csv'