#!/usr/bin/env python3
import Create_db
import Stock_selection
import pandas as pd
import Signals
import Errors_logging
import pandas as pd
import Sending_Email
import Signals
from datetime import datetime, timedelta, date

# Get the current date
current_date = datetime.now()

monthly_signals_log = '/home/ubuntu/Stock_screener/stocks_data_csv/errors_logs/Monthly_signals.csv'
weekly_signals_log = '/home/ubuntu/Stock_screener/stocks_data_csv/errors_logs/Weekly_signals.csv'
emails_log = '/home/ubuntu/Stock_screener/stocks_data_csv/errors_logs/Emails.csv'
db_log = '/home/ubuntu/Stock_screener/stocks_data_csv/errors_logs/db_update.csv'

stock_list_100_selection_df = pd.read_csv(
    '/home/ubuntu/Stock_screener/stocks_data_csv/data_base/final_100_selection.csv')
stock_list_manual_selection_df = pd.read_csv(
    '/home/ubuntu/Stock_screener/stocks_data_csv/data_base/manual_selection.csv')

symbols_100_selection = stock_list_100_selection_df['Symbol'].tolist()
symbols_manual_selection = stock_list_manual_selection_df['Symbol'].tolist()

symbols = list(set(symbols_100_selection + symbols_manual_selection))

# Check if today is Saturday
if current_date.weekday() == 5:  # 5 represents Saturday

    Errors_logging.clear_csv_data(weekly_signals_log)
    Errors_logging.clear_csv_data(emails_log)

    # Check if it's the first Saturday of the month
    if 1 <= current_date.day <= 7:
        Errors_logging.clear_csv_data(monthly_signals_log)
        Errors_logging.clear_csv_data(db_log)
        # First Saturday of the month tasks
        stock_list_path = "/home/ubuntu/Stock_screener/stocks_data_csv/data_base/stocks_data_base.csv"
        Create_db.update_databases(stock_list_path)
        csv_file_path = "/home/ubuntu/Stock_screener/stocks_data_csv/data_base/Data_Base.csv"
        Stock_selection.selection_by_fundamentals(csv_file_path, 100)

        # Additional tasks after update_databases and selection_by_fundamentals
        try:
            for symbol in symbols:  # Ensure 'symbols' is defined earlier in your code
                Signals.add_monthly_stock_data(symbol)
            error_log_path = '/home/ubuntu/Stock_screener/stocks_data_csv/errors_logs/Monthly_signals.csv'
            Sending_Email.job_done_email("Run Monthly signals", error_log_path)
        except Exception as e:
            error_log_path = '/home/ubuntu/Stock_screener/stocks_data_csv/errors_logs/Monthly_signals.csv'
            Sending_Email.db_error_email(e, "Run Monthly signals", error_log_path)

    # Regular Saturday tasks
    try:
        for symbol in symbols:  # Ensure 'symbols' is defined earlier in your code
            Signals.add_weekly_stock_data(symbol)
        Signals.update_portfolio_details()
        error_log_path = '/home/ubuntu/Stock_screener/stocks_data_csv/errors_logs/Weekly_signals.csv'
        Sending_Email.job_done_email("Run Weekly Signal", error_log_path)
    except Exception as e:
        error_log_path = '/home/ubuntu/Stock_screener/stocks_data_csv/errors_logs/Weekly_signals.csv'
        Sending_Email.db_error_email(e, "Run Weekly Signal", error_log_path)

    # Send portfolio and transaction log emails
    Sending_Email.portfolio_email()
    Sending_Email.transaction_log_email()




