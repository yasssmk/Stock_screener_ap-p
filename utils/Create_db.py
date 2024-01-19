import pandas as pd
import sqlite3
from sqlite3 import connect
import csv
import numpy as np
import random
import yfinance as yf
from datetime import datetime, timedelta, date
#import ta
import os
#import matplotlib.pyplot as plt
import math
from scipy import stats
import utils.Stock_Data
import utils.Sending_Email
import utils.Errors_logging
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client


def create_stock_data_db():
    load_dotenv()
    url: str = os.getenv('sb_url')
    key: str = os.getenv('sb_api_key')  # Replace with your Supabase API key
    supabase: Client = create_client(url, key)

    response = supabase.table('stocks_list').select("Stock_id", "Symbol").execute()
    symbols_data = response.data

    # nbr_stock = len(symbols_data)
    # done = 0

    for data in symbols_data:
        symbol = data["Symbol"]
        stock_id = data["Stock_id"]
        try:
            # print(symbol)
            last_eps = utils.Stock_Data.get_eps(symbol)
            av_eps = utils.Stock_Data.get_3years_av_eps(symbol)
            result_df = utils.Stock_Data.get_yearly_growth(symbol)
            eps_growth = utils.Stock_Data.calculate_eps_growth(result_df)
            median_eps_growth = utils.Stock_Data.calculate_median_eps_growth(result_df)
            years_data = utils.Stock_Data.get_years_of_data(symbol)
            last_growth = utils.Stock_Data.get_last_growth(symbol)
            dte = utils.Stock_Data.debt_to_equity_ratio(symbol)
            nwc = utils.Stock_Data.get_nwc(symbol)
            roe = utils.Stock_Data.get_roe(symbol)

            insert_data = {
                'Stock_id': stock_id,
                'Symbol': symbol,
                'Last EPS': last_eps,
                '3 years av': av_eps,
                'Last Growth': last_growth,
                'EPS average Growth': eps_growth,
                'EPS median Growth': median_eps_growth,
                'Years of Data': years_data,
                'Debt to Equity': dte,
                'NWC per share': nwc,
                'ROE': roe,
            }

            check_response = supabase.table('data_stocks').select("*").eq('Stock_id', stock_id).execute()
            try:
                if check_response.data:
                    # Update the existing record
                    supabase.table('data_stocks').update(insert_data).eq('Stock_id', stock_id).execute()
                else:
                    # Insert a new record
                    supabase.table('data_stocks').insert(insert_data).execute()
            except Exception as e:
                utils.Errors_logging.functions_error_log("create_stock_data_db", e,utils.Errors_logging.log_name_rundb, symbol=symbol)
                continue


        except Exception as e:
            utils.Errors_logging.functions_error_log("create_stock_data_db", e, utils.Errors_logging.log_name_rundb, symbol=symbol)
            continue

        # done += 1
        # progress = (done / nbr_stock) * 100  # Recalculate avancement
        # pct_avc = math.ceil(progress)  # Update pct_avc
        # print(f'{done} sur {nbr_stock} : {pct_avc}%')

def remove_outliers(data):
    try:
        valid_data = data.replace([np.inf, -np.inf], np.nan).dropna()
        z_scores = stats.zscore(valid_data)

        # Create a mask to filter out outliers
        mask = np.abs(z_scores) < 3  # Adjust the threshold as needed

        # Apply the mask to the original data
        filtered_data = data[valid_data.index][mask]

        return filtered_data
    except Exception as e:
        utils.Errors_logging.functions_error_log("remove_outliers", e, utils.Errors_logging.log_name_rundb)

