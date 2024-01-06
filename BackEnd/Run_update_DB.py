import Create_db
import Stock_selection
import pandas as pd


stock_list_path ="./stocks_data_csv/data_base/stock_list.csv"
Create_db.update_databases(stock_list_path)
csv_file_path = "./stocks_data_csv/data_base/Data_Base.csv"
Stock_selection.selection_by_fundamentals(csv_file_path, 100)

# stock_data =pd.read_csv(stock_list_path)
# stock_list = stock_data['Symbol'].tolist()
# total = len(stock_list)
# x = 0
# for symbol in stock_list:
#     x += 1
#     score = Create_db.custom_ranking(symbol)
#     print(f'{x}/{total} - {symbol}: {score}')

