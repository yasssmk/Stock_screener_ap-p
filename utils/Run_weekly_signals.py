import Signals
import pandas as pd
import Sending_Email
import Signals

stock_list_100_selection_df = pd.read_csv('./stocks_data_csv/data_base/final_100_selection.csv')
stock_list_manual_selection_df =pd.read_csv('./stocks_data_csv/data_base/manual_selection.csv')

symbols_100_selection = stock_list_100_selection_df['Symbol'].tolist()
symbols_manual_selection = stock_list_manual_selection_df['Symbol'].tolist()

symbols = list(set(symbols_100_selection + symbols_manual_selection))


try:
    for symbol in symbols:
        Signals.add_weekly_stock_data(symbol)
    error_log_path = './stocks_data_csv/errors_logs/Weekly_signals.csv'
    #Sending_Email.job_done_email("Run Weekly Signal", error_log_path)
except Exception as e:
    error_log_path = './stocks_data_csv/errors_logs/Weekly_signals.csv'
    #Sending_Email.db_error_email(e, "Run Weekly Signal", error_log_path)


#Sending_Email.portfolio_email()
#Sending_Email.transaction_log_email()



