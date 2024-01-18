import pandas as pd
import csv
import numpy as np
import random
import yfinance as yf
from datetime import datetime, timedelta, date
import ta
import os
import utils.Stock_Data
import utils.Sending_Email
import utils.Errors_logging
# import matplotlib.pyplot as plt
import math

data_end_date = datetime.now()
five_years_ago = data_end_date - timedelta(days=365 * 5)
# data_start_date = two_years_ago.strftime('%Y-%m-%d')
data_start_date = '2015-01-05'


# Data
def get_data(symbol):
    try:
        # Download stock data
        start_date = datetime.strptime(data_start_date, '%Y-%m-%d')
        end_date = datetime.now()
        success = False
        stock_data = None

        while not success and start_date <= end_date:
            try:
                # Download stock data
                stock_data = yf.download(symbol, start=start_date.strftime('%Y-%m-%d'),
                                         end=end_date.strftime('%Y-%m-%d'),
                                         interval='1wk')

                if not stock_data.empty:
                    success = True
                else:
                    # Increment start date by one month
                    start_date += timedelta(days=30)
            except Exception as e:
                # print(f"Error encountered for date {start_date.strftime('%Y-%m-%d')}: {e}")
                # Increment start date by one month
                start_date += timedelta(days=30)

        if success:
            # Save the data to a CSV file
            csv_file_name = f"./stocks_data_csv/stock_data/{symbol}.csv"
            stock_data.to_csv(csv_file_name)
            return csv_file_name
        else:
            # print(f"No data available for {symbol} from {initial_start_date} to {end_date.strftime('%Y-%m-%d')}")
            return None
    except Exception as e:
        utils.Errors_logging.functions_error_log("get_data", e, utils.Errors_logging.log_name_weekly_signals,
                                           symbol=symbol)


def get_monthly_data(symbol):
    try:
        start_date = datetime.strptime(data_start_date, '%Y-%m-%d')
        end_date = datetime.now()
        success = False
        stock_data = None

        while not success and start_date <= end_date:
            try:
                # Download stock data
                stock_data = yf.download(symbol, start=start_date.strftime('%Y-%m-%d'),
                                         end=end_date.strftime('%Y-%m-%d'),
                                         interval='1mo')

                if not stock_data.empty:
                    success = True
                else:
                    # Increment start date by one month
                    start_date += timedelta(days=30)
            except Exception as e:
                # Increment start date by one month
                start_date += timedelta(days=30)

        if success:
            # Save the data to a CSV file
            csv_file_name = f"./stocks_data_csv/stock_data/{symbol}_monthly.csv"
            stock_data.to_csv(csv_file_name)
            return csv_file_name
        else:
            return None
    except Exception as e:
        utils.Errors_logging.functions_error_log("get_monthly_data", e, utils.Errors_logging.log_name_monthly_signals,
                                           symbol=symbol)


def load_data_from_csv(csv_file_name):
    # Load stock data from a CSV file
    stock_data = pd.read_csv(csv_file_name, index_col='Date', parse_dates=True)

    return stock_data


# Indicators

def calculate_macd(stock_data, slow, fast, signal):
    macd = ta.trend.MACD(stock_data['Close'], window_slow=slow, window_fast=fast, window_sign=signal)
    stock_data['MACD'] = macd.macd()
    stock_data['Signal'] = macd.macd_signal()
    try:
        stock_data['MACD_Histogram'] = macd.macd_diff()
    except KeyError as e:
        print(f"KeyError: {e}. The 'MACD_Histogram' column is not available in the data.")
    return stock_data


def calculate_moving_averages(stock_data):
    stock_data['MA12'] = stock_data['Close'].rolling(window=12).mean()
    stock_data['MA20'] = stock_data['Close'].rolling(window=20).mean()
    stock_data['MA50'] = stock_data['Close'].rolling(window=50).mean()
    stock_data['MA5'] = stock_data['Close'].rolling(window=5).mean()


# trends

def get_lt_trend(stock_data, date):
    try:
        # Ensure the date is in the correct format and the DataFrame index is a DatetimeIndex
        date = pd.to_datetime(date)
        stock_data.index = pd.to_datetime(stock_data.index)

        # Calculate MACD values if they haven't been already calculated
        calculate_macd(stock_data, 26, 12, 9)

        # Find the closest previous date in the DataFrame index
        closest_date_index = stock_data.index.get_indexer([date], method='ffill')[0]
        closest_date = stock_data.index[closest_date_index]

        # Get the data for the closest previous date and the previous date
        data_on_closest_date = stock_data.loc[closest_date]
        previous_data = stock_data.loc[:closest_date].iloc[-2]
        pre_previous_data = stock_data.loc[:closest_date].iloc[-3]

        # Determine the trend based on MACD and Signal values for the closest date
        if data_on_closest_date['MACD'] >= 0:
            if data_on_closest_date['MACD'] >= data_on_closest_date['Signal']:
                if data_on_closest_date['MACD'] >= previous_data['MACD']:
                    trend_type = 'Bullish'
                elif data_on_closest_date['MACD'] < previous_data['MACD']:
                    trend_type = 'Bullish breath'
            elif data_on_closest_date['MACD'] < data_on_closest_date['Signal']:
                trend_type = 'Bullish breath'

        elif data_on_closest_date['MACD'] < 0:
            if data_on_closest_date['MACD'] <= data_on_closest_date['Signal']:
                trend_type = 'Bearish'
            elif data_on_closest_date['MACD'] > data_on_closest_date['Signal']:
                trend_type = 'Bearish breath'

        return trend_type
    except Exception as e:
        utils.Errors_logging.functions_error_log("get_lt_trend", e, utils.Errors_logging.log_name_weekly_signals)


