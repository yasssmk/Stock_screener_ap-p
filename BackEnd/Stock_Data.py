import pandas as pd
import sqlite3
from sqlite3 import connect
import csv
import numpy as np
import random
import yfinance as yf
from datetime import datetime, timedelta, date
import ta
import os
#import matplotlib.pyplot as plt
import math
from scipy import stats
from io import StringIO



def get_company_info(symbol):
    stock_list_df = pd.read_csv('./stocks_data_csv/data_base/stock_list_data_base.csv')
    # Find the row corresponding to the provided symbol
    symbol_row = stock_list_df[stock_list_df['Symbol'] == symbol]

    # Initialize an empty dictionary to store company information
    company_info = {}

    # Extract the desired information using setdefault
    company_info.setdefault('Company Name', symbol_row['Company Name'].values[0])
    company_info.setdefault('Country', symbol_row['Country'].values[0])
    company_info.setdefault('Sector', symbol_row['Sector'].values[0])
    company_info.setdefault('Industry', symbol_row['Industry'].values[0])

    return company_info

def get_stock_price(symbol):
    r = round(yf.Ticker(symbol).history(interval="1wk")['Close'].tail(1).values[0],2)
    price = f'${r}'
    return price

# def get_stock_price(symbol, date_str):
#     # Convert string date to datetime object
#     date = datetime.strptime(date_str, '%Y-%m-%d')
#
#     # Initialize variables
#     attempts = 0
#     max_attempts = 4
#     close_price = None
#
#     # Download data for the week of the given date
#     while attempts < max_attempts:
#         try:
#             # Try to get the closing price for 'date'
#             data = yf.download(symbol, start=date.strftime('%Y-%m-%d'), end=(date + timedelta(days=1)).strftime('%Y-%m-%d'))
#             close_price = round(data['Close'].iloc[0], 2)  # Get the first close price in the returned data
#             break
#         except (KeyError, IndexError):
#             # If there's no data (KeyError or IndexError because data is empty), move to the previous day
#             date -= timedelta(days=1)
#             attempts += 1
#
#     if close_price is not None:
#         return f'${close_price}'
#     else:
#         # If no data available after 4 attempts, return a message indicating no data was found
#         return f"No data available for {symbol} on or before {date_str}"

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
        eps = round(stock.info.get('trailingEps', None),1)
        return eps
    except:
        try:
            inc_stm = stock.income_stmt
            eps = round(inc_stm.loc['Diluted EPS'].iloc[0],1)
            return eps
        except:
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
    av_eps_growth = round(result_df['Growth'].mean(), 2)
    return av_eps_growth


def calculate_median_eps_growth(result_df):
    median_eps_growth = round(result_df['Growth'].median(), 2)
    return median_eps_growth


def get_last_growth(symbol):
    try:
        result_df = get_yearly_growth(symbol)
        last_growth = result_df.iloc[0]['Growth']
        if np.isnan(last_growth):
            last_growth = result_df.iloc[1]['Growth']
        return last_growth
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
        if debts != 0:
            der = round(debts / total_equity, 2)
        else:
            der = 0
        return der
    except:
        return None


def get_nwc(symbol):
    try:
        stock = yf.Ticker(symbol)
        bs = stock.quarterly_balance_sheet.iloc[:, 0]
        current_assets = bs.get('Current Assets', 0) or bs.get('Cash And Cash Equivalents', 0)
        current_liabilities = bs.get('Current Liabilities', 0)
        nwc = current_assets - current_liabilities
        nwc_per_share = round(nwc / bs.get('Share Issued', 0), 2)
        return nwc_per_share
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
        if total_equity is not None and net_income is not None:
            roe = round(net_income / total_equity, 2)
            return roe
        return None
    except:
        return None


# Custom Ranking Function

