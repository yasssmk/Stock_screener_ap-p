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


def create_stock_data_db(stock_list):
    symbols = stock_list['Symbol'].tolist()
    nbr_stock = len(symbols)
    done = 0

    data = {
        'Company Name': [],
        'Symbol': [],
        'Country': [],
        'Sector': [],
        'Industry': [],
        'Last EPS': [],
        '3 years av': [],
        'Last Growth': [],
        'EPS average Growth': [],
        'EPS median Growth': [],
        'Years of Data': [],
        'Debt to Equity': [],
        'NWC per share': [],
        'ROE': [],
        'Free Cash Flow': []
    }

    for symbol in symbols:
        try:
            #print(symbol)
            company_info = utils.Stock_Data.get_company_info(symbol)
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
            fcf = utils.Stock_Data.get_fcf(symbol)

            if years_data >= 3:
                data['Company Name'].append(company_info['Company Name'])
                data['Symbol'].append(symbol)
                data['Country'].append(company_info['Country'])
                data['Sector'].append(company_info['Sector'])
                data['Industry'].append(company_info['Industry'])
                data['Last EPS'].append(last_eps)
                data['3 years av'].append(av_eps)
                data['Last Growth'].append(last_growth)
                data['EPS average Growth'].append(eps_growth)
                data['EPS median Growth'].append(median_eps_growth)
                data['Years of Data'].append(years_data)
                data['Debt to Equity'].append(dte)
                data['NWC per share'].append(nwc)
                data['ROE'].append(roe)
                data['Free Cash Flow'].append(fcf)

        except Exception as e:
            utils.Errors_logging.functions_error_log("create_stock_data_db", e, utils.Errors_logging.log_name_rundb, symbol=symbol)
            continue

        #done += 1
        #progress = (done / nbr_stock) * 100  # Recalculate avancement
        #pct_avc = math.ceil(progress)  # Update pct_avc
        #print(f'{done} sur {nbr_stock} : {pct_avc}%')

    df = pd.DataFrame(data)

    file_path = "./stocks_data_csv/data_base/Data_Base.csv"

    try:
        # Save the DataFrame to a CSV file
        df.to_csv(file_path, index=False)# Set index to False if you don't want to save the row numbers
        #print(f'CSV file saved to {file_path}')
    except Exception as e:
        utils.Errors_logging.functions_error_log("create_stock_data_db", e, utils.Errors_logging.log_name_rundb)
        #print(f'Error: {e}')

    return df


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
    df = pd.read_csv("./stocks_data_csv/data_base/Data_Base.csv")
    technologies = df['Industry'].dropna().unique().tolist()
    industry_stats = {
        'Sector': [],
        'Industry': [],
        'Average Last EPS': [],
        'Average 3 years EPS': [],
        'Average Last Growth': [],
        'Average EPS Growth': [],
        'Average EPS median Growth': [],
        'Average Debt to Equity': [],
        'Average NWC per share': [],
        'Average ROE': [],
        'Average Free Cash Flow': [],
        'Number of companies': []
    }

    for techno in technologies:
        numbers_company = len(df[df['Industry'] == techno])
        sector = df[df['Industry'] == techno]['Sector'].iloc[0]

        if numbers_company > 5:
            techno_eps = df[df['Industry'] == techno]['Last EPS']
            techno_eps = remove_outliers(techno_eps)
            three_years = df[df['Industry'] == techno]['3 years av']
            three_years = pd.to_numeric(three_years, errors='coerce')
            three_years = remove_outliers(three_years)
            last_growth = df[df['Industry'] == techno]['Last Growth']
            last_growth = pd.to_numeric(last_growth, errors='coerce')
            last_growth = remove_outliers(last_growth)
            techno_eps_growth = df[df['Industry'] == techno]['EPS average Growth']
            techno_eps_growth = pd.to_numeric(techno_eps_growth, errors='coerce')
            techno_eps_growth = remove_outliers(techno_eps_growth)
            techno_eps_median_growth = df[df['Industry'] == techno]['EPS median Growth']
            techno_eps_median_growth = pd.to_numeric(techno_eps_median_growth, errors='coerce')
            techno_eps_median_growth = remove_outliers(techno_eps_median_growth)
            der = df[df['Industry'] == techno]['Debt to Equity']
            der = pd.to_numeric(der, errors='coerce')
            der = remove_outliers(der)
            nwc = df[df['Industry'] == techno]['NWC per share']
            nwc = pd.to_numeric(nwc, errors='coerce')
            nwc = remove_outliers(nwc)
            roe = df[df['Industry'] == techno]['ROE']
            roe = pd.to_numeric(roe, errors='coerce')
            roe = remove_outliers(roe)
            fcf = df[df['Industry'] == techno]['Free Cash Flow']
            fcf = pd.to_numeric(fcf, errors='coerce')
            fcf = remove_outliers(fcf)
        else:
            techno_eps = df[df['Industry'] == techno]['Last EPS']
            three_years = df[df['Industry'] == techno]['3 years av']
            three_years = pd.to_numeric(three_years, errors='coerce')
            last_growth = df[df['Industry'] == techno]['Last Growth']
            last_growth = pd.to_numeric(last_growth, errors='coerce')
            techno_eps_growth = df[df['Industry'] == techno]['EPS average Growth']
            techno_eps_growth = pd.to_numeric(techno_eps_growth, errors='coerce')
            techno_eps_median_growth = df[df['Industry'] == techno]['EPS median Growth']
            techno_eps_median_growth = pd.to_numeric(techno_eps_median_growth, errors='coerce')
            der = df[df['Industry'] == techno]['Debt to Equity']
            der = pd.to_numeric(der, errors='coerce')
            nwc = df[df['Industry'] == techno]['NWC per share']
            nwc = pd.to_numeric(nwc, errors='coerce')
            roe = df[df['Industry'] == techno]['ROE']
            roe = pd.to_numeric(roe, errors='coerce')
            fcf = df[df['Industry'] == techno]['Free Cash Flow']
            fcf = pd.to_numeric(fcf, errors='coerce')



        average_techno_eps = round(techno_eps.mean(), 1)
        three_years_average = round(three_years.mean(), 1)
        average_last_growth = round(last_growth.mean(), 1)
        average_techno_eps_growth = round(techno_eps_growth.mean(), 1)
        average_techno_eps_median_growth = round(techno_eps_median_growth.mean(), 1)
        average_der = round(der.mean(), 1)
        average_nwc = round(nwc.mean(), 1)
        average_roe = round(roe.mean(), 1)
        average_fcf = round(fcf.mean(), 1)

        industry_stats['Sector'].append(sector)
        industry_stats['Industry'].append(techno)
        industry_stats['Average Last EPS'].append(average_techno_eps)
        industry_stats['Average 3 years EPS'].append(three_years_average)
        industry_stats['Average Last Growth'].append(average_last_growth)
        industry_stats['Average EPS Growth'].append(average_techno_eps_growth)
        industry_stats['Average EPS median Growth'].append(average_techno_eps_median_growth)
        industry_stats['Average Debt to Equity'].append(average_der)
        industry_stats['Average NWC per share'].append(average_nwc)
        industry_stats['Average ROE'].append(average_roe)
        industry_stats['Average Free Cash Flow'].append(average_fcf)
        industry_stats['Number of companies'].append(numbers_company)

    file_path = "./stocks_data_csv/data_base/Industry_stat_data_base.csv"

    try:
        industry_stats_df = pd.DataFrame(industry_stats)
        industry_stats_df.to_csv(file_path, index=False)
        #print(f'CSV file saved to {file_path}')
    except Exception as e:
        utils.Errors_logging.functions_error_log("calculate_industry_stat", e, utils.Errors_logging.log_name_rundb)
        #print(f'Error: {e}')

    return industry_stats_df