def get_macd_trend(stock_data, date):
    try:
        # Ensure the date is in the correct format and the DataFrame index is a DatetimeIndex
        date = pd.to_datetime(date)
        stock_data.index = pd.to_datetime(stock_data.index)

        # Calculate moving averages and MACD if they haven't been already calculated
        calculate_moving_averages(stock_data)
        calculate_macd(stock_data, 26, 3, 7)  # Corrected the parameters for standard MACD (12, 26, 9)

        # Find the closest previous date in the DataFrame index
        closest_date_index = stock_data.index.get_indexer([date], method='ffill')[0]
        closest_date = stock_data.index[closest_date_index]

        # Get the data for the closest previous date and the date before that
        data_on_closest_date = stock_data.loc[closest_date]
        # previous_data = stock_data.loc[:closest_date].iloc[-2]  # Second last row up to the closest date

        # Determine the trend based on MACD and Signal values for the closest date
        if data_on_closest_date['Signal'] > 0:
            if data_on_closest_date['MACD'] > data_on_closest_date['Signal']:
                trend_type = 'MACD Bullish'
            elif data_on_closest_date['MACD'] < data_on_closest_date['Signal']:
                trend_type = 'MACD Bullish breath'
            # If MACD equals the Signal line, we need to look at the previous data to determine the trend
            # elif data_on_closest_date['MACD'] == data_on_closest_date['Signal']:
            #     if previous_data['MACD'] > previous_data['Signal']:
            #         trend_type = 'MACD Bullish'
            #     else:
            # trend_type = 'MACD Bullish breath'

        elif data_on_closest_date['Signal'] < 0:
            if data_on_closest_date['MACD'] < data_on_closest_date['Signal']:
                trend_type = 'MACD Bearish'
            elif data_on_closest_date['MACD'] > data_on_closest_date['Signal']:
                trend_type = 'MACD Bearish breath'
            # If MACD equals the Signal line, determine the trend from the previous data
            # elif data_on_closest_date['MACD'] == data_on_closest_date['Signal']:
            #     if previous_data['MACD'] < previous_data['Signal']:
            #         trend_type = 'MACD Bearish'
            #     else:
            #         trend_type = 'MACD Bearish breath'
        else:
            trend_type = 'Neutral'

        return trend_type
    except Exception as e:
        utils.Errors_logging.functions_error_log("get_macd_trend", e, utils.Errors_logging.log_name_weekly_signals)


# Divergences

def spot_monthly_divergences(monthly_stock_data, file_data):
    current_lt_trend = file_data.iloc[-1]['LT Trend']
    current_macd_trend = file_data.iloc[-1]['MACD Trend']

    # Retrieve the last spotted divergence, if any
    last_divergence_spotted = file_data.iloc[-1]['Divergence spotted']
    previous_divergence_spotted = file_data.iloc[-2]['Divergence spotted']
    previous_lt_trend = file_data.iloc[-2]['LT Trend']

    # if last_divergence_spotted == None and current_lt_trend == previous_lt_trend:
    #   last_divergence_spotted = previous_divergence_spotted

    # Find the index where the current LT trend starts
    indexes = []
    nmbr = 0
    skip = 0

    for index, row in file_data.iloc[::-1].iterrows():
        # print(f'{row["Start Date"]}: {row["Highest Price"]}')
        if row['MACD Trend'] == current_macd_trend:
            nmbr += 1
            if nmbr <= 2 and skip >= 1:
                # print(f'{file_data.iloc[-1]["Start Date"]}')
                # print(f'{current_macd_trend} - {row["Start Date"]}: nmbr={nmbr} ou skip={skip}')
                indexes.append(index)
        else:
            skip += 1
            continue

    indexes.reverse()
    same_macd_trend_data = file_data.loc[indexes]
    # print(f'{file_data.iloc[-1]["Start Date"]}: {same_macd_trend_data}')

    # Retrieve the current high/low prices and MACD values
    current_highest_price = file_data.iloc[-1]['Highest Price']
    current_lowest_price = file_data.iloc[-1]['Lowest Price']
    current_highest_macd = file_data.iloc[-1]['Highest MACD']
    current_lowest_macd = file_data.iloc[-1]['Lowest MACD']

    # Check for divergences by comparing the current price and MACD with the past instances
    if len(same_macd_trend_data) >= 1:  # We need at least two instances: one current, one past
        for i in range(len(same_macd_trend_data) - 1, -1, -1):
            row = same_macd_trend_data.iloc[i]
            if current_macd_trend == 'MACD Bullish':
                # Bearish Divergence: Current price is higher but MACD is lower than previous
                if current_highest_price > row['Highest Price'] and current_highest_macd < row['Highest MACD']:
                    return 'Sell - Monthly Divergence'
            elif current_macd_trend == 'MACD Bearish':
                # Bullish Divergence: Current price is lower but MACD is higher than previous
                if current_lowest_price < row['Lowest Price'] and current_lowest_macd > row['Lowest MACD']:
                    # print(f'{row["Start Date"]}: {current_lowest_price}')
                    return 'Buy - Monthly Divergence'

    # If no divergences are found or not enough data
    return last_divergence_spotted


