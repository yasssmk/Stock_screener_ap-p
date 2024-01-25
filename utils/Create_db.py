import pandas as pd
import numpy as np
import os
from scipy import stats
import utils.Stock_Data
import utils.Sending_Email
import utils.Errors_logging
import utils.Stock_selection
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
url: str = os.getenv('sb_url')
key: str = os.getenv('sb_api_key')  # Replace with your Supabase API key
supabase: Client = create_client(url, key)

error_log_path = './errors_logs/update_db'

def create_stock_data_db():
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
                utils.Errors_logging.functions_error_log("create_stock_data_db - Update data_stock", e,utils.Errors_logging.log_name_rundb, symbol=symbol)
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

    fin_response = supabase.table('data_stocks').select("*").execute()
    fin_data = fin_response.data
    stock_response = supabase.table('stocks_list').select("Stock_id", "Industry", "Sector").execute()
    stock_data = stock_response.data

    def calculate_mean(data, number_of_companies):
        if number_of_companies > 5:
            # Remove outliers and then calculate mean
            return round(remove_outliers(data).mean(), 1)
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
                utils.Errors_logging.functions_error_log("calculate_sector_stat update db", e,
                                                         utils.Errors_logging.log_name_rundb)

    except Exception as e:
        utils.Errors_logging.functions_error_log("calculate_sector_stat", e, utils.Errors_logging.log_name_rundb)


def add_percentile():

    # Retrieve data from Supabase tables
    fin_response = supabase.table('data_stocks').select("*").execute()
    fin_data = fin_response.data
    stock_response = supabase.table('stocks_list').select("Stock_id", "Industry", "Sector").execute()
    stock_data = stock_response.data

    # Join data
    joined_data = []
    try:
        for fin_item in fin_data:
            stock_id = fin_item['Stock_id']
            stock_item = next((item for item in stock_data if item['Stock_id'] == stock_id), None)
            if stock_item:
                joined_item = {**fin_item, **stock_item}
                joined_data.append(joined_item)

        # Convert joined data to a DataFrame
        dataframe = pd.DataFrame(joined_data)

        # Calculate percentiles
        dataframe['Growth percentile'] = dataframe.groupby('Industry')['EPS average Growth'].rank(pct=True)
        dataframe['Total Growth percentile'] = dataframe.groupby('Sector')['EPS average Growth'].rank(pct=True)
        dataframe['Last Growth percentile'] = dataframe.groupby('Industry')['Last Growth'].rank(pct=True)
        dataframe['Total last Growth percentile'] = dataframe.groupby('Sector')['Last Growth'].rank(pct=True)
        dataframe['NWC percentile'] = dataframe.groupby('Industry')['NWC per share'].rank(pct=True)
        dataframe['DER percentile'] = dataframe.groupby('Industry')['Debt to Equity'].rank(pct=True)

        # Prepare data for insertion into 'stock_ranking' table
        percentile_data = dataframe[
            ['Stock_id', 'Symbol', 'Industry', 'Sector', 'Growth percentile', 'Total Growth percentile',
             'Last Growth percentile', 'Total last Growth percentile', 'NWC percentile', 'DER percentile']].copy()


        return percentile_data

    except Exception as e:
        utils.Errors_logging.functions_error_log("add_percentile", e, utils.Errors_logging.log_name_rundb)

def get_industries_data():
    try:
        # Retrieve data from Supabase tables
        fin_response = supabase.table('industries_fin_data').select("*").execute()
        fin_data = fin_response.data
        df = pd.DataFrame(fin_data)
        return df
    except Exception as e:
        utils.Errors_logging.functions_error_log("get_industries_data", e, utils.Errors_logging.log_name_rundb)

def get_sectors_data():
    try:
        # Retrieve data from Supabase tables
        fin_response = supabase.table('sectors_fin_data').select("*").execute()
        fin_data = fin_response.data
        df = pd.DataFrame(fin_data)
        return df
    except Exception as e:
        utils.Errors_logging.functions_error_log("get_sectors_data", e, utils.Errors_logging.log_name_rundb)

