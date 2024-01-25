import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import pandas as pd
import utils.Stock_Data
from datetime import datetime
import utils.Errors_logging

def send_html_email(subject, body, recipient_email, sender_email, sender_password, smtp_server, smtp_port, attachment_path=None):
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    if attachment_path:
        with open(attachment_path, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(attachment_path)}")
            msg.attach(part)

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()
        #print("Email sent successfully")
    except Exception as e:
        utils.Errors_logging.functions_error_log("send_email", e, utils.Errors_logging.log_name_emails)

def send_email(subject, body, recipient_email, sender_email, sender_password, smtp_server, smtp_port, attachment_path=None):
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    if attachment_path:
        with open(attachment_path, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(attachment_path)}")
            msg.attach(part)

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()
        #print("Email sent successfully")
    except Exception as e:
        utils.Errors_logging.functions_error_log("send_email", e, utils.Errors_logging.log_name_emails)

def process_signals(symbol):
    signal = check_signals(symbol)  # Assuming this function returns 'Buy', 'Sell', or None
    client_emails = get_client_emails('client_list.csv')  # Fetch client emails from CSV

    if signal == 'Buy':
        update_portfolio(symbol, 'Buy')
        send_email(f"New Buying Signal", f"Buy signal for the stock {symbol}", client_emails, ...)
    elif signal == 'Sell':
        if symbol_in_portfolio(symbol, 'portfolio.csv'):  # Check if symbol is in the portfolio
            update_portfolio(symbol, 'Sell')
            send_email(f"New Selling Signal", f"Sell signal for the stock {symbol}", client_emails, ...)



def format_date(input_date):
    # Convert the input date string to a datetime object
    date_object = datetime.strptime(input_date, "%Y-%m-%d")

    # Define the suffix for the day
    def date_suffix(day):
        return 'th' if 11 <= day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')

    # Apply the suffix to the day
    day_with_suffix = str(date_object.day) + date_suffix(date_object.day)

    # Format the date without the weekday
    formatted_date = date_object.strftime(f"{day_with_suffix} of %B %Y")
    return formatted_date



def process_buy_signals(symbol, date):
    sender_email = os.environ.get('SENDER_EMAIL')
    sender_pw = os.environ.get('SENDER_EMAIL_PW')
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    info = utils.Stock_Data.get_company_info(symbol)
    company_name = info['Company Name']
    recipient_list_csv = './stocks_data_csv/data_base/users_emails.csv'
    recipient_df = pd.read_csv(recipient_list_csv)
    # Create a dictionary from the DataFrame
    name_email_dict = pd.Series(recipient_df.Email.values, index=recipient_df.Name).to_dict()
    formatted_date = format_date(date)

    # Iterating through the dictionary
    for name, email in name_email_dict.items():

        subject = f'New signal for {company_name}({symbol})'
        body = f"""
                                Hey {name},
    
                                We found a new buy opportunity for {company_name} this {formatted_date},
                                Go buy it daawwg.
    
                                Get rich or dying trying akhi.
    
                                Yass-Cap Team
                                """
        send_email(subject, body, email, sender_email, sender_pw, smtp_server, smtp_port)


def process_sell_signals(symbol, date):
    sender_email = os.environ.get('SENDER_EMAIL')
    sender_pw = os.environ.get('SENDER_EMAIL_PW')
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    info = utils.Stock_Data.get_company_info(symbol)
    company_name = info['Company Name']
    recipient_list_csv = './stocks_data_csv/data_base/users_emails.csv'
    recipient_df = pd.read_csv(recipient_list_csv)
    # Create a dictionary from the DataFrame
    name_email_dict = pd.Series(recipient_df.Email.values, index=recipient_df.Name).to_dict()
    formatted_date = format_date(date)

    # Iterating through the dictionary
    for name, email in name_email_dict.items():
        subject = f'New signal for {company_name}({symbol})'
        body = f"""
                                Hey {name},

                                We found a new selling opportunity for {company_name} this {formatted_date},
                                Drop that bitch ese.

                                Collect the dinero.

                                Yass-Cap Team
                                """
        send_email(subject, body, email, sender_email, sender_pw, smtp_server, smtp_port)


def error_email(symbol, error_message):
    sender_email = os.environ.get('SENDER_EMAIL')
    sender_pw = os.environ.get('SENDER_EMAIL_PW')
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    info = utils.Stock_Data.get_company_info(symbol)
    company_name = info['Company Name']
    recipient_email = os.environ.get('SENDER_EMAIL')
    subject = f'New Error for {symbol}'
    body = f"{error_message}"
    send_email(subject, body, recipient_email, sender_email, sender_pw, smtp_server, smtp_port)

def db_error_email(error_message, code, error_log_path=None):
    sender_email = os.environ.get('SENDER_EMAIL')
    sender_pw = os.environ.get('SENDER_EMAIL_PW')
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    recipient_email = os.environ.get('SENDER_EMAIL')
    subject = f'New Error for updating {code}'
    body = f"{error_message}"
    send_email(subject, body, recipient_email, sender_email, sender_pw, smtp_server, smtp_port)

    if os.path.isfile(error_log_path) and os.path.getsize(error_log_path) > 0:
        body += "\nPlease find the error log attached."
        send_email(subject, body, recipient_email, sender_email, sender_pw, smtp_server, smtp_port,
                   attachment_path=error_log_path)
    else:
        send_email(subject, body, recipient_email, sender_email, sender_pw, smtp_server, smtp_port)
    send_email(subject, body, recipient_email, sender_email, sender_pw, smtp_server, smtp_port)


def job_done_email(job_name, error_log_path):
    sender_email = os.environ.get('SENDER_EMAIL')
    sender_pw = os.environ.get('SENDER_EMAIL_PW')
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    recipient_email = os.environ.get('SENDER_EMAIL')
    subject = f'Satus for {job_name}: Successful'
    body = f"The {job_name} is donne correctly"

    # if os.path.isfile(error_log_path) and os.path.getsize(error_log_path) > 0:
    body += "\nPlease find the error log attached."
    send_email(subject, body, recipient_email, sender_email, sender_pw, smtp_server, smtp_port,
               attachment_path=error_log_path)
    # else:
    #     send_email(subject, body, recipient_email, sender_email, sender_pw, smtp_server, smtp_port)


def portfolio_email():
    sender_email = os.environ.get('SENDER_EMAIL')
    sender_pw = os.environ.get('SENDER_EMAIL_PW')
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    recipient_email = os.environ.get('SENDER_EMAIL')
    subject = f'Portfolio Email'
    body = f"Please find the portfolio attached"
    portfolio_path = "./stocks_data_csv/data_base/portfolio.csv"

    send_email(subject, body, recipient_email, sender_email, sender_pw, smtp_server, smtp_port,
               attachment_path=portfolio_path)


def transaction_log_email():
    sender_email = os.environ.get('SENDER_EMAIL')
    sender_pw = os.environ.get('SENDER_EMAIL_PW')
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    recipient_email = os.environ.get('SENDER_EMAIL')
    subject = f'Transaction log Email'
    body = f"Please find the transaction log attached"
    transaction_path = "./stocks_data_csv/data_base/transactions_logs.csv"

    send_email(subject, body, recipient_email, sender_email, sender_pw, smtp_server, smtp_port,
               attachment_path=transaction_path)