def spot_weekly_divergences(stock_data, monthly_stock_data, file_data, date):
    current_lt_trend = file_data.iloc[-1]['LT Trend']
    current_macd_trend = file_data.iloc[-1]['MACD Trend']

    # Retrieve the last spotted divergence, if any
    last_divergence_spotted = file_data.iloc[-1]['Divergence spotted']
    previous_divergence_spotted = file_data.iloc[-2]['Divergence spotted']
    previous_lt_trend = file_data.iloc[-2]['LT Trend']
    # print(f'1: last div row = data:{file_data.iloc[-1]["Start Date"]} Divergence: {last_divergence_spotted} previous div: {previous_divergence_spotted}')

    if previous_divergence_spotted == 'Weekly Bearish Divergence' or previous_divergence_spotted == 'Weekly Bullish Divergence':
        if last_divergence_spotted == None:
            last_divergence_spotted = previous_divergence_spotted

    if previous_divergence_spotted == 'Weekly Bullish Divergence' and current_lt_trend == 'Bearish':
        last_divergence_spotted = None

    # indexes = []
    # for index, row in file_data.iloc[::-1].iterrows():
    #   if row['LT Trend'] == current_lt_trend:
    #     indexes.append(index)
    #   else:
    #     break

    # indexes.reverse()
    # filtered_file_data = file_data.loc[indexes]
    # same_macd_trend_data = filtered_file_data[filtered_file_data['MACD Trend'] == current_macd_trend]

    # Get current trend highest and lowest data
    start_date_of_current_trend = None
    for index, row in file_data.iloc[::-1].iterrows():
        if row['LT Trend'] != current_lt_trend:
            start_date_of_current_trend = row['End Date']
            # print(f'{current_lt_trend}: {start_date_of_current_trend} - {date}')
            break

    previous_highest_price = round(stock_data['High'][start_date_of_current_trend:date].max(), 2)
    previous_lowest_price = round(stock_data['Low'][start_date_of_current_trend:date].min(), 2)
    previous_highest_macd = round(stock_data['MACD'][start_date_of_current_trend:date].max(), 2)
    previous_lowest_macd = round(stock_data['MACD'][start_date_of_current_trend:date].min(), 2)

    # print(f'Price: {previous_lowest_price} MACD: {previous_lowest_macd}')

    # Retrieve the current high/low prices and MACD values
    current_highest_price = file_data.iloc[-1]['Highest Price']
    current_lowest_price = file_data.iloc[-1]['Lowest Price']
    current_highest_macd = file_data.iloc[-1]['Highest MACD']
    current_lowest_macd = file_data.iloc[-1]['Lowest MACD']
    # print(f'Price: {current_highest_price} MACD: {current_highest_macd}')

    if current_macd_trend == 'MACD Bullish':
        if current_highest_price >= previous_highest_price and current_highest_macd <= previous_highest_macd:
            return 'Weekly Bearish Divergence'
    elif current_macd_trend == 'MACD Bearish':
        # print(f'{start_date_of_current_trend} - {date}: current low: {current_lowest_price}  previous low {previous_lowest_price}')
        if current_lowest_price <= previous_lowest_price and current_lowest_macd >= previous_lowest_macd:
            return 'Weekly Bullish Divergence'

    # Check for divergences by comparing the current price and MACD with the past instances
    # if len(same_macd_trend_data) > 1:  # We need at least two instances: one current, one past
    #     for i in range(len(same_macd_trend_data) - 2, -1, -1):  # Start from the second last and go backwards
    #         row = same_macd_trend_data.iloc[i]
    #         if current_macd_trend == 'MACD Bullish':
    #             # Bearish Divergence: Current price is higher but MACD is lower than previous
    #             if current_highest_price > row['Highest Price'] and current_highest_macd < row['Highest MACD']:
    #                 return 'Weekly Bearish Divergence'
    #         elif current_macd_trend == 'MACD Bearish':
    #             # Bullish Divergence: Current price is lower but MACD is higher than previous
    #             if current_lowest_price < row['Lowest Price'] and current_lowest_macd > row['Lowest MACD']:
    #                 return 'Weekly Bullish Divergence'

    # If no divergences are found or not enough data
    # print(f'2: {last_divergence_spotted} ')
    return last_divergence_spotted


def divergences_signal(current_lt_trend, file_data, date):
    divergence_spotted = file_data.iloc[-1]['Divergence spotted']
    previous_lt_trend = file_data.iloc[-1]['LT Trend']
    current_lt_trend = current_lt_trend

    if previous_lt_trend == 'Bullish breath' and current_lt_trend == 'Bullish' and divergence_spotted == 'Weekly Bullish Divergence':
        return 'Buy - divergence'
    elif current_lt_trend != 'Bearish' and previous_lt_trend == 'Bearish' and divergence_spotted == 'Weekly Bullish Divergence':
        return 'Buy - divergence'
    elif previous_lt_trend == 'Bullish' and current_lt_trend == 'Bullish breath' and divergence_spotted == 'Weekly Bearish Divergence':
        # print(f'{date}: Sell - Weekly Bearish divergence')
        return 'Sell - divergence'
    elif current_lt_trend == 'Bearish' and divergence_spotted == 'Weekly Bullish Divergence':
        return 'Weekly Bullish Divergence'
    else:
        return None


# signals

def spot_weekly_signals(file_data, date, lt_trend, stock_data_weekly, stock_data_monthly):
    lt_trend = lt_trend
    current_signal = file_data.iloc[-1]['Signal']
    # print(f'{date}: current signal : {current_signal}')
    previous_signal = file_data.iloc[-2]['Signal']
    preprevious_signal = file_data.iloc[-3]['Signal']
    # print(f'{date}: previous signal : {previous_signal} and preprevious_signal ={preprevious_signal} ')

    # print(f'{date}: lt trend : {lt_trend}')
    current_divergence = file_data.iloc[-1]['Divergence spotted']
    previous_divergence = file_data.iloc[-2]['Divergence spotted']

    # Indicators
    bb_low_serie = utils.Stock_Data.bb_low_indicator(stock_data_weekly)
    bb_low = bb_low_serie[date]
    bb_high_serie = utils.Stock_Data.bb_high_indicator(stock_data_weekly)
    bb_high = bb_high_serie[date]
    previous_bb_high = bb_high_serie.shift(1).loc[date]

    calculate_moving_averages(stock_data_weekly)
    calculate_macd(stock_data_weekly, 26, 3, 7)

    # Buying signals weekly
    curent_data = stock_data_weekly.loc[date]
    previous_data = stock_data_weekly.shift(1).loc[date]

    if previous_signal == 'Sell signal' or previous_signal == 'Buy signal':
        current_signal == None

    # bearish_div = is_there_divergence(file_data)

    if lt_trend == 'Bullish':
        if curent_data['MA12'] > curent_data['MA20']:
            if curent_data['MA5'] >= curent_data['MA12'] and previous_data['MA5'] <= previous_data['MA12']:
                # print(f'{date} - Buy signal : Pull Back')
                return f'Buy signal'

    if current_signal == None:
        if lt_trend == 'Bullish' or lt_trend == 'Bullish breath':

            if bb_low == 1:
                return 'Waiting for confirmation : Buy'

            if curent_data['Low'] < curent_data['MA50']:
                return 'Waiting for confirmation : Buy'

    # Invalidation
    if current_divergence != None:
        if 'Sell' in current_divergence:
            return None

    if current_signal == 'Waiting for confirmation : Buy' or previous_signal == 'Waiting for confirmation : Buy':
        # print(f"1. {date}")
        if lt_trend == 'Bearish':
            # print('1.1')
            return None

        elif lt_trend == 'Bullish':
            # print(f"1.2: {date} :{curent_data['MACD']} and signal: {curent_data['Signal']}")
            if curent_data['MACD'] > curent_data['Signal']:
                # print('1.3')
                if curent_data['MA12'] > curent_data['MA50']:
                    return 'Buy signal'

            elif curent_data['MACD'] > curent_data['Signal']:
                # print('1.4')
                if previous_data['MA12'] <= previous_data['MA50']:
                    return 'Buy signal'
        else:
            if previous_signal == 'Sell signal' or previous_signal == 'Buy signal':
                current_signal = None
            else:
                current_signal = previous_signal

    if previous_signal == 'Sell signal':
        if file_data.iloc[-3]['Signal'] == 'Waiting for confirmation : Buy':
            current_signal = 'Waiting for confirmation : Buy'
        elif file_data.iloc[-3]['Signal'] == 'Sell signal' and file_data.iloc[-4][
            'Signal'] == 'Waiting for confirmation : Buy':
            current_signal = 'Waiting for confirmation : Buy'
        else:
            current_signal = None

    # sell signals

    if lt_trend != 'Bullish':
        if bb_high == 1 or previous_bb_high == 1:
            return 'Sell signal'

    return current_signal