def calculate_industry_stat():
    load_dotenv()
    url: str = os.getenv('sb_url')
    key: str = os.getenv('sb_api_key')  # Replace with your Supabase API key
    supabase: Client = create_client(url, key)

    fin_response = supabase.table('data_stocks').select("*").execute()
    fin_data = fin_response.data
    stock_response = supabase.table('stocks_list').select("Stock_id", "Industry", "Sector").execute()
    stock_data = stock_response.data

    def calculate_mean(data, number_of_companies):
        if number_of_companies > 5:
            # Remove outliers and then calculate mean
            return round(utils.Create_db.remove_outliers(data).mean(), 1)
        else:
            # Directly calculate mean
            return round(data.mean(), 1)
    try:
        joined_data = []
        for fin_item in fin_data:
            stock_id = fin_item['Stock_id']
            stock_item = next((item for item in stock_data if item['Stock_id'] == stock_id), None)
            if stock_item:
                joined_item = {**fin_item, **stock_item}
                joined_data.append(joined_item)

        # Assuming 'joined_data' is a list of dictionaries as before
        df = pd.DataFrame(joined_data)

        # Group by 'Industry' and aggregate data
        industry_financials = df.groupby('Industry').agg({
            'Sector': 'first',
            'Stock_id': 'count',
            # Other columns are aggregated into lists for further processing
            'Last EPS': list,
            '3 years av': list,
            'Last Growth': list,
            'EPS average Growth': list,
            'EPS median Growth': list,
            'Debt to Equity': list,
            'NWC per share': list,
            'ROE': list
        }).reset_index()

        # Apply the logic for mean calculation
        for index, row in industry_financials.iterrows():
            number_of_companies = row['Stock_id']
            for col in ['Last EPS', '3 years av', 'Last Growth', 'EPS average Growth', 'EPS median Growth', 'Debt to Equity', 'NWC per share', 'ROE']:
                data_series = pd.Series(row[col])
                industry_financials.at[index, col] = calculate_mean(data_series, number_of_companies)

        # Renaming 'Stock_id' column to 'Number of Companies'
        industry_financials.rename(columns={'Stock_id': 'Number of Companies'}, inplace=True)

        # Convert the DataFrame to a list of dictionaries if needed
        industries_list = industry_financials.to_dict(orient='records')

        for i in industries_list:
            industry = i["Industry"]
            check_response = supabase.table('industries_fin_data').select("*").eq('Industry',industry).execute()

            try:
                # Update existing record
                if check_response.data:
                    update_response = supabase.table('industries_fin_data').update(i).eq('Industry',industry).execute()

                    # Insert new record
                else:
                    insert_response = supabase.table('industries_fin_data').insert(i).execute()
            except Exception as e:
                utils.Errors_logging.functions_error_log("calculate_industry_stat update db", e,
                                                         utils.Errors_logging.log_name_rundb)

    except Exception as e:
        utils.Errors_logging.functions_error_log("calculate_industry_stat", e, utils.Errors_logging.log_name_rundb)


def calculate_sector_stat():
    load_dotenv()
    url: str = os.getenv('sb_url')
    key: str = os.getenv('sb_api_key')  # Replace with your Supabase API key
    supabase: Client = create_client(url, key)

    fin_response = supabase.table('data_stocks').select("*").execute()
    fin_data = fin_response.data
    stock_response = supabase.table('stocks_list').select("Stock_id", "Sector").execute()
    stock_data = stock_response.data

    def calculate_mean(data, number_of_companies):
        if number_of_companies > 5:
            # Remove outliers and then calculate mean
            return round(utils.Create_db.remove_outliers(data).mean(), 1)
        else:
            # Directly calculate mean
            return round(data.mean(), 1)

    try:
        joined_data = []
        for fin_item in fin_data:
            stock_id = fin_item['Stock_id']
            stock_item = next((item for item in stock_data if item['Stock_id'] == stock_id), None)
            if stock_item:
                joined_item = {**fin_item, **stock_item}
                joined_data.append(joined_item)

        # Assuming 'joined_data' is a list of dictionaries as before
        df = pd.DataFrame(joined_data)

        # Group by 'Industry' and aggregate data
        sector_financials = df.groupby('Sector').agg({
            'Stock_id': 'count',
            # Other columns are aggregated into lists for further processing
            'Last EPS': list,
            '3 years av': list,
            'Last Growth': list,
            'EPS average Growth': list,
            'EPS median Growth': list,
            'Debt to Equity': list,
            'NWC per share': list,
            'ROE': list
        }).reset_index()

        # Apply the logic for mean calculation
        for index, row in sector_financials.iterrows():
            number_of_companies = row['Stock_id']
            for col in ['Last EPS', '3 years av', 'Last Growth', 'EPS average Growth', 'EPS median Growth',
                        'Debt to Equity', 'NWC per share', 'ROE']:
                data_series = pd.Series(row[col])
                sector_financials.at[index, col] = calculate_mean(data_series, number_of_companies)

        # Renaming 'Stock_id' column to 'Number of Companies'
        sector_financials.rename(columns={'Stock_id': 'Number of Companies'}, inplace=True)

        # Convert the DataFrame to a list of dictionaries if needed
        sectors_list = sector_financials.to_dict(orient='records')

        for i in sectors_list:
            sector = i["Sector"]
            check_response = supabase.table('sectors_fin_data').select("*").eq('Sector', sector).execute()

            try:
                # Update existing record
                if check_response.data:
                    update_response = supabase.table('sectors_fin_data').update(i).eq('Sector', sector).execute()

                    # Insert new record
                else:
                    insert_response = supabase.table('sectors_fin_data').insert(i).execute()
            except Exception as e:
                utils.Errors_logging.functions_error_log("calculate_sector_stat", e,
                                                         utils.Errors_logging.log_name_rundb)

    except Exception as e:
        utils.Errors_logging.functions_error_log("calculate_sector_stat", e, utils.Errors_logging.log_name_rundb)


