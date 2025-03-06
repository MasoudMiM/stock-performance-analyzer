import yfinance as yf
import numpy as np
from time import sleep
import pandas as pd
import logging, os, base64, traceback
import matplotlib.pyplot as plt
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from tenacity import retry, stop_after_attempt, wait_exponential


# ------ USER INPUT
MY_EMAIL = "example@gmail.com" # email to send the report like "example@gmail.com"
N_STOCK = 10 # number of best and worst performing stocks
DAYS = 90 # number of days to consider
INPUT_NYSE = 'NYSE_sample.txt'
INPUT_NASDAQ = 'NASDAQ_sample.txt'
# -------

# Set up logging
def setup_logger():
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f'stock_analysis_{timestamp}.log')
    
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        handlers=[
                            logging.FileHandler(log_file),
                            logging.StreamHandler()
                        ])
    return logging.getLogger()

# my function to read tickers from a file (assuming a standard CSV or TXT format)
def read_tickers_from_txt(file_path):
    tickers_df = pd.read_csv(file_path, delimiter='\t', header=None, skiprows=1)
    return tickers_df[0].tolist(), tickers_df[1].tolist()

# my function to get stock data
def get_stock_data(ticker, days, logger):
    try:
        if days == 5:
            data = yf.download(ticker, period="5d", progress=False)
            data_range = "5 days"
        elif days > 5 and days <= 30:
            data = yf.download(ticker, period="1mo", progress=False)
            data_range = "1 month"
        elif days > 30 and days <= 90:
            data = yf.download(ticker, period="3mo", progress=False)
            data_range = "3 months"
        elif days > 90 and days <= 180:
            data = yf.download(ticker, period="6mo", progress=False)
            data_range = "6 months"
        if data is None or data.empty:
            logger.warning(f"No data available for {ticker}")
            return None, None
        return data, data_range
    except Exception as e:
        logger.error(f"Error fetching data for {ticker}: {e}")
        return None, None

# my function to analyze performance (Price Growth and Volatility)
def calculate_performance(data):
    start_price = data['Close'].iloc[0]
    end_price = data['Close'].iloc[-1]
    price_growth = ((end_price - start_price) / start_price) * 100
    daily_returns = data['Close'].pct_change().dropna()
    volatility = np.std(daily_returns, axis=0) * np.sqrt(len(data))
    return price_growth, volatility, start_price, end_price

def analyze_all_stocks(tickers, names, days, logger):
    performance_results = []
    total = len(tickers)
    count = 0
    for ticker, name in zip(tickers, names):
        count += 1
        logger.info(f"Fetching data for {ticker}... ({count}/{total})")
        data, data_range = get_stock_data(ticker, days, logger)
        
        if data is not None:
            price_growth, volatility, start_price, end_price = calculate_performance(data)

            performance_results.append({
                'Name': name,
                'Ticker': ticker,
                'Start Price': start_price[ticker],
                'End Price': end_price[ticker],
                'Price Growth (%)': price_growth[ticker],
                'Volatility': volatility[ticker],
                'Data Range': data_range
            })

        sleep(1)  # pause 1 second to prevent rate-limiting
    
    df = pd.DataFrame(performance_results)
    return df, data_range

# to get top and bottom performers
def get_top_and_bottom_performers(df, top_n, logger):
    logger.info(f"Data for calculating best and wors performers:\n {df['Price Growth (%)']}") # DEBUG
    df_sorted = df.sort_values(by='Price Growth (%)', ascending=False)
    top_performers = df_sorted.head(top_n)
    logger.info(f"Top performers {top_performers}")
    worst_performers = df_sorted.tail(top_n).sort_values(by='Price Growth (%)', ascending=True)
    logger.info(f"Worst performers {worst_performers}")
    
    return top_performers, worst_performers