def spot_monthly_signals(file_data, date, lt_trend, stock_data_monthly):
    lt_trend = lt_trend
    current_signal = file_data.iloc[-1]['Signal']
    previous_signal = file_data.iloc[-2]['Signal']
    previous_lt_trend = file_data.iloc[-2]['LT Trend']

    # Indicators
    bb_low_serie = utils.Stock_Data.bb_low_indicator(stock_data_monthly)
    bb_low = bb_low_serie[date]

    if bb_low == 1:
        return 'Waiting for confirmation : Buy'

    if current_signal == 'Waiting for confirmation : Buy':
        if lt_trend == 'Bullish':
            return 'Buy signal'

        elif lt_trend == 'Bearish' and previous_lt_trend == 'Bearish':
            return None


# def update_portfolio(symbol, action, date):
#     try:
#         portfolio_file = './stocks_data_csv/data_base/portfolio.csv'
#         transaction_log = './stocks_data_csv/data_base/transactions_logs.csv'
#         # Check if the portfolio file exists and has content
#         try:
#             portfolio_df = pd.read_csv(portfolio_file)
#             portfolio_df = portfolio_df.dropna(how='all')
#             portfolio_df.to_csv('./stocks_data_csv/data_base/portfolio.csv', index=False)
#         except (FileNotFoundError, pd.errors.EmptyDataError):
#             # If the file does not exist or is empty, create a new DataFrame
#             portfolio_df = pd.DataFrame(columns=['Symbol', 'Buying date', 'Buying price'])
#         try:
#             transaction_df = pd.read_csv(transaction_log)
#         except FileNotFoundError:
#             transaction_df = pd.DataFrame(
#                 columns=['Symbol', 'Buying date', 'Buying Price', 'Selling Date', 'Selling Price', 'Profit', 'Yield'])
#         if action == 'Buy':
#             # Get the current stock price
#             price = Stock_Data.get_stock_price(symbol, date)
#             # Create a new row with the purchase information
#             new_row = pd.DataFrame({'Symbol': [symbol], 'Buying date': [date], 'Buying price': [price]})
#             # Append the new row to the DataFrame
#             portfolio_df = pd.concat([portfolio_df, new_row], ignore_index=True)
#
#         elif action == 'Sell':
#             for index, row in portfolio_df[portfolio_df['Symbol'] == symbol].iterrows():
#                 buying_price = float(row['Buying price'].replace('$', ''))
#                 selling_price_str = Stock_Data.get_stock_price(symbol, date)
#                 selling_price = float(selling_price_str.replace('$', ''))
#                 profit = selling_price - buying_price
#                 yield_ = profit / buying_price
#
#                 transaction = {
#                     'Symbol': symbol,
#                     'Buying date': row['Buying date'],
#                     'Buying Price': row['Buying price'],
#                     'Selling Date': date,
#                     'Selling Price': f'${selling_price:.2f}',
#                     'Profit': f'${profit:.2f}',
#                     'Yield': f'{yield_ * 100:.2f}%'
#                 }
#                 transaction_df = pd.concat([transaction_df, pd.DataFrame([transaction])], ignore_index=True)
#
#             # Save the updated data
#             portfolio_df.to_csv(portfolio_file, index=False)
#             transaction_df.to_csv(transaction_log, index=False)
#             # Remove the sold stock from the DataFrame
#             portfolio_df = portfolio_df[portfolio_df['Symbol'] != symbol]
#
#         # Write the updated DataFrame back to the CSV file
#         portfolio_df.to_csv(portfolio_file, index=False)
#     except Exception as e:
#         #print(e)
#         Errors_logging.functions_error_log("update_portfolio", e, Errors_logging.log_name_weekly_signals, symbol=symbol)


def update_portfolio(symbol, action, date):
    try:
        portfolio_file = './stocks_data_csv/data_base/portfolio.csv'
        transaction_log = './stocks_data_csv/data_base/transactions_logs.csv'

        # Ensure the directories exist
        os.makedirs(os.path.dirname(portfolio_file), exist_ok=True)
        os.makedirs(os.path.dirname(transaction_log), exist_ok=True)

        # Read or initialize the portfolio DataFrame
        if os.path.isfile(portfolio_file):
            portfolio_df = pd.read_csv(portfolio_file)
            # portfolio_df = portfolio_df.dropna(how='all')
            # portfolio_df.to_csv('./stocks_data_csv/data_base/portfolio.csv', index=False)
        else:
            portfolio_df = pd.DataFrame(columns=['Symbol', 'Buying date', 'Buying Price'])

        # Read or initialize the transaction DataFrame
        if os.path.isfile(transaction_log):
            transaction_df = pd.read_csv(transaction_log)
            # transaction_df = portfolio_df.dropna(how='all')
            # transaction_df.to_csv('./stocks_data_csv/data_base/transactions_logs.csv', index=False)
        else:
            transaction_df = pd.DataFrame(
                columns=['Symbol', 'Buying date', 'Buying Price', 'Selling Date', 'Selling Price', 'Profit', 'Yield'])

        # Get the current stock price
        price = utils.Stock_Data.get_stock_price(symbol)

        if action == 'Buy':
            if not ((portfolio_df['Symbol'] == symbol) & (portfolio_df['Buying date'] == date)).any():
                new_row = {'Symbol': [symbol], 'Buying date': [date], 'Buying Price': [price]}
                portfolio_df = pd.concat([portfolio_df, pd.DataFrame(new_row)], ignore_index=True)
        elif action == 'Sell':
            # Perform selling operations...
            for index, row in portfolio_df.loc[portfolio_df['Symbol'] == symbol].iterrows():
                buying_price = float(row['Buying Price'].replace('$', ''))
                selling_price_str = utils.Stock_Data.get_stock_price(symbol)
                selling_price = float(selling_price_str.replace('$', ''))
                profit = selling_price - buying_price
                yield_ = profit / buying_price

                transaction = {
                    'Symbol': symbol,
                    'Buying date': row['Buying date'],
                    'Buying Price': row['Buying Price'],
                    'Selling Date': date,
                    'Selling Price': f'${selling_price:.2f}',
                    'Profit': f'${profit:.2f}',
                    'Yield': f'{yield_ * 100:.2f}%'
                }
                transaction_df = pd.concat([transaction_df, pd.DataFrame([transaction])], ignore_index=True)

            # Remove the sold stock from the DataFrame
            portfolio_df = portfolio_df.loc[portfolio_df['Symbol'] != symbol]

        # Save the updated data to CSV
        portfolio_df.to_csv(portfolio_file, index=False)
        transaction_df.to_csv(transaction_log, index=False)

    except Exception as e:
        # print(f"An error occurred: {e}")
        utils.Errors_logging.functions_error_log("update_portfolio", e, utils.Errors_logging.log_name_weekly_signals, symbol=symbol)