def add_percentile(dataframe):
    try:
        dataframe['Growth percentile'] = dataframe.groupby('Industry')['EPS average Growth'].rank(
            pct=True)
        dataframe['Total Growth percentile'] = dataframe.groupby('Sector')['EPS average Growth'].rank(pct=True)
        dataframe['Last Growth percentile'] = dataframe.groupby('Industry')['Last Growth'].rank(pct=True)
        dataframe['Total last Growth percentile'] = dataframe.groupby('Sector')['Last Growth'].rank(
            pct=True)

        dataframe['NWC percentile'] = dataframe.groupby('Industry')['NWC per share'].rank(pct=True)
        dataframe['DER percentile'] = dataframe.groupby('Industry')['Debt to Equity'].rank(pct=True)

        output_path = "./stocks_data_csv/data_base/Data_Base.csv"
        dataframe.to_csv(output_path, index=False)

    except Exception as e:
        utils.Errors_logging.functions_error_log("add_percentile", e, utils.Errors_logging.log_name_rundb)


def custom_ranking(symbol):
    try:
        all_stocks_stat_df = pd.read_csv("./stocks_data_csv/data_base/Data_Base.csv")
        stock_stat = all_stocks_stat_df[all_stocks_stat_df['Symbol'] == symbol]

        if stock_stat.empty:
            return None

        # Stock Info
        industry = stock_stat['Industry'].values[0]
        sector = stock_stat['Sector'].values[0]
        name = stock_stat['Company Name'].values[0]
        y = stock_stat['Years of Data'].values[0]

        # Industry data
        all_industry_data = pd.read_csv("./stocks_data_csv/data_base/Industry_stat_data_base.csv")
        industry_stats = all_industry_data[all_industry_data['Industry'] == industry]

        # Sector data
        all_sector_data = pd.read_csv("./stocks_data_csv/data_base/Sector_stat_data_base.csv")
        sector_statistics = all_sector_data[all_sector_data['Sector'] == sector]

        # Value for investors:
        past_years_average = stock_stat['3 years av'].values[0]
        last_eps = stock_stat['Last EPS'].values[0]
        if industry_stats['Number of companies'].values[0] > 10:
            delta_eps = (past_years_average - industry_stats['Average 3 years EPS'].values[0])
        else:
            delta_eps = (past_years_average - sector_statistics['Average 3 years EPS'].values[0])

        value_eps = (past_years_average + delta_eps) * 0.8 + last_eps * 0.2

        roe = stock_stat['ROE'].values[0]
        if industry_stats['Number of companies'].values[0] > 10:
            delta_roe = (roe - industry_stats['Average ROE'].values[0])
        else:
            delta_roe = (roe - sector_statistics['Average ROE'].values[0])

        value_eps = (past_years_average + delta_eps) * 0.7 + last_eps * 0.3
        value_roe = roe + delta_roe
        total_value = value_eps * 0.7 + value_roe * 0.3

        # Growth:
        # all_stocks_stat_df['Growth percentile'] = all_stocks_stat_df.groupby('Industry')['EPS average Growth'].rank(pct=True)
        # all_stocks_stat_df['Total Growth percentile'] = all_stocks_stat_df.groupby('Sector')['EPS average Growth'].rank(pct=True)
        growth_percentile_by_indus = all_stocks_stat_df[all_stocks_stat_df['Symbol'] == symbol]['Growth percentile'].values[0]
        growth_percentile = all_stocks_stat_df[all_stocks_stat_df['Symbol'] == symbol]['Total Growth percentile'].values[0]
        # all_stocks_stat_df['Last Growth percentile'] = all_stocks_stat_df.groupby('Industry')['Last Growth'].rank(pct=True)
        # all_stocks_stat_df['Total last Growth percentile'] = all_stocks_stat_df.groupby('Sector')['Last Growth'].rank(pct=True)
        last_growth_percentile_by_indus = all_stocks_stat_df[all_stocks_stat_df['Symbol'] == symbol]['Last Growth percentile'].values[0]
        last_growth_percentile = all_stocks_stat_df[all_stocks_stat_df['Symbol'] == symbol]['Total last Growth percentile'].values[0]

        if industry_stats['Number of companies'].values[0] > 10:
            value_growth = last_growth_percentile_by_indus * 0.25 + last_growth_percentile * 0.25 + growth_percentile_by_indus * 0.25 + growth_percentile * 0.25
        else:
            value_growth = last_growth_percentile * 0.5 + growth_percentile * 0.5

        # risk:
        # all_stocks_stat_df['NWC percentile'] = all_stocks_stat_df.groupby('Industry')['NWC per share'].rank(pct=True)
        # all_stocks_stat_df['DER percentile'] = all_stocks_stat_df.groupby('Industry')['Debt to Equity'].rank(pct=True)
        nwc_percentile = all_stocks_stat_df[all_stocks_stat_df['Symbol'] == symbol]['NWC percentile'].values[0]
        der_percentile = 1 - all_stocks_stat_df[all_stocks_stat_df['Symbol'] == symbol]['DER percentile'].values[0]

        risk_ratio = (nwc_percentile * 0.5 + der_percentile * 0.5)

        composite_score = (total_value * 4 * value_growth * risk_ratio
                           )
        composite_score = round(composite_score, 1)

        # print(total_value)
        # print(value_growth)
        # print(risk_ratio)
        return composite_score
    except Exception as e:
        utils.Errors_logging.functions_error_log("custom_ranking", e, utils.Errors_logging.log_name_rundb, symbol=symbol)
        return None