def plot_performers(output_dir, performers, title, days, logger):
    plt.figure(figsize=(15, 5 * ((len(performers) + 1) // 2)))
    
    signals = []

    for i, (_, row) in enumerate(performers.iterrows(), 1):
        ticker = row['Ticker']
        name = row['Name']
        logger.info(f"Plotting data for {ticker} - {name}")
        data, data_range = get_stock_data(ticker, days, logger)
        
        if data is not None:
            ax = plt.subplot(((len(performers) + 1) // 2), 2, i)
            data['Close'].plot(ax=ax)
            ax.set_title(f"{ticker} - {name} | duration: {data_range}")
            ax.set_ylabel("Price")
            ax.grid(True)
            
            signals.append((ticker, name, data['Close'][ticker].to_list()))

    plt.tight_layout()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plot_file = f'{output_dir}/{title}_{data_range.strip()}_{timestamp}.png'
    plt.savefig(plot_file)
    logger.info(f"Plot saved as {plot_file}")
    plt.close()

    signals_file = f'{output_dir}/{title}_{data_range.strip()}_{timestamp}.txt'
    with open(signals_file, 'w') as f:
        f.write("Ticker,Name,Date,Close_Price\n") 
        for ticker, name, close_prices in signals:
            for date, price in zip(data.index, close_prices):
                f.write(f"{ticker},{name},{date},{price}\n")

    logger.info(f"Signals saved as {signals_file}")
    return plot_file


SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def get_gmail_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)
    return service

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def send_email(service, top_performers, worst_performers, top_plot, bottom_plot,recipient_email, logger, top_n, data_range):
    try:
        logger.info(f"Attempting to send email to {recipient_email}")
        message = MIMEMultipart()
        message['to'] = recipient_email
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message['subject'] = f"Stock Performance Report - {current_time}"

        text = f"Here are the top {top_n} and bottom {top_n} performing stocks in {data_range.strip()}:"
        message.attach(MIMEText(text, 'plain'))
        logger.info("Added text content to email")

        html_content = "<h2>Top Performing Stocks</h2>"
        html_content += top_performers.to_html(index=False)
        html_content += "<h2>Worst Performing Stocks</h2>"
        html_content += worst_performers.to_html(index=False)
        html_content += "<h2>Currently Owned Stocks</h2>"
        html_content += "<br><p>Please see the attached plots for visual representation.</p>"
        message.attach(MIMEText(html_content, 'html'))
        logger.info("Added HTML content with top and worst performers")

        for plot_file, plot_name in [(top_plot, "Top Performers"), (bottom_plot, "Worst Performers")]:
            with open(plot_file, 'rb') as f:
                img = MIMEImage(f.read())
                img.add_header('Content-Disposition', 'attachment', filename=os.path.basename(plot_file))
                message.attach(img)
        logger.info("Attached plots to email")

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        message = service.users().messages().send(userId='me', body={'raw': raw_message}).execute(num_retries=3)
        logger.info(f"Message Id: {message['id']}")
        logger.info("Email sent successfully")
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        raise

def main(days=15, top_n=10, recipient_email=None):
    logger = setup_logger()
    logger.info("Starting stock analysis")
    logger.info("Reading tickers from files...")
    
    nasdaq_tickers, nasdaq_names = read_tickers_from_txt(f'data/{INPUT_NASDAQ}')
    nyse_tickers, nyse_names = read_tickers_from_txt(f'data/{INPUT_NYSE}')
    
    all_tickers = nasdaq_tickers + nyse_tickers 
    all_names = nasdaq_names + nyse_names

    seen = set()
    unique_tickers = []
    unique_names = []

    for ticker, name in zip(all_tickers, all_names):
        if ticker not in seen:
            seen.add(ticker)
            unique_tickers.append(ticker)
            unique_names.append(name)

    logger.info(f"Total tickers: {len(unique_tickers)}")

    df, data_range = analyze_all_stocks(unique_tickers, unique_names, days, logger)
    
    top_performers, worst_performers = get_top_and_bottom_performers(df, top_n, logger)
    
    logger.info("Top Performing Stocks:")
    logger.info("\n" + top_performers.to_string())
    logger.info("Worst Performing Stocks:")
    logger.info("\n" + worst_performers.to_string())

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    output_dir = f'outputs/results_{timestamp}'
    os.makedirs(output_dir, exist_ok=True)

    logger.info(f"Saving the results in {output_dir} folder...")

    top_performers.to_csv(f'{output_dir}/top_{top_n}_{data_range.strip()}_stocks_{timestamp}.csv', index=False)
    worst_performers.to_csv(f'{output_dir}/worst_{top_n}_{data_range.strip()}_stocks_{timestamp}.csv', index=False)
    
    logger.info("Top and worst performing stocks as well as currently owned ones saved to CSV files")

    top_plot = plot_performers(output_dir, top_performers, f"top_{top_n}_performers", days, logger)
    bottom_plot = plot_performers(output_dir, worst_performers, f"worst_{top_n}_performers", days, logger)


    if recipient_email:
        service = get_gmail_service()
        send_email(service, top_performers, worst_performers, top_plot, bottom_plot, recipient_email, logger, top_n, data_range)

if __name__ == '__main__':
    main(days=DAYS, top_n=N_STOCK, recipient_email=MY_EMAIL)