portfolio_file = './stocks_data_csv/data_base/portfolio.csv'
portfolio_df = pd.read_csv(portfolio_file)

def update_portfolio_details():
    try:
        portfolio_file = './stocks_data_csv/data_base/portfolio.csv'

        # Ensure the directory exists
        os.makedirs(os.path.dirname(portfolio_file), exist_ok=True)

        # Read or initialize the portfolio DataFrame
        if os.path.isfile(portfolio_file):
            portfolio_df = pd.read_csv(portfolio_file)
        else:
            #e = "Portfolio file not found."
            #Errors_logging.functions_error_log("update_portfolio_detail", e, Errors_logging.log_name_weekly_signals)
            return

        # Add new columns if they do not exist
        for col in ['Current Price', 'Change', 'Time (in weeks)']:
            if col not in portfolio_df.columns:
                portfolio_df[col] = None

        # Update new columns
        for index, row in portfolio_df.iterrows():
            current_price_str = utils.Stock_Data.get_stock_price(row['Symbol'])
            current_price = float(current_price_str.replace('$', ''))
            buying_price = float(row['Buying Price'].replace('$', ''))
            change = (current_price - buying_price) / buying_price * 100
            profit = current_price - buying_price
            buying_date = datetime.strptime(row['Buying date'], '%Y-%m-%d')
            time_in_weeks = (datetime.now() - buying_date).days // 7

            portfolio_df.at[index, 'Current Price'] = current_price_str
            portfolio_df.at[index, 'Profit'] = f'${profit:.2f}'
            portfolio_df.at[index, 'Change'] = f'{change:.2f}%'
            portfolio_df.at[index, 'Time (in weeks)'] = time_in_weeks

        # Save the updated data to CSV
        portfolio_df.to_csv(portfolio_file, index=False)

    except Exception as e:
        utils.Errors_logging.functions_error_log("update_portfolio_detail", e, utils.Errors_logging.log_name_weekly_signals)


def is_symbol_in_portfolio(symbol, file_path):
    """
    Checks if the given symbol is present in the portfolio.

    :param symbol: The stock symbol to check.
    :param file_path: The path to the portfolio CSV file.
    :return: True if the symbol is in the portfolio, False otherwise.
    """
    try:
        # Load the portfolio CSV file
        portfolio_df = pd.read_csv(file_path)

        # Check if the symbol is in the 'Symbol' column
        return symbol in portfolio_df['Symbol'].values
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False


