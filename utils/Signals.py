import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta, date
import ta
import os
import utils.Stock_Data
import utils.Sending_Email
import utils.Errors_logging
from dotenv import load_dotenv
from supabase import create_client, Client

data_end_date = datetime.now()
five_years_ago = data_end_date - timedelta(days=365 * 5)
data_start_date = '2015-01-05'


load_dotenv()

url: str = os.getenv('sb_url')
key: str = os.getenv('sb_api_key')  # Replace with your Supabase API key
supabase: Client = create_client(url, key)

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
            csv_file_name = f"stock_data/{symbol}.csv"
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
            csv_file_name = f"stock_data/{symbol}_monthly.csv"
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
        return stock_data
    except:
        return stock_data
        # print(f"KeyError: {e}. The 'MACD_Histogram' column is not available in the data.")



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


def update_portfolio(symbol, action, price, date):
    try:
        # Get the current stock price

        response = supabase.table('stocks_list').select("Stock_id", "Symbol").eq("Symbol", symbol).execute()
        symbols_data = response.data
        stock_id = symbols_data[0]["Stock_id"]

        if action == 'Buy':
            # Insert new record into 'portfolio' table
            data = {'Stock_id': stock_id, 'Symbol': symbol, 'Buying date': date, 'Buying Price': price}
            supabase.table('portfolio').insert(data).execute()
        elif action == 'Sell':
            # Fetch existing records from 'portfolio' table
            portfolio_data = supabase.table('portfolio').select('*').eq('Symbol', symbol).execute().data


            # Perform selling operations...
            for row in portfolio_data:
                buying_price = float(row['Buying Price'])
                selling_price = float(price)
                profit = selling_price - buying_price
                yield_ = profit / buying_price

                # Insert new record into 'transaction logs' table
                transaction = {
                    'Stock_id': stock_id,
                    'Symbol': symbol,
                    'Buying date': row['Buying date'],
                    'Buying Price': row['Buying Price'],
                    'Selling Date': date,
                    'Selling Price': selling_price,
                    'Profit': profit,
                    'Yield': yield_ * 100
                }
                supabase.table('transactions logs').insert(transaction).execute()


            # Remove the sold stock from the 'portfolio' table
            supabase.table('portfolio').delete().eq('Symbol', symbol).execute()

    except Exception as e:
        utils.Errors_logging.functions_error_log("update_portfolio", e, utils.Errors_logging.log_name_weekly_signals,
                                                 symbol=symbol)


def update_portfolio_details():
    try:
        # Fetch portfolio data from Supabase
        data = supabase.table('portfolio').select('*').execute().data

        if not data:
            return  # Handle case where no data is found

        # Update each row in the portfolio
        for row in data:
            stock_id = row['Stock_id']
            symbol = row['Symbol']
            current_price = float(utils.Stock_Data.get_stock_price(symbol))
            buying_price = float(row['Buying Price'])
            change = (current_price - buying_price) / buying_price * 100
            profit = current_price - buying_price
            buying_date = datetime.datetime.strptime(row['Buying date'], '%Y-%m-%d')
            time_in_weeks = (datetime.datetime.now() - buying_date).days // 7

            # Update the row in the database
            updated_data = {
                'Current Price': current_price,
                'Profit': profit,
                'Change': change,
                'Time (in weeks)': time_in_weeks
            }
            supabase.table('portfolio').update(updated_data).eq('Symbol', symbol).execute()

    except Exception as e:
        utils.Errors_logging.functions_error_log("update_portfolio_detail", e, utils.Errors_logging.log_name_weekly_signals)


def is_symbol_in_portfolio(symbol):
    """
    Checks if the given symbol is present in the portfolio in the Supabase database.

    :param symbol: The stock symbol to check.
    :return: True if the symbol is in the portfolio, False otherwise.
    """
    try:
        # Query the 'portfolio' table for the symbol
        data = supabase.table('portfolio').select('Symbol').eq('Symbol', symbol).execute().data

        # Check if the symbol is found
        return len(data) > 0
    except Exception as e:
        utils.Errors_logging.functions_error_log("is_symbol_in_portfolio", e, utils.Errors_logging.log_name_weekly_signals, symbol=symbol)
        return False