# def custom_ranking(symbol):
#     try:
#         stock_info = get_company_info(symbol)
#         industry = stock_info['Industry']
#         sector = stock_info['Sector']
#         name = stock_info['Company Name']
#
#         sector_df = pd.read_csv(f'{sector}_stocks_growth.csv')
#         stock_growth_stat = sector_df[sector_df['Symbol'] == symbol]
#
#         industries_stats = calculate_industry_growth(sector)
#         industry_stats = industries_stats[industries_stats['Industry'] == industry]
#
#         if industry_stats['Number of companies'].values[0] > 10:
#             delta_eps = (stock_growth_stat['3 years av'].values[0] - industry_stats['3 years average'].values[0])
#         else:
#             sector_statistics = calculate_sector_growth(sector)
#             delta_eps = (stock_growth_stat['3 years av'].values[0] - sector_statistics['3 Years average EPS'])
#
#         value_eps = (stock_growth_stat['3 years av'].values[0] + delta_eps) * 0.8 + \
#                     stock_growth_stat['Last EPS'].values[0] * 0.2
#
#         industries_health_stats = calculate_industry_health(sector)
#         indus_health_stats = industries_health_stats[industries_health_stats['Industry'] == industry]
#         roe = stock_growth_stat['ROE'].values[0]
#
#         if industry_stats['Number of companies'].values[0] > 10:
#             delta_roe = (roe - indus_health_stats['Median ROE'].values[0])
#         else:
#             sector_health_stats = calculate_sector_health(sector)
#             delta_roe = (roe - sector_health_stats['Median ROE'])
#
#         value_eps = (stock_growth_stat['3 years av'].values[0] + delta_eps) * 0.7 + \
#                     stock_growth_stat['Last EPS'].values[0] * 0.3
#         value_roe = roe + delta_roe
#         total_value = value_eps * 0.7 + value_roe * 0.3
#
#         sector_df['Growth percentile'] = sector_df.groupby('Industry')['EPS average Growth'].rank(pct=True)
#         sector_df['Total Growth percentile'] = sector_df['EPS average Growth'].rank(pct=True)
#         growth_percentile_by_indus = sector_df[sector_df['Symbol'] == symbol]['Growth percentile'].values[0]
#         growth_percentile = sector_df[sector_df['Symbol'] == symbol]['Total Growth percentile'].values[0]
#
#         sector_df['Last Growth percentile'] = sector_df.groupby('Industry')['Last Growth'].rank(pct=True)
#         sector_df['Total last Growth percentile'] = sector_df['Last Growth'].rank(pct=True)
#         last_growth_percentile_by_indus = sector_df[sector_df['Symbol'] == symbol]['Last Growth percentile'].values[0]
#         last_growth_percentile = sector_df[sector_df['Symbol'] == symbol]['Total last Growth percentile'].values[0]
#
#         if industry_stats['Number of companies'].values[0] > 10:
#             value_growth = last_growth_percentile_by_indus * 0.25 + last_growth_percentile * 0.25 + growth_percentile_by_indus * 0.25 + growth_percentile * 0.25
#         else:
#             value_growth = last_growth_percentile * 0.5 + growth_percentile * 0.5
#
#         sector_health_df = pd.read_csv(f'{sector}_financial_data.csv')
#         stock_health_stat = sector_health_df[sector_health_df['Symbol'] == symbol]
#
#         sector_health_df['NWC percentile'] = sector_health_df.groupby('Industry')['NWC per share'].rank(pct=True)
#         sector_health_df['DER percentile'] = sector_health_df.groupby('Industry')['Debt to Equity'].rank(pct=True)
#         nwc_percetile = sector_health_df[sector_health_df['Symbol'] == symbol]['NWC percentile'].values[0]
#         der_percetile = 1 - sector_health_df[sector_health_df['Symbol'] == symbol]['DER percentile'].values[0]
#         risk_ratio = (nwc_percetile * 0.5 + der_percetile * 0.5)
#
#         composite_score = (total_value * 4 * value_growth * risk_ratio)
#         composite_score = round(composite_score, 1)
#
#         return composite_score
#     except:
#         return None


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




