import pandas as pd
import numpy as np
import yfinance as yf
import ta
import os
import math
from dotenv import load_dotenv
from supabase import create_client, Client


def get_company_info(symbol):
    load_dotenv()

    url: str = os.getenv('sb_url')
    key: str = os.getenv('sb_api_key')  # Replace with your Supabase API key
    supabase: Client = create_client(url, key)

    response = supabase.table('stocks_list').select("*").eq('Symbol', symbol).execute()
    company_info = response.data[0]

    return company_info


def get_stock_price(symbol):
    r = round(yf.Ticker(symbol).history(interval="1wk")['Close'].tail(1).values[0],2)
    price = f'${r}'
    return price


def get_last_eps(symbol):
    try:
        stock = yf.Ticker(symbol)
        inc_stm = stock.get_income_stmt()
        row_name = 'DilutedEPS'

        # Extract 'DilutedEPS' values directly from the DataFrame
        eps_df = inc_stm.loc[row_name].reset_index()
        eps_df.columns = ['Year', 'EPS']
        eps_df['Year'] = pd.to_datetime(eps_df['Year']).dt.strftime('%Y')
        eps_df['Year'] = eps_df['Year'].astype('int64')

        return eps_df
    except:
        return None



def get_eps(symbol):
    try:
        stock = yf.Ticker(symbol)
        try:
            eps = stock.info.get('trailingEps')
            return round(eps, 1)
        except:
            try:
                # If 'trailingEps' is not available or is NaN, try 'Diluted EPS'
                inc_stm = stock.income_stmt
                eps = inc_stm.loc['Diluted EPS'].iloc[0]

                # If the first 'Diluted EPS' is NaN, try the next
                if math.isnan(eps):
                    eps = inc_stm.loc['Diluted EPS'].iloc[1]

                return round(eps, 1) if eps is not None and not math.isnan(eps) else None
            except:
                return None

    except:
        # print(f"An error occurred: {e}")
        return None


def get_3years_av_eps(symbol):
    try:
        last_eps = get_last_eps(symbol)
        last_years_eps = last_eps['EPS'].dropna().head(3)
        av_eps = round(last_years_eps.mean(), 2)
        return av_eps
    except:
        return None


def get_yearly_eps(symbol):
    try:
        stock = yf.Ticker(symbol)
        earnings_dates = stock.get_earnings_dates(limit=100)
        earnings_dates = earnings_dates[earnings_dates['Reported EPS'].notna()]
        earnings_dates['Year'] = earnings_dates.index.year
        yearly_eps = earnings_dates.groupby('Year')['Reported EPS'].sum().reset_index()
        result = yearly_eps.sort_values(by='Year', ascending=False).head(10)
        result['Year'] = result['Year'].astype(object)
        return result
    except:
        return None


def is_historical_reliable(symbol):
    try:
        eps_from_inc = get_last_eps(symbol)
        result = get_yearly_eps(symbol)

        common_years = set(eps_from_inc['Year']) & set(result['Year'])
        eps_inc = eps_from_inc.set_index('Year').loc[common_years, 'EPS'].sum()
        eps_result = result.set_index('Year').loc[common_years, 'Reported EPS'].sum()
        pct_diff = math.ceil(eps_inc / eps_result * 100)

        return 90 <= pct_diff <= 110
    except:
        return False


def get_yearly_growth(symbol):
    try:
        result = get_last_eps(symbol)
        for i in range(len(result) - 1, 0, -1):
            start = result.at[i, 'EPS']
            end = result.at[i - 1, 'EPS']
            if start < 0 and end < 0:
                result.at[i - 1, 'Growth'] = round((end / start - 1) * -1, 2)
            elif start < 0 and end > 0:
                result.at[i - 1, 'Growth'] = round((end / start - 1) * -1, 2)
            else:
                result.at[i - 1, 'Growth'] = round(end / start - 1, 2)
        return result
    except:
        return None

def calculate_eps_growth(result_df):
    if result_df['Growth'].isna().all():
        return None
    av_eps_growth = round(result_df['Growth'].mean(), 2)
    return av_eps_growth