def add_weekly_stock_data(symbol):
    signals_list = []
    try:
        stock_data_csv = get_data(symbol)
        lt_stock_data_csv = get_monthly_data(symbol)
        stock_data = load_data_from_csv(stock_data_csv)
        lt_stock_data = load_data_from_csv(lt_stock_data_csv)
        calculate_macd(stock_data, 26, 3, 7)
        path_file = f'signal_data/{symbol}_weekly_data.csv'
        info = utils.Stock_Data.get_company_info(symbol)
        symbol_held = is_symbol_in_portfolio(symbol)

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
                            utils.Errors_logging.functions_error_log("add_weekly_stock_data: new row", e,
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
            print('Previous data added')

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
                        price = utils.Stock_Data.get_stock_price(symbol)
                        signal_dict = signal_to_dict(symbol, 'Buy', price, current_date)
                        if not signals_list:
                            signals_list.append(signal_dict)
                        # utils.Sending_Email.process_buy_signals(symbol, current_date)
                        update_portfolio(symbol, 'Buy', current_date)
                    elif signal_divergence == 'Sell - divergence':
                        if symbol_held:
                            price = utils.Stock_Data.get_stock_price(symbol)
                            signal_dict = signal_to_dict(symbol, 'Sell', price, current_date)
                            if not signals_list or (signals_list and signals_list[0]['Signal'] == 'Buy'):
                                signals_list = [signal_dict]
                            # utils.Sending_Email.process_sell_signals(symbol, current_date)
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
                    price = utils.Stock_Data.get_stock_price(symbol)
                    signal_dict = signal_to_dict(symbol, 'Buy', price, current_date)
                    if not signals_list:
                        signals_list.append(signal_dict)
                    # utils.Sending_Email.process_buy_signals(symbol, current_date)
                    update_portfolio(symbol, 'Buy', current_date)
                elif signal == 'Sell signal':
                    if symbol_held:
                        price = utils.Stock_Data.get_stock_price(symbol)
                        signal_dict = signal_to_dict(symbol, 'Sell', price, current_date)
                        if not signals_list or (signals_list and signals_list[0]['Signal'] == 'Buy'):
                            signals_list = [signal_dict]
                        # utils.Sending_Email.process_sell_signals(symbol, current_date)
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
                        price = utils.Stock_Data.get_stock_price(symbol)
                        signal_dict = signal_to_dict(symbol, 'Buy', price, current_date)
                        if not signals_list:
                            signals_list.append(signal_dict)
                        # utils.Sending_Email.process_buy_signals(symbol, current_date)
                        update_portfolio(symbol, 'Buy', current_date)
                    elif signal_divergence == 'Sell - divergence':
                        if symbol_held:
                            price = utils.Stock_Data.get_stock_price(symbol)
                            signal_dict = signal_to_dict(symbol, 'Sell', price, current_date)
                            if not signals_list or (signals_list and signals_list[0]['Signal'] == 'Buy'):
                                signals_list = [signal_dict]
                            # utils.Sending_Email.process_sell_signals(symbol, current_date)
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
                        price = utils.Stock_Data.get_stock_price(symbol)
                        signal_dict = signal_to_dict(symbol, 'Buy', price, current_date)
                        if not signals_list:
                            signals_list.append(signal_dict)
                        # utils.Sending_Email.process_buy_signals(symbol, current_date)
                        update_portfolio(symbol, 'Buy', current_date)
                    elif signal == 'Sell signal':
                        if symbol_held:
                            price = utils.Stock_Data.get_stock_price(symbol)
                            signal_dict = signal_to_dict(symbol, 'Sell', price, current_date)
                            if not signals_list or (signals_list and signals_list[0]['Signal'] == 'Buy'):
                                signals_list = [signal_dict]
                            # utils.Sending_Email.process_sell_signals(symbol, current_date)
                        update_portfolio(symbol, 'Sell', current_date)

            # Save the updated file_data back to the file
            file_data.to_csv(path_file, index=False)
            # print('Last week data added')

    except Exception as e:
        utils.Errors_logging.functions_error_log("add_weekly_stock_data", e,
                                           utils.Errors_logging.log_name_weekly_signals,
                                           symbol=symbol)

    return signals_list


def add_monthly_stock_data(symbol):
    signals_list = []
    try:
        lt_stock_data_csv = get_monthly_data(symbol)
        stock_data = load_data_from_csv(lt_stock_data_csv)
        calculate_macd(stock_data, 26, 3, 7)
        path_file = f'signal_data/{symbol}_monthly_data.csv'
        symbol_held = is_symbol_in_portfolio(symbol)

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
                    price = utils.Stock_Data.get_stock_price(symbol)
                    signal_dict = signal_to_dict(symbol, 'Buy', price, current_date)
                    if not signals_list:
                        signals_list.append(signal_dict)
                    # utils.Sending_Email.process_buy_signals(symbol, current_date)
                    update_portfolio(symbol, 'Buy', current_date)
                elif spot_divergence == 'Sell - Monthly divergence':
                    if symbol_held:
                        price = utils.Stock_Data.get_stock_price(symbol)
                        signal_dict = signal_to_dict(symbol, 'Sell', price, current_date)
                        if not signals_list or (signals_list and signals_list[0]['Signal'] == 'Buy'):
                            signals_list = [signal_dict]
                        # utils.Sending_Email.process_sell_signals(symbol, current_date)
                        update_portfolio(symbol, 'Sell', current_date)

                new_rows_list.append(new_row)
                file_data = pd.concat([file_data, pd.DataFrame([new_row])], ignore_index=True)
                signal = spot_monthly_signals(file_data, current_date, lt_trend, stock_data)
                file_data.loc[file_data.index[-1], 'Signal'] = signal
                if signal == 'Buy signal':
                    price = utils.Stock_Data.get_stock_price(symbol)
                    signal_dict = signal_to_dict(symbol, 'Buy', price, current_date)
                    if not signals_list:
                        signals_list.append(signal_dict)
                    # utils.Sending_Email.process_buy_signals(symbol, current_date)
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
                        price = utils.Stock_Data.get_stock_price(symbol)
                        signal_dict = signal_to_dict(symbol, 'Buy', price, current_date)
                        if not signals_list:
                            signals_list.append(signal_dict)
                        # utils.Sending_Email.process_buy_signals(symbol, current_date)
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

    return signals_list





def signal_to_dict(symbol, signal, price, date):
    stock_info = utils.Stock_Data.get_company_info(symbol)
    name = stock_info["Company Name"]
    stock_id = stock_info["Stock_id"]
    signal = {
        "Stock Id": stock_id,
        "Symbol": symbol,
        "Name": name,
        "Signal": signal,
        "Price": price,
        "Date": date
        }
    return signal



def signal_stock():
    try:
        # Fetch rows where 'Top 100' is True
        response = supabase.table('stocks_ranking_data').select('Symbol').eq('Top 100', True).execute()

        # Extract the 'Symbol' column values into a list
        symbols = [row['Symbol'] for row in response.data]
        return symbols
    except Exception as e:
        utils.Errors_logging.functions_error_log("signal stocks empty", e, utils.Errors_logging.log_name_rundb)
        return []


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