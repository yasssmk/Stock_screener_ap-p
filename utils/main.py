#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import Create_db
import Stock_selection
import Errors_logging
import pandas as pd
import Sending_Email
import Signals
from datetime import datetime, timedelta, date
from flask import Flask, jsonify
import requests

def send_signals_to_node(signals):
    print("Sending signals:", signals)
    url = 'http://localhost:3000/receive-signals'  # URL of your Node.js server
    try:
        response = requests.post(url, json=signals)
        print("Response Status Code:", response.status_code)
        print("Response Text:", response.text)
        if response.status_code == 200:
            print("Signals sent successfully")
        else:
            print("Failed to send signals")
    except Exception as e:
        print(f"Error occurred: {e}")


# Get the current date
current_date = datetime.now()

load_dotenv()

url: str = os.getenv('sb_url')
key: str = os.getenv('sb_api_key')  # Replace with your Supabase API key
supabase: Client = create_client(url, key)

monthly_signals_log = 'errors_logs/Monthly_signals.csv'
weekly_signals_log = 'errors_logs/Weekly_signals.csv'
emails_log = 'errors_logs/Emails.csv'
db_log = 'errors_logs/db_update.csv'

signals_list = []

# Check if today is Saturday
if current_date.weekday() == 5:  # 5 represents Saturday

    Errors_logging.clear_csv_data(weekly_signals_log)
    Errors_logging.clear_csv_data(emails_log)

    symbols = Signals.signal_stock()
    print(symbols)

    # Check if it's the first Saturday of the month
    if 1 <= current_date.day <= 7:
        Errors_logging.clear_csv_data(monthly_signals_log)
        Errors_logging.clear_csv_data(db_log)
        # First Saturday of the month tasks
        Create_db.run_update_databases()


        # Additional tasks after update_databases and selection_by_fundamentals
        try:
            for symbol in symbols:  # Ensure 'symbols' is defined earlier in your code
                monthly_signal = Signals.add_monthly_stock_data(symbol)
                if monthly_signal:  # If there is no monthly signal but a weekly signal exists
                    signal_dict = {symbol: monthly_signal[0]}  # Use the first weekly signal
                    signals_list.append(signal_dict)
            error_log_path = 'errors_logs/Monthly_signals.csv'
            Sending_Email.job_done_email("Run Monthly signals", error_log_path)
        except Exception as e:
            error_log_path = 'errors_logs/Monthly_signals.csv'
            Sending_Email.db_error_email(e, "Run Monthly signals", error_log_path)

    # Regular Saturday tasks
    try:
        for symbol in symbols:  # Ensure 'symbols' is defined earlier in your code
            if not any(symbol in signal for signal in signals_list):
                weekly_signal = Signals.add_weekly_stock_data(symbol)
                if weekly_signal:  # If there is a weekly signal
                    signal_dict = {symbol: weekly_signal[0]}
                    signals_list.append(signal_dict)
        Signals.update_portfolio_details()
        error_log_path = 'errors_logs/Weekly_signals.csv'
        Sending_Email.job_done_email("Run Weekly Signal", error_log_path)
    except Exception as e:
        error_log_path = 'errors_logs/Weekly_signals.csv'
        Sending_Email.db_error_email(e, "Run Weekly Signal", error_log_path)


send_signals_to_node(signals_list)