def get_stocks_data():
    try:
        # Retrieve data from Supabase tables
        fin_response = supabase.table('data_stocks').select("*").execute()
        fin_data = fin_response.data
        df = pd.DataFrame(fin_data)
        return df
    except Exception as e:
        utils.Errors_logging.functions_error_log("get_stocks_data", e, utils.Errors_logging.log_name_rundb)


def calculate_industry_outliers():
    try:
        fin_response = supabase.table('data_stocks').select("Stock_id", "EPS average Growth").execute()
        fin_data = fin_response.data
        stock_response = supabase.table('stocks_list').select("Stock_id", "Industry", "Sector").execute()
        stock_data = stock_response.data
        joined_data = []
        for fin_item in fin_data:
            stock_id = fin_item['Stock_id']
            stock_item = next((item for item in stock_data if item['Stock_id'] == stock_id), None)
            if stock_item:
                joined_item = {**fin_item, **stock_item}
                joined_data.append(joined_item)

        # Create DataFrame from joined data
        df = pd.DataFrame(joined_data)

        # Group by Industry and aggregate
        industry_financials = df.groupby('Industry').agg({
            'Sector': 'first',
            'Stock_id': 'count',
            'EPS average Growth': list,
        })

        # Dictionary to store results
        industry_outliers = {}

        for industry, industry_df in industry_financials.iterrows():
            eps_growth_data = pd.Series(industry_df['EPS average Growth'])

            # Check if number of companies is greater than 10
            if industry_df['Stock_id'] > 10:
                eps_growth_data = eps_growth_data.dropna()
            else:
                # Get sector data if number of companies <= 10
                sector = industry_df['Sector']
                sector_df = df[df['Sector'] == sector]['EPS average Growth']
                eps_growth_data = sector_df.dropna()

            # Convert 'EPS average Growth' to numeric and calculate stats
            eps_growth_data = pd.to_numeric(eps_growth_data, errors='coerce')
            Q1 = eps_growth_data.quantile(0.25)
            Q3 = eps_growth_data.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            filtered_eps_growth_data = eps_growth_data[(eps_growth_data >= lower_bound) & (eps_growth_data <= upper_bound)]

            # Skip if filtered data is empty
            if filtered_eps_growth_data.empty:
                continue

            standard_deviation = filtered_eps_growth_data.std()
            mean = filtered_eps_growth_data.mean()
            min_value = mean - standard_deviation
            max_value = mean + standard_deviation

            # Store results in dictionary
            industry_outliers[industry] = {"max_value": max_value, "min_value": min_value}

        return industry_outliers
    except Exception as e:
        utils.Errors_logging.functions_error_log("calculate Industry outliers", e, utils.Errors_logging.log_name_rundb)
        return None