def add_monthly_stock_data(symbol):
    try:
        lt_stock_data_csv = get_monthly_data(symbol)
        stock_data = load_data_from_csv(lt_stock_data_csv)
        calculate_macd(stock_data, 26, 3, 7)
        path_file = f'./stocks_data_csv/signal_data/{symbol}_monthly_data.csv'
        symbol_held = is_symbol_in_portfolio(symbol,
                                             file_path='./stocks_data_csv/data_base/portfolio.csv')

        if not os.path.exists(path_file):
            file_data = pd.DataFrame(columns=[
                'Date', 'Start Date', 'End Date', 'LT Trend', 'MACD Trend',
                'Highest Price', 'Highest MACD', 'Lowest Price', 'Lowest MACD',
                'Divergence spotted', 'Signal'
            ])

            new_rows_list = []

            for date in stock_data.index:
                try:
                    date_str = date.strftime('%Y-%m-%d')
                    lt_trend = get_lt_trend(stock_data, date_str)
                    macd_trend = get_macd_trend(stock_data, date_str)

                    if file_data.empty or macd_trend != file_data.iloc[-1]['MACD Trend'] or lt_trend != \
                            file_data.iloc[-1][
                                'LT Trend']:
                        # Create a new row
                        new_row = {
                            'Date': date_str,
                            'Start Date': date_str,
                            'End Date': None,
                            'LT Trend': lt_trend,
                            'MACD Trend': macd_trend,
                            'Highest Price': round(stock_data.loc[date]['High'], 2),
                            'Highest MACD': round(stock_data.loc[date]['MACD'], 2),
                            'Lowest Price': round(stock_data.loc[date]['Low'], 2),
                            'Lowest MACD': round(stock_data.loc[date]['MACD'], 2),
                            'Divergence spotted': None,
                            'Signal': None,
                        }
                        new_rows_list.append(new_row)

                        # Append new_row only once
                        if not file_data.empty:
                            file_data.at[file_data.index[-1], 'End Date'] = date_str
                            if len(file_data) > 4:
                                spot_divergence = spot_monthly_divergences(stock_data, file_data)
                                file_data.loc[file_data.index[-1], 'Divergence spotted'] = spot_divergence
                                # if spot_divergence == 'Buy - Monthly Divergence':
                                #     #Sending_Email.process_buy_signals(symbol, date_str)
                                #     update_portfolio(symbol, 'Buy', date_str)
                                # elif spot_divergence == 'Sell - Monthly divergence':
                                #     #Sending_Email.process_sell_signals(symbol, date_str)
                                #     update_portfolio(symbol, 'Sell', date_str)

                            else:
                                file_data.loc[file_data.index[-1], 'Divergence spotted'] = 'None'

                        file_data.loc[len(file_data)] = new_row
                        signal = spot_monthly_signals(file_data, date_str, lt_trend, stock_data)
                        file_data.loc[file_data.index[-1], 'Signal'] = signal
                        # if signal == 'Buy signal':
                        #     update_portfolio(symbol, 'Buy', date_str)

                    # Check for divergence and add to the last row if there's any

                    else:

                        last_row = file_data.iloc[-1]
                        # MACD trend didn't change, update the end date and check for new highs/lows
                        trend_start_date = last_row['Start Date']
                        trend_end_date = date_str

                        # Check if there have been new highs or lows
                        highest_price = round(stock_data['High'][trend_start_date:trend_end_date].max(), 2)
                        lowest_price = round(stock_data['Low'][trend_start_date:trend_end_date].min(), 2)
                        highest_macd = round(stock_data['MACD'][trend_start_date:trend_end_date].max(), 2)
                        lowest_macd = round(stock_data['MACD'][trend_start_date:trend_end_date].min(), 2)
                        signal = spot_monthly_signals(file_data, date_str, lt_trend, stock_data)

                        # Update the last row in file_data with the new end date and high/low values
                        file_data.loc[file_data.index[-1], 'End Date'] = trend_end_date
                        file_data.loc[file_data.index[-1], 'Highest Price'] = max(highest_price,
                                                                                  last_row['Highest Price'])
                        # file_data.loc[file_data.index[-1], 'Highest Price'] = highest_price
                        file_data.loc[file_data.index[-1], 'Lowest Price'] = min(lowest_price, last_row['Lowest Price'])
                        file_data.loc[file_data.index[-1], 'Highest MACD'] = max(highest_macd, last_row['Highest MACD'])
                        file_data.loc[file_data.index[-1], 'Lowest MACD'] = min(lowest_macd, last_row['Lowest MACD'])
                        file_data.loc[file_data.index[-1], 'Signal'] = signal

                        # if signal == 'Buy signal':
                        #     update_portfolio(symbol, 'Buy', date_str)

                except Exception as e:
                    utils.Errors_logging.functions_error_log("add_monthly_stock_data", e,
                                                       utils.Errors_logging.log_name_monthly_signals,
                                                       symbol=symbol)
                    continue

            # Save the new file
            file_data.to_csv(path_file, index=False)
            # print('Previous data added')

        else:
            file_data = pd.read_csv(path_file)

            # Get the last row of the file_data
            last_row = file_data.iloc[-1]

            current_date = stock_data.index[-1].strftime('%Y-%m-%d')
            lt_trend = get_lt_trend(stock_data, current_date)
            macd_trend = get_macd_trend(stock_data, current_date)

            new_rows_list = []

            if macd_trend != last_row['MACD Trend'] or lt_trend != file_data.iloc[-1]['LT Trend']:
                # MACD trend changed, update trend_start_date and add a new row
                trend_start_date = last_row['End Date']
                new_row = {
                    'Date': current_date,
                    'Start Date': current_date,
                    'End Date': None,
                    'LT Trend': lt_trend,
                    'MACD Trend': macd_trend,
                    'Highest Price': round(stock_data.tail(1)['High'].iloc[0], 2),
                    'Highest MACD': round(stock_data.tail(1)['MACD'].iloc[0], 2),
                    'Lowest Price': round(stock_data.tail(1)['Low'].iloc[0], 2),
                    'Lowest MACD': round(stock_data.tail(1)['MACD'].iloc[0], 2),
                    'Divergence spotted': None,
                    'Signal': None
                }

                file_data.at[file_data.index[-1], 'End Date'] = current_date
                spot_divergence = spot_monthly_divergences(stock_data, file_data)
                file_data.loc[file_data.index[-1], 'Divergence spotted'] = spot_divergence
                if spot_divergence == 'Buy - Monthly Divergence':
                    utils.Sending_Email.process_buy_signals(symbol, current_date)
                    update_portfolio(symbol, 'Buy', current_date)
                elif spot_divergence == 'Sell - Monthly divergence':
                    if symbol_held:
                        utils.Sending_Email.process_sell_signals(symbol, current_date)
                    update_portfolio(symbol, 'Sell', current_date)

                new_rows_list.append(new_row)
                file_data = pd.concat([file_data, pd.DataFrame([new_row])], ignore_index=True)
                signal = spot_monthly_signals(file_data, current_date, lt_trend, stock_data)
                file_data.loc[file_data.index[-1], 'Signal'] = signal
                if signal == 'Buy signal':
                    utils.Sending_Email.process_buy_signals(symbol, current_date)
                    update_portfolio(symbol, 'Buy', current_date)

            else:
                # MACD trend didn't change, update the end date and check for new highs/lows
                trend_start_date = last_row['Start Date']
                trend_end_date = current_date
                current_signal = last_row['Signal']

                # Check if there have been new highs or lows
                highest_price = round(stock_data['High'][trend_start_date:trend_end_date].max(), 2)
                lowest_price = round(stock_data['Low'][trend_start_date:trend_end_date].min(), 2)
                highest_macd = round(stock_data['MACD'][trend_start_date:trend_end_date].max(), 2)
                lowest_macd = round(stock_data['MACD'][trend_start_date:trend_end_date].min(), 2)
                signal = spot_monthly_signals(file_data, current_date, lt_trend, stock_data)
                if current_signal != signal:
                    if signal == 'Buy signal':
                        utils.Sending_Email.process_buy_signals(symbol, current_date)
                        update_portfolio(symbol, 'Buy', current_date)

                # Update the last row in file_data with the new end date and high/low values
                file_data.loc[file_data.index[-1], 'End Date'] = trend_end_date
                file_data.loc[file_data.index[-1], 'Highest Price'] = max(highest_price, last_row['Highest Price'])
                file_data.loc[file_data.index[-1], 'Lowest Price'] = min(lowest_price, last_row['Lowest Price'])
                file_data.loc[file_data.index[-1], 'Highest MACD'] = max(highest_macd, last_row['Highest MACD'])
                file_data.loc[file_data.index[-1], 'Lowest MACD'] = min(lowest_macd, last_row['Lowest MACD'])
                file_data.loc[file_data.index[-1], 'Signal'] = signal

            # Save the updated file_data back to the file
            file_data.to_csv(path_file, index=False)
            # print('Last week data added')
    except Exception as e:
        utils.Errors_logging.functions_error_log("add_monthly_stock_data", e,
                                           utils.Errors_logging.log_name_monthly_signals,
                                           symbol=symbol)