#Original
# def get_company_info(symbol):
#     # Find the row corresponding to the provided symbol
#     stock_list_df = pd.read_csv('stock_list_filtered.csv')
#     symbol_row = stock_list_df[stock_list_df['Symbol'] == symbol]
#
#     # Initialize an empty dictionary to store company information
#     company_info = {}
#
#     # Check if the row exists
#     if not symbol_row.empty:
#         # Extract the desired information
#         company_info['Company Name'] = symbol_row['Company Name'].values[0]
#         company_info['Country'] = symbol_row['Country'].values[0]
#         company_info['Sector'] = symbol_row['Sector'].values[0]
#         company_info['Industry'] = symbol_row['Industry'].values[0]
#     else:
#         company_info['Company Name'] = 'N/A'
#         company_info['Country'] = 'N/A'
#         company_info['Sector'] = 'N/A'
#         company_info['Industry'] = 'N/A'
#
#     return company_info
#
# # Stock Growth Functions
# def get_last_eps(symbol):
#     try:
#         stock = yf.Ticker(symbol)
#         inc_stm = stock.get_income_stmt()
#         eps = []
#         row_name = 'DilutedEPS'
#
#         # Iterate through the columns and extract 'DilutedEPS' values
#         for column in inc_stm.columns:
#             value = inc_stm.loc[row_name, column]
#             eps.append(value)
#
#         # Create a DataFrame from the list
#         eps_df = pd.DataFrame({'Year': inc_stm.columns, 'EPS': eps})
#
#         # Format the 'Year' column to %Y
#         eps_df['Year'] = pd.to_datetime(eps_df['Year']).dt.strftime('%Y')
#         eps_df['Year'] = eps_df['Year'].astype('int64')
#
#         return eps_df
#
#     except:
#         return None
#
# def get_eps(symbol):
#     try:
#         stock = yf.Ticker(symbol)
#         try:
#             eps = stock.info['trailingEps']
#         except:
#             inc_stm = stock.income_stmt
#             eps = inc_stm.loc['Diluted EPS', :].iloc[0]
#         return eps
#     except:
#         return None
#
# def get_3years_av_eps(symbol):
#     try:
#         stock = yf.Ticker(symbol)
#         inc_stm = get_last_eps(symbol)
#
#         # Create an empty list to store the 'EPS' values
#         last_years_eps = []
#
#         # Extract the 'EPS' column from the DataFrame 'inc_stm'
#         eps_column = inc_stm['EPS'].dropna().head(3).tolist()
#
#         # Iterate through the 'EPS' values and append them to the list
#         for eps in eps_column:
#             last_years_eps.append(eps)
#
#         # Calculate the average DilutedEPS over the last 3 years
#         av_eps = round(sum(last_years_eps) / len(last_years_eps), 2)
#
#         return av_eps
#     except:
#           try:
#             stock = yf.Ticker(symbol)
#             inc_stm = get_last_eps(symbol)
#
#             # Create an empty list to store the 'EPS' values
#             last_years_eps = []
#
#             # Extract the 'EPS' column from the DataFrame 'inc_stm'
#             eps_column = inc_stm['EPS'].dropna().head(3).tolist()
#
#             # Iterate through the 'EPS' values and append them to the list
#             for eps in eps_column:
#                 last_years_eps.append(eps)
#
#             # Calculate the average DilutedEPS over the last 3 years
#             av_eps = round(sum(last_years_eps) / len(last_years_eps), 2)
#             return av_eps
#           except:
#             return None
#
# def get_yearly_eps(symbol):
#     try:
#       stock= yf.Ticker(symbol)
#       eps = pd.DataFrame(stock.get_earnings_dates(limit=100)['Reported EPS'])
#       eps = eps.dropna(subset=['Reported EPS'])
#       eps.index = pd.to_datetime(eps.index)
#       eps['Year'] = eps.index.year
#       yearly_eps = eps.groupby('Year')['Reported EPS'].sum().reset_index()
#       result = yearly_eps.sort_values(by='Year', ascending=False).head(10)
#
#       result.reset_index(drop=True, inplace=True)
#
#       # Convert 'Year' column to the same data type (object) in both DataFrames
#
#       result['Year'] = result['Year'].astype(object)
#
#       return result
#     except:
#       return None
#
# def is_historical_reliable(symbol):
#   try:
#     eps_from_inc = get_last_eps(symbol)
#     eps_from_inc['Year'] = eps_from_inc['Year'].astype(object)
#
#     result = get_yearly_eps(symbol)
#
#     # # Convert DataFrames to dictionaries
#     eps_from_inc_dict = dict(zip(eps_from_inc['Year'], eps_from_inc['EPS']))
#     result_dict = dict(zip(result['Year'], result['Reported EPS']))
#
#     # Calculate Percentage Difference for common years
#     common_years = set(eps_from_inc_dict.keys()) & set(result_dict.keys())
#     pct_diff = {}
#     eps_inc = 0
#     eps_result = 0
#
#
#     for year in common_years:
#       eps_inc += eps_from_inc_dict[year]
#       eps_result +=result_dict[year]
#
#     pct_diff = math.ceil(eps_inc/eps_result*100)
#
#     if pct_diff >= 90 and pct_diff <= 110:
#       return True
#   except:
#     return False
#
# def get_yearly_growth(symbol):
#     try:
#       if is_historical_reliable(symbol):
#         result = get_yearly_eps(symbol)
#         for i in range(len(result)-1,0,-1):
#           start = result.at[i, 'Reported EPS']
#           end = result.at[i-1, 'Reported EPS']
#           if start <0 and end <0:
#             result.at[i-1, 'Growth'] = round((end / start-1)*-1,2)
#           else:
#             result.at[i-1, 'Growth'] = round(end / start-1,2)
#         return result
#       else:
#         result=get_last_eps(symbol)
#         for i in range(len(result)-1,0,-1):
#           start = result.at[i, 'EPS']
#           end = result.at[i-1, 'EPS']
#           if start <0 and end <0:
#             result.at[i-1, 'Growth'] = round((end / start-1)*-1,2)
#           elif start < 0 and end >0:
#             result.at[i-1, 'Growth'] = round((end / start-1)*-1,2)
#           else:
#             result.at[i-1, 'Growth'] = round(end / start-1,2)
#         return result
#     except:
#       return None
#
# def calculate_eps_growth(result_df):
#   av_eps_growth = round(result_df['Growth'].mean(),2)
#   return av_eps_growth
#
# def calculate_median_eps_growth(result_df):
#   median_eps_growth = round(result_df['Growth'].median(),2)
#   return median_eps_growth
#
# def get_last_growth(symbol):
#   try:
#     last_growth = get_yearly_growth(symbol).iloc[0]['Growth']
#     if np.isnan(last_growth):
#       last_growth = get_yearly_growth(symbol).iloc[1]['Growth']
#     return last_growth
#   except:
#     return None
#
# def get_years_of_data(symbol):
#     try:
#       y = len(get_yearly_growth(symbol))
#       return y
#     except:
#       return None
#
# #STock Health Functions
#
# def get_debt(symbol):
#     try:
#       stock = yf.Ticker(symbol)
#       bs = stock.quarterly_balance_sheet.iloc[:, 0]
#       try:
#         debt = bs['Total Debt']
#       except:
#         debt = 0
#
#       return debt
#     except:
#       return  None
#
# def debt_to_equity_ratio(symbol):
#   try:
#     stock = yf.Ticker(symbol)
#     debts = get_debt(symbol)
#     # print(debts)
#     bs = stock.quarterly_balance_sheet.iloc[:, 0]
#     # print(bs['Total Equity Gross Minority Interest'])
#     if debts != 0:
#       der = round(debts/bs['Total Equity Gross Minority Interest'],2)
#     else:
#       der = 0
#     return der
#   except:
#     return  None
#
# def get_nwc(symbol):
#   try:
#     stock = yf.Ticker(symbol)
#     bs = stock.quarterly_balance_sheet.iloc[:, 0]
#     try:
#       current_assets = bs['Current Assets']
#     except:
#       try:
#         current_assets = bs['Cash And Cash Equivalents']
#       except:
#         current_assets = 0
#     try:
#       current_liabilities = bs['Current Liabilities']
#     except:
#       current_liabilities = 0
#
#     nwc = current_assets-current_liabilities
#     nwc_per_share = round(nwc/bs['Share Issued'],2)
#
#     return nwc_per_share
#   except:
#     return None
#
# def get_fcf(symbol):
#   try:
#     stock = yf.Ticker(symbol)
#     cf = stock.quarterly_cashflow.iloc[:, 0]
#     fcf = cf['Free Cash Flow']
#
#     return fcf
#   except:
#     None
#
# def get_roe(symbol):
#   try:
#     stock = yf.Ticker(symbol)
#     bs = stock.balance_sheet.iloc[:, 0]['Total Equity Gross Minority Interest']
#
#     ist = stock.income_stmt.iloc[:, 0]['Net Income']
#     roe = round(ist/bs,2)
#     return roe
#   except:
#     return None
#
# def custom_ranking(symbol):
#   try:
#       #stock Info
#       stock_info = get_company_info(symbol)
#       industry = stock_info['Industry']
#       sector = stock_info['Sector']
#       name = stock_info['Company Name']
#       y = get_years_of_data(symbol)
#
#       sector_df = pd.read_csv(f'/content/drive/MyDrive/Colab files/{sector}_stocks_growth.csv')
#       stock_growth_stat = sector_df[sector_df['Symbol'] == symbol]
#       sector_health_df = pd.read_csv(f'/content/drive/MyDrive/Colab files/{sector}_financial_data.csv')
#       stock_health_stat = sector_health_df[sector_health_df['Symbol'] == symbol]
#
#       #Value for investors:
#       past_years_average = stock_growth_stat ['3 years av'].values[0]
#       last_eps = stock_growth_stat ['Last EPS'].values[0]
#       industries_stats = calculate_industry_growth(sector)
#       industry_stats = industries_stats[industries_stats['Industry'] == industry]
#       if industry_stats['Number of companie'].values[0] > 10:
#         delta_eps = (past_years_average - industry_stats['3 years average'].values[0])
#       else:
#         sector_statistics = calculate_sector_growth(sector)
#         delta_eps = (past_years_average-sector_statistics['3 Years average EPS'])
#
#       value_eps = (past_years_average+delta_eps)*0.8+last_eps*0.2
#
#       industries_health_stats = calculate_industry_health(sector)
#       indus_health_stats = industries_health_stats[industries_health_stats['Industry']== industry]
#       roe = stock_health_stat['ROE'].values[0]
#       if industry_stats['Number of companie'].values[0] > 10:
#         delta_roe = (roe-indus_health_stats['Median ROE'].values[0])
#       else:
#         sector_health_stats = calculate_sector_health(sector)
#         delta_roe = (roe-sector_health_stats['Median ROE'])
#
#       value_eps = (past_years_average + delta_eps) * 0.7 + last_eps * 0.3
#       value_roe = roe + delta_roe
#       total_value = value_eps * 0.7 + value_roe * 0.3
#
#       #Growth:
#       sector_df['Growth percentile'] =  sector_df.groupby('Industry')['EPS average Growth'].rank(pct=True)
#       sector_df['Total Growth percentile'] =  sector_df['EPS average Growth'].rank(pct=True)
#       growth_percentile_by_indus = sector_df[sector_df['Symbol']==symbol]['Growth percentile'].values[0]
#       growth_percentile = sector_df[sector_df['Symbol']==symbol]['Total Growth percentile'].values[0]
#       sector_df['Last Growth percentile'] =  sector_df.groupby('Industry')['Last Growth'].rank(pct=True)
#       sector_df['Total last Growth percentile'] =  sector_df['Last Growth'].rank(pct=True)
#       last_growth_percentile_by_indus = sector_df[sector_df['Symbol']==symbol]['Last Growth percentile'].values[0]
#       last_growth_percentile = sector_df[sector_df['Symbol']==symbol]['Total last Growth percentile'].values[0]
#
#       if industry_stats['Number of companie'].values[0] > 10:
#         value_growth = last_growth_percentile_by_indus*0.25+last_growth_percentile*0.25+growth_percentile_by_indus*0.25 + growth_percentile*0.25
#       else:
#         value_growth = last_growth_percentile*0.5 + growth_percentile*0.5
#
#
#       #risk:
#       sector_health_df['NWC percentile'] = sector_health_df.groupby('Industry')['NWC per share'].rank(pct=True)
#       sector_health_df['DER percentile'] = sector_health_df.groupby('Industry')['Debt to Equity'].rank(pct=True)
#       nwc_percetile = sector_health_df[sector_health_df['Symbol']==symbol]['NWC percentile'].values[0]
#       der_percetile = 1 - sector_health_df[sector_health_df['Symbol']==symbol]['DER percentile'].values[0]
#
#       risk_ratio = (nwc_percetile*0.5 + der_percetile*0.5)
#
#       composite_score =(total_value*4*value_growth*risk_ratio
#       )
#       composite_score = round(composite_score,1)
#
#       # print(total_value)
#       # print(value_growth)
#       # print(risk_ratio)
#       return composite_score
#   except:
#       return None
#
# def is_outperformer(symbol):
#
#   stock_info = get_company_info(symbol)
#   industry = stock_info['Industry']
#   sector = stock_info['Sector']
#   sector_df = pd.read_csv(f'/content/drive/MyDrive/Colab files/{sector}_stocks_growth.csv')
#   stock_growth_stat = sector_df[sector_df['Symbol'] == symbol]
#   industries_stats = calculate_industry_growth(sector)
#   industry_stats = industries_stats[industries_stats['Industry'] == industry]
#
#   if industry_stats['Number of companie'].values[0] > 10:
#       industry_df = sector_df[sector_df['Industry'] == industry]
#       industry_df.replace([np.inf, -np.inf], np.nan, inplace=True)
#
#       # Select the 'EPS average Growth' column and drop NaN values
#       eps_growth_data = industry_df['EPS average Growth'].dropna()
#
#   else:
#
#       sector_df.replace([np.inf, -np.inf], np.nan, inplace=True)
#   # Select the 'EPS average Growth' column and drop NaN values
#   eps_growth_data = sector_df['EPS average Growth'].dropna()
#
#   # Calculate the IQR (Interquartile Range)
#   Q1 = eps_growth_data.quantile(0.25)
#   Q3 = eps_growth_data.quantile(0.75)
#   IQR = Q3 - Q1
#
#   # Define the lower and upper bounds to identify outliers
#   lower_bound = Q1 - 1.5 * IQR
#   upper_bound = Q3 + 1.5 * IQR
#
#   # Filter the data to remove outliers
#   filtered_eps_growth_data = eps_growth_data[(eps_growth_data >= lower_bound) & (eps_growth_data <= upper_bound)]
#
#   # Calculate the standard deviation on the filtered data
#   standard_deviation = filtered_eps_growth_data.std()
#
#   mean = filtered_eps_growth_data.mean()
#   min_value = filtered_eps_growth_data.mean() - standard_deviation
#   max_value = filtered_eps_growth_data.mean() + standard_deviation
#
#   growth = stock_growth_stat ['EPS average Growth'].values[0]
#
#   if growth > max_value:
#     return 'Outperfomer'
#   if growth < min_value:
#     return 'Underperformer'
#   else:
#     return 'Regular growth'