def custom_ranking(df_percentiles):
    try:
        df_percentiles['Score'] = 0.0
        df_percentiles['Outperformer'] = False
        df_percentiles['Underperformer'] = False

        if df_percentiles.empty:
            utils.Errors_logging.functions_error_log("custom_ranking", "df_percentiles is empty", utils.Errors_logging.log_name_rundb)
            return None

        industries_data = get_industries_data()
        sectors_data = get_sectors_data()
        stock_data = get_stocks_data()
        industries_ouliers = calculate_industry_outliers()

        for index, row in df_percentiles.iterrows():

            # Stock Info
            industry = row['Industry']
            sector = row['Sector']
            symbol = row['Symbol']
            stock_id = row['Stock_id']

            # Industry data
            industry_stats = industries_data[industries_data['Industry'] == industry]
            # Sector data
            sector_stats = sectors_data[sectors_data['Sector'] == sector]
            #Stock data
            stock_stats = stock_data[stock_data['Stock_id'] == stock_id]

            # Calculate Score
            try:
                # Value for investors:
                past_years_average = stock_stats['3 years av'].iloc[0]
                last_eps = stock_stats['Last EPS'].iloc[0]

                if industry_stats['Number of Companies'].iloc[0] > 10:
                    delta_eps = (past_years_average - industry_stats['3 years av'].iloc[0])
                else:
                    delta_eps = (past_years_average - sector_stats['3 years av'].iloc[0])

                value_eps = (past_years_average + delta_eps) * 0.7 + last_eps * 0.3
                roe = stock_stats['ROE'].iloc[0]
                if industry_stats['Number of Companies'].iloc[0] > 10:
                    delta_roe = (roe - industry_stats['ROE'].iloc[0])
                else:
                    delta_roe = (roe - sector_stats['ROE'].iloc[0])

                value_roe = roe + delta_roe
                total_value = value_eps * 0.7 + value_roe * 0.3

                # Growth:
                growth_percentile_by_indus = row['Growth percentile']
                growth_percentile = row['Total Growth percentile']
                last_growth_percentile_by_indus = row['Last Growth percentile']
                last_growth_percentile = row['Total last Growth percentile']

                if industry_stats['Number of Companies'].iloc[0] > 10:
                    value_growth = last_growth_percentile_by_indus * 0.25 + last_growth_percentile * 0.25 + growth_percentile_by_indus * 0.25 + growth_percentile * 0.25
                else:
                    value_growth = last_growth_percentile * 0.5 + growth_percentile * 0.5

                # risk:
                nwc_percentile = row['NWC percentile']
                der_percentile = 1 - row['DER percentile']

                risk_ratio = (nwc_percentile * 0.5 + der_percentile * 0.5)

                composite_score = (total_value * 4 * value_growth * risk_ratio
                                   )
                composite_score = round(composite_score, 1)
                df_percentiles.at[index, 'Score'] = composite_score
            except Exception as e:
                utils.Errors_logging.functions_error_log("custom_ranking - Score", e, utils.Errors_logging.log_name_rundb,symbol=symbol)

            #Performace check
            try:
                industry_outliers = industries_ouliers[industry]
                max_value = industry_outliers['max_value']
                min_value = industry_outliers['min_value']

                growth = stock_stats['EPS average Growth'].iloc[0]

                if growth > max_value:
                    df_percentiles.at[index,'Outperformer'] = True
                if growth < min_value:
                    df_percentiles.at[index,'Underperformer'] = True

            except Exception as e:
                utils.Errors_logging.functions_error_log("custom_ranking - Performance", e,
                                                         utils.Errors_logging.log_name_rundb,
                                                         symbol=symbol)
        return df_percentiles

    except Exception as e:
        utils.Errors_logging.functions_error_log("custom_ranking", e, utils.Errors_logging.log_name_rundb)
        return None


def process_and_update_data():
    try:
        # Run the add_percentile function
        percentile_data = add_percentile()
        if percentile_data is None:
            raise ValueError("Failed to get percentile data")

        # Run the custom_ranking function
        scored_data = custom_ranking(percentile_data)
        if scored_data is None:
            raise ValueError("Failed to calculate scores")

        # Patch or add rows to the stocks_ranking_data table
        for _, row in scored_data.iterrows():
            try:
                response = supabase.table('stocks_ranking_data').upsert(row.to_dict()).execute()
                utils.Sending_Email.job_done_email("Update Data Base", error_log_path)
            except Exception as e:
                utils.Errors_logging.functions_error_log("process_and_update_data: upsert table", e,
                                                         utils.Errors_logging.log_name_rundb)

    except Exception as e:
        utils.Errors_logging.functions_error_log("process_and_export_data", e, utils.Errors_logging.log_name_rundb)
        utils.Sending_Email.db_error_email(e, "Data Base", error_log_path)


def run_update_databases():
    try:

        # Create a stock data dataframe
        utils.Create_db.create_stock_data_db()

        # Calculate industry statistics
        utils.Create_db.calculate_industry_stat()

        # Calculate sector statistics
        utils.Create_db.calculate_sector_stat()

        # Add percentiles
        utils.Create_db.process_and_update_data()

        utils.Stock_selection.selection_by_fundamentals(100)

        error_log_path = 'errors_logs/db_update.csv'
        utils.Sending_Email.job_done_email("Update Data Base", error_log_path)

        utils.Stock_selection.selection_by_fundamentals(100)

    except Exception as e:
        utils.Errors_logging.functions_error_log("update_databases", e, utils.Errors_logging.log_name_rundb)
        error_log_path = 'errors_logs/db_update.csv'
        utils.Sending_Email.db_error_email(e, "Data Base update main", error_log_path)