def is_outperformer(symbol):
    try:
        all_stocks_stat_df = pd.read_csv("./stocks_data_csv/data_base/Data_Base.csv")
        stock_stat = all_stocks_stat_df[all_stocks_stat_df['Symbol'] == symbol]

        # Stock Info
        industry = stock_stat['Industry'].values[0]
        sector = stock_stat['Sector'].values[0]
        name = stock_stat['Company Name'].values[0]
        y = stock_stat['Years of Data'].values[0]

        # Industry data
        all_industry_data = pd.read_csv("./stocks_data_csv/data_base/Industry_stat_data_base.csv")
        industry_stats = all_industry_data[all_industry_data['Industry'] == industry]

        # Sector data
        all_sector_data = pd.read_csv("./stocks_data_csv/data_base/Sector_stat_data_Bbse.csv")
        sector_statistics = all_sector_data[all_sector_data['Sector'] == sector]

        if industry_stats['Number of companies'].values[0] > 10:
            industry_df = all_stocks_stat_df[all_stocks_stat_df['Industry'] == industry].copy()
            industry_df.replace([np.inf, -np.inf], np.nan, inplace=True)
            # Select the 'EPS average Growth' column and drop NaN values
            eps_growth_data = industry_df['EPS average Growth'].dropna()
        else:
            sector_df = all_stocks_stat_df[all_stocks_stat_df['Sector'] == sector].copy()
            sector_df.replace([np.inf, -np.inf], np.nan, inplace=True)
            # Select the 'EPS average Growth' column and drop NaN values
            eps_growth_data = sector_df['EPS average Growth'].dropna()

        # Convert 'EPS average Growth' to numeric
        eps_growth_data = pd.to_numeric(eps_growth_data, errors='coerce')

        # Calculate the IQR (Interquartile Range)
        Q1 = eps_growth_data.quantile(0.25)
        Q3 = eps_growth_data.quantile(0.75)
        IQR = Q3 - Q1

        # Define the lower and upper bounds to identify outliers
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR

        # Filter the data to remove outliers
        filtered_eps_growth_data = eps_growth_data[(eps_growth_data >= lower_bound) & (eps_growth_data <= upper_bound)]

        # Calculate the standard deviation on the filtered data
        standard_deviation = filtered_eps_growth_data.std()

        mean = filtered_eps_growth_data.mean()
        min_value = filtered_eps_growth_data.mean() - standard_deviation
        max_value = filtered_eps_growth_data.mean() + standard_deviation

        # Convert 'growth' and 'max_value' to numeric
        growth = pd.to_numeric(stock_stat['EPS average Growth'].values[0], errors='coerce')
        max_value = pd.to_numeric(max_value, errors='coerce')

        if growth > max_value:
            return 'Outperformer'
        if growth < min_value:
            return 'Underperformer'
        else:
            return 'Regular growth'
    except Exception as e:
        utils.Errors_logging.functions_error_log("is_outperformer", e, utils.Errors_logging.log_name_rundb, symbol=symbol)