def add_weekly_stock_data(symbol):
    try:
        stock_data_csv = get_data(symbol)
        lt_stock_data_csv = get_monthly_data(symbol)
        stock_data = load_data_from_csv(stock_data_csv)
        lt_stock_data = load_data_from_csv(lt_stock_data_csv)
        calculate_macd(stock_data, 26, 3, 7)
        path_file = f'./stocks_data_csv/signal_data/{symbol}_weekly_data.csv'
        info = utils.Stock_Data.get_company_info(symbol)
        company_name = info['Company Name']
        symbol_held = is_symbol_in_portfolio(symbol,
                                             file_path='./stocks_data_csv/data_base/portfolio.csv')

        portfolio_file = './stocks_data_csv/data_base/portfolio.csv'
        portfolio_df = pd.read_csv(portfolio_file)

        if not os.path.exists(path_file):
            file_data = pd.DataFrame(columns=[
                'Date', 'Start Date', 'End Date', 'LT Trend', 'MACD Trend',
                'Highest Price', 'Highest MACD', 'Lowest Price', 'Lowest MACD',
                'Divergence spotted', 'Signal'
            ])

            new_rows_list = []

            for date in stock_data.index:
                try:
                    date_str = date.strftime('%Y-%m-%d')
                    lt_trend = get_lt_trend(lt_stock_data, date_str)
                    macd_trend = get_macd_trend(stock_data, date_str)

                    if file_data.empty or macd_trend != file_data.iloc[-1]['MACD Trend'] or lt_trend != \
                            file_data.iloc[-1][
                                'LT Trend']:
                        # Create a new row
                        new_row = {
                            'Date': date_str,
                            'Start Date': date_str,
                            'End Date': None,
                            'LT Trend': lt_trend,
                            'MACD Trend': macd_trend,
                            'Highest Price': round(stock_data.loc[date]['High'], 2),
                            'Highest MACD': round(stock_data.loc[date]['MACD'], 2),
                            'Lowest Price': round(stock_data.loc[date]['Low'], 2),
                            'Lowest MACD': round(stock_data.loc[date]['MACD'], 2),
                            'Divergence spotted': None,
                            'Signal': None,
                        }

                        # Append new_row only once
                        if not file_data.empty:
                            file_data.at[file_data.index[-1], 'End Date'] = date_str
                            if len(file_data) > 4:
                                check_date = file_data.iloc[-1]['Start Date']
                                spot_divergence = spot_weekly_divergences(stock_data, lt_stock_data, file_data,
                                                                          check_date)
                                if pd.isna(file_data.iloc[-1]['Divergence spotted']):
                                    # print(f'1: {date_str}:{spot_divergence}')
                                    file_data.loc[file_data.index[-1], 'Divergence spotted'] = spot_divergence
                                # if spot_divergence == 'Buy - divergence':
                                #     Sending_Email.process_buy_signals(symbol, date_str)
                        try:
                            signal_divergence = divergences_signal(lt_trend, file_data, date_str)
                            if signal_divergence != None:
                                new_row['Divergence spotted'] = signal_divergence

                        except Exception as e:
                            utils.Errors_logging.functions_error_log("add_weekly_stock_data", e,
                                                               utils.Errors_logging.log_name_weekly_signals,
                                                               symbol=symbol)

                        new_rows_list.append(new_row)

                        file_data = pd.concat([file_data, pd.DataFrame([new_row])], ignore_index=True)
                        signal = spot_weekly_signals(file_data, date_str, lt_trend, stock_data, lt_stock_data)
                        file_data.at[file_data.index[-1], 'Signal'] = signal

                    # Check for divergence and add to the last row if there's any

                    else:
                        last_row = file_data.iloc[-1]
                        # MACD trend didn't change, update the end date and check for new highs/lows
                        trend_start_date = last_row['Start Date']
                        trend_end_date = date_str

                        # Check if there have been new highs or lows
                        highest_price = round(stock_data['High'][trend_start_date:trend_end_date].max(), 2)
                        lowest_price = round(stock_data['Low'][trend_start_date:trend_end_date].min(), 2)
                        highest_macd = round(stock_data['MACD'][trend_start_date:trend_end_date].max(), 2)
                        lowest_macd = round(stock_data['MACD'][trend_start_date:trend_end_date].min(), 2)
                        signal_divergence = divergences_signal(lt_trend, file_data, date_str)

                        # Update the last row in file_data with the new end date and high/low values
                        file_data.loc[file_data.index[-1], 'End Date'] = trend_end_date
                        file_data.loc[file_data.index[-1], 'Highest Price'] = max(highest_price,
                                                                                  last_row['Highest Price'])
                        file_data.loc[file_data.index[-1], 'Lowest Price'] = min(lowest_price, last_row['Lowest Price'])
                        file_data.loc[file_data.index[-1], 'Highest MACD'] = max(highest_macd, last_row['Highest MACD'])
                        file_data.loc[file_data.index[-1], 'Lowest MACD'] = min(lowest_macd, last_row['Lowest MACD'])
                        if signal_divergence != None:
                            file_data.loc[file_data.index[-1], 'Divergence spotted'] = signal_divergence

                        if file_data.iloc[-1]['Signal'] == None or file_data.iloc[-1][
                            'Signal'] == 'Waiting for confirmation : Buy' or file_data.iloc[-1][
                            'Signal'] == 'Waiting for confirmation : Sell':
                            signal = spot_weekly_signals(file_data, date_str, lt_trend, stock_data, lt_stock_data)
                            file_data.loc[file_data.index[-1], 'Signal'] = signal



                except Exception as e:
                    utils.Errors_logging.functions_error_log("add_weekly_stock_data", e,
                                                       utils.Errors_logging.log_name_weekly_signals,
                                                       symbol=symbol)
                    continue

            # Save the new file
            file_data.to_csv(path_file, index=False)
            # print('Previous data added')

        else:
            file_data = pd.read_csv(path_file)

            # Get the last row of the file_data
            last_row = file_data.iloc[-1]

            current_date = stock_data.index[-1].strftime('%Y-%m-%d')
            lt_trend = get_lt_trend(lt_stock_data, current_date)
            macd_trend = get_macd_trend(stock_data, current_date)

            new_rows_list = []

            if macd_trend != last_row['MACD Trend'] or lt_trend != last_row['LT Trend']:
                # MACD trend changed, update trend_start_date and add a new row
                trend_start_date = last_row['End Date']
                new_row = {
                    'Date': current_date,
                    'Start Date': current_date,
                    'End Date': None,
                    'LT Trend': lt_trend,
                    'MACD Trend': macd_trend,
                    'Highest Price': round(stock_data.tail(1)['High'].iloc[0], 2),
                    'Highest MACD': round(stock_data.tail(1)['MACD'].iloc[0], 2),
                    'Lowest Price': round(stock_data.tail(1)['Low'].iloc[0], 2),
                    'Lowest MACD': round(stock_data.tail(1)['MACD'].iloc[0], 2),
                    'Divergence spotted': None,
                    'Signal': None
                }

                file_data.at[file_data.index[-1], 'End Date'] = current_date
                signal_divergence = divergences_signal(lt_trend, file_data, current_date)
                if signal_divergence != 'None':
                    file_data.loc[file_data.index[-1], 'Divergence spotted'] = signal_divergence
                    if signal_divergence == 'Buy - divergence':
                        utils.Sending_Email.process_buy_signals(symbol, current_date)
                        update_portfolio(symbol, 'Buy', current_date)
                    elif signal_divergence == 'Sell - divergence':
                        if symbol_held:
                            utils.Sending_Email.process_sell_signals(symbol, current_date)
                        update_portfolio(symbol, 'Sell', current_date)
                else:
                    check_date = file_data.iloc[-1]['Start Date']
                    spot_divergence = spot_weekly_divergences(stock_data, lt_stock_data, file_data, check_date)
                    file_data.loc[file_data.index[-1], 'Divergence spotted'] = spot_divergence

                new_rows_list.append(new_row)
                file_data = pd.concat([file_data, pd.DataFrame([new_row])], ignore_index=True)
                signal = spot_weekly_signals(file_data, current_date, lt_trend, stock_data, lt_stock_data)
                file_data.loc[file_data.index[-1], 'Signal'] = signal
                if signal == 'Buy signal':
                    utils.Sending_Email.process_buy_signals(symbol, current_date)
                    update_portfolio(symbol, 'Buy', current_date)
                elif signal == 'Sell signal':
                    if symbol_held:
                        utils.Sending_Email.process_sell_signals(symbol, current_date)
                    update_portfolio(symbol, 'Sell', current_date)

            else:
                # MACD trend didn't change, update the end date and check for new highs/lows
                trend_start_date = last_row['Start Date']
                trend_end_date = current_date
                current_signal = last_row['Signal']
                current_divergence = last_row['Divergence spotted']

                # Check if there have been new highs or lows
                highest_price = round(stock_data['High'][trend_start_date:trend_end_date].max(), 2)
                lowest_price = round(stock_data['Low'][trend_start_date:trend_end_date].min(), 2)
                highest_macd = round(stock_data['MACD'][trend_start_date:trend_end_date].max(), 2)
                lowest_macd = round(stock_data['MACD'][trend_start_date:trend_end_date].min(), 2)

                signal_divergence = divergences_signal(lt_trend, file_data, current_date)
                if current_divergence != signal_divergence:
                    if signal_divergence == 'Buy - divergence':
                        utils.Sending_Email.process_buy_signals(symbol, current_date)
                        update_portfolio(symbol, 'Buy', current_date)
                    elif signal_divergence == 'Sell - divergence':
                        if symbol_held:
                            utils.Sending_Email.process_sell_signals(symbol, current_date)
                        update_portfolio(symbol, 'Sell', current_date)

                # Update the last row in file_data with the new end date and high/low values
                file_data.loc[file_data.index[-1], 'End Date'] = trend_end_date
                file_data.loc[file_data.index[-1], 'Highest Price'] = max(highest_price, last_row['Highest Price'])
                file_data.loc[file_data.index[-1], 'Lowest Price'] = min(lowest_price, last_row['Lowest Price'])
                file_data.loc[file_data.index[-1], 'Highest MACD'] = max(highest_macd, last_row['Highest MACD'])
                file_data.loc[file_data.index[-1], 'Lowest MACD'] = min(lowest_macd, last_row['Lowest MACD'])
                file_data.loc[file_data.index[-1], 'Divergence spotted'] = signal_divergence

                signal = spot_weekly_signals(file_data, current_date, lt_trend, stock_data, lt_stock_data)
                file_data.loc[file_data.index[-1], 'Signal'] = signal
                if current_signal != signal:
                    if signal == 'Buy signal':
                        utils.Sending_Email.process_buy_signals(symbol, current_date)
                        update_portfolio(symbol, 'Buy', current_date)
                    elif signal == 'Sell signal':
                        if symbol_held:
                            utils.Sending_Email.process_sell_signals(symbol, current_date)
                        update_portfolio(symbol, 'Sell', current_date)

            # Save the updated file_data back to the file
            file_data.to_csv(path_file, index=False)
            # print('Last week data added')

    except Exception as e:
        utils.Errors_logging.functions_error_log("add_weekly_stock_data", e,
                                           utils.Errors_logging.log_name_weekly_signals,
                                           symbol=symbol)


# symbol = 'UBER'
# stock_data_csv = get_data(symbol)
# lt_stock_data_csv = get_monthly_data(symbol)
# stock_data = load_data_from_csv(stock_data_csv)
# current_date = stock_data.index[-1].strftime('%Y-%m-%d')
# print(current_date)
# price = Stock_Data.get_stock_price(symbol)
# print(price)
# update_portfolio(symbol, 'Sell', current_date)
#
# portfolio = pd.read_csv('./stocks_data_csv/data_base/portfolio.csv')
# print(portfolio)
# print(portfolio.dtypes)