def calculate_sector_stat():
    df = pd.read_csv("./stocks_data_csv/data_base/Data_Base.csv")
    sectors = df['Sector'].dropna().unique().tolist()

    sector_stats = {
        'Sector': [],
        'Average Last EPS': [],
        'Average 3 years EPS': [],
        'Average Last Growth': [],
        'Average EPS Growth': [],
        'Average EPS median Growth': [],
        'Average Debt to Equity': [],
        'Average NWC per share': [],
        'Average ROE': [],
        'Average Free Cash Flow': [],
        'Number of companies': []
    }

    for sector in sectors:
        sector_df = df[df['Sector'] == sector]
        numbers_company = len(sector_df)

        if numbers_company > 5:
            techno_eps = sector_df['Last EPS']
            techno_eps = remove_outliers(techno_eps)
            three_years = sector_df['3 years av']
            three_years = pd.to_numeric(three_years, errors='coerce')
            three_years = remove_outliers(three_years)
            last_growth = sector_df['Last Growth']
            last_growth = pd.to_numeric(last_growth, errors='coerce')
            last_growth = remove_outliers(last_growth)
            eps_growth = sector_df['EPS average Growth']
            eps_growth = pd.to_numeric(eps_growth, errors='coerce')
            eps_growth = remove_outliers(eps_growth)
            eps_median_growth = sector_df['EPS median Growth']
            eps_median_growth = pd.to_numeric(eps_median_growth, errors='coerce')
            eps_median_growth = remove_outliers(eps_median_growth)
            der = sector_df['Debt to Equity']
            der = pd.to_numeric(der, errors='coerce')
            der = remove_outliers(der)
            nwc = sector_df['NWC per share']
            nwc = pd.to_numeric(nwc, errors='coerce')
            nwc = remove_outliers(nwc)
            roe = sector_df['ROE']
            roe = pd.to_numeric(roe, errors='coerce')
            roe = remove_outliers(roe)
            fcf = sector_df['Free Cash Flow']
            fcf = pd.to_numeric(fcf, errors='coerce')
            fcf = remove_outliers(fcf)

            # Repeat for other columns

        else:
            techno_eps = sector_df['Last EPS']
            three_years = sector_df['3 years av']
            three_years = pd.to_numeric(three_years, errors='coerce')
            last_growth = sector_df['Last Growth']
            last_growth = pd.to_numeric(last_growth, errors='coerce')
            eps_growth = sector_df['EPS average Growth']
            eps_growth = pd.to_numeric(eps_growth, errors='coerce')
            eps_median_growth = sector_df['EPS median Growth']
            eps_median_growth = pd.to_numeric(eps_median_growth, errors='coerce')
            der = sector_df['Debt to Equity']
            der = pd.to_numeric(der, errors='coerce')
            nwc = sector_df['NWC per share']
            nwc = pd.to_numeric(nwc, errors='coerce')
            roe = sector_df['ROE']
            roe = pd.to_numeric(roe, errors='coerce')
            fcf = sector_df['Free Cash Flow']
            fcf = pd.to_numeric(fcf, errors='coerce')



        average_techno_eps = round(techno_eps.mean(), 1)
        three_years_average = round(three_years.mean(), 1)
        average_last_growth = round(last_growth.mean(), 1)
        average_eps_growth= round(eps_growth.mean(), 1)
        average_eps_median_growth = round(eps_median_growth.mean(), 1)
        average_der = round(der.mean(), 1)
        average_nwc = round(nwc.mean(), 1)
        average_roe = round(roe.mean(), 1)
        average_fcf = round(fcf.mean(), 1)

        # Repeat for other columns

        sector_stats['Sector'].append(sector)
        sector_stats['Average Last EPS'].append(average_techno_eps)
        sector_stats['Average 3 years EPS'].append(three_years_average)
        sector_stats['Average Last Growth'].append(average_last_growth)
        sector_stats['Average EPS Growth'].append(average_eps_growth)
        sector_stats['Average EPS median Growth'].append(average_eps_median_growth)
        sector_stats['Average Debt to Equity'].append(average_der)
        sector_stats['Average NWC per share'].append(average_nwc)
        sector_stats['Average ROE'].append(average_roe)
        sector_stats['Average Free Cash Flow'].append(average_fcf)

        # Repeat for other columns

        sector_stats['Number of companies'].append(numbers_company)

    file_path = "./stocks_data_csv/data_base/Sector_stat_data_base.csv"

    try:
        sector_stats_df = pd.DataFrame(sector_stats)
        sector_stats_df.to_csv(file_path, index=False)
        #print(f'CSV file saved to {file_path}')
    except Exception as e:
        utils.Errors_logging.functions_error_log("calculate_sector_stat", e, utils.Errors_logging.log_name_rundb)

    return sector_stats_df


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