def calculate_median_eps_growth(result_df):
    if result_df['Growth'].isna().all():
        return None
    median_eps_growth = round(result_df['Growth'].median(), 2)
    return median_eps_growth


def get_last_growth(symbol):
    try:
        result_df = get_yearly_growth(symbol)
        if result_df is None:
            return None

        last_growth = result_df.iloc[0]['Growth']
        if np.isnan(last_growth) and len(result_df) > 1:
            last_growth = result_df.iloc[1]['Growth']

        return None if np.isnan(last_growth) else last_growth
    except:
        return None


def get_years_of_data(symbol):
    try:
        result_df = get_yearly_growth(symbol)
        return len(result_df)
    except:
        return None


# Stock Health Functions

def get_debt(symbol):
    try:
        stock = yf.Ticker(symbol)
        bs = stock.quarterly_balance_sheet.iloc[:, 0]
        debt = bs.get('Total Debt', 0)
        return debt
    except:
        return None


def debt_to_equity_ratio(symbol):
    try:
        stock = yf.Ticker(symbol)
        bs = stock.quarterly_balance_sheet.iloc[:, 0]
        debts = get_debt(symbol)
        total_equity = bs.get('Total Equity Gross Minority Interest', 0)

        if debts is None or total_equity in (None, 0):
            return None

        der = round(debts / total_equity, 2)
        return der
    except:
        return None


def get_nwc(symbol):
    try:
        stock = yf.Ticker(symbol)
        bs = stock.quarterly_balance_sheet.iloc[:, 0]
        current_assets = bs.get('Current Assets', 0) or bs.get('Cash And Cash Equivalents', 0)
        current_liabilities = bs.get('Current Liabilities', 0)
        shares_issued = bs.get('Share Issued', 0)

        # Ensure that shares_issued is not zero to avoid division by zero
        if shares_issued == 0:
            return None

        nwc = current_assets - current_liabilities
        nwc_per_share = nwc / shares_issued

        # Check if nwc_per_share is NaN
        if math.isnan(nwc_per_share):
            return None

        return round(nwc_per_share, 2)
    except:
        return None


def get_fcf(symbol):
    try:
        stock = yf.Ticker(symbol)
        cf = stock.quarterly_cashflow.iloc[:, 0]
        fcf = cf.get('Free Cash Flow', None)
        return fcf
    except:
        return None


def get_roe(symbol):
    try:
        stock = yf.Ticker(symbol)
        bs = stock.balance_sheet.iloc[:, 0]
        total_equity = bs.get('Total Equity Gross Minority Interest', None)
        ist = stock.income_stmt.iloc[:, 0]
        net_income = ist.get('Net Income', None)

        # Ensure total_equity and net_income are not None and total_equity is not zero
        if total_equity is not None and total_equity != 0 and net_income is not None:
            roe = net_income / total_equity

            # Check if roe is NaN
            if math.isnan(roe):
                return None

            return round(roe, 2)

        return None
    except:
        return None


# Technical Data

def get_data(symbol):
    # Download stock data
    stock_data = yf.download(symbol, start=data_start_date, end=data_end_date, interval='1wk')

    # Save the data to a CSV file
    csv_file_name = f"{symbol}.csv"
    stock_data.to_csv(csv_file_name)
    return csv_file_name

def get_monthly_data(symbol):
    # Download stock data
    stock_data = yf.download(symbol, start=data_start_date, end=data_end_date, interval='1mo')

    # Save the data to a CSV file
    csv_file_name = f"{symbol}_monthly.csv"
    stock_data.to_csv(csv_file_name)

    return csv_file_name

def load_data_from_csv(csv_file_name):
    # Load stock data from a CSV file
    stock_data = pd.read_csv(csv_file_name, index_col='Date', parse_dates=True)

    return stock_data

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

def bb_low_indicator(stock_data):
    bb = ta.volatility.BollingerBands(stock_data['Low'])
    bb_low = bb.bollinger_lband_indicator()
    return bb_low

def bb_high_indicator(stock_data):
  bb = ta.volatility.BollingerBands(stock_data['High'])
  bb_high = bb.bollinger_hband_indicator()
  return bb_high