def update_databases(stock_list_path):
    try:
        # Read stock list
        stock_list = pd.read_csv(stock_list_path)
        # Create a stock data dataframe
        create_stock_data_db(stock_list)

        data_df = pd.read_csv("./stocks_data_csv/data_base/Data_Base.csv")

        # Calculate industry statistics
        industry_stats = calculate_industry_stat()

        # Calculate sector statistics
        sector_stats = calculate_sector_stat()

        # Add percentiles
        add_percentile(data_df)

        for index, row in data_df.iterrows():
            try:
                # Apply custom_ranking
                score = custom_ranking(row['Symbol'])
                if score is not None:
                    data_df.at[index, 'Score'] = score
                else:
                    data_df.at[index, 'Score'] = -100  # Default value in case of None

                # Apply is_outperformer
                performance = is_outperformer(row['Symbol'])
                if performance is not None:
                    data_df.at[index, 'Performance'] = performance
                else:
                    data_df.at[index, 'Performance'] = False  # Default value in case of None

            except Exception as e:
                symbol = row['Symbol']
                utils.Errors_logging.functions_error_log("update_databases", e, utils.Errors_logging.log_name_rundb, symbol=symbol)
                continue


        # Define file paths for saving data
        data_path = f"./stocks_data_csv/data_base/Data_Base.csv"
        industry_stats_path = f"./stocks_data_csv/data_base/Industry_stat_data_base.csv"
        sector_stats_path = f"./stocks_data_csv/data_base/Sector_stat_data_base.csv"

        # Save data to CSV files
        data_df.to_csv(data_path, index=False)
        industry_stats.to_csv(industry_stats_path, index=False)
        sector_stats.to_csv(sector_stats_path, index=False)

        error_log_path = './stocks_data_csv/errors_logs/Create_update_selection'
        utils.Sending_Email.job_done_email("Update Data Base", error_log_path)

    except Exception as e:
        utils.Errors_logging.functions_error_log("update_databases", e, utils.Errors_logging.log_name_rundb)
        error_log_path = './stocks_data_csv/errors_logs/Create_update_selection'
        utils.Sending_Email.db_error_email(e, "Data Base", error_log_path)

