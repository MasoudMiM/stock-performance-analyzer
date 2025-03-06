# Stock Performance Analyzer

A tool for analyzing stock performance over a specified period. This project fetches stock data from Yahoo Finance, calculates performance metrics, and generates visual reports. It can also send email reports with the analysis results.

## Features
Thie code

- Fetches stock data for tickers listed in [NASDAQ_sample](./data/NASDAQ_sample.txt) and [NYSE_sample](./data/NYSE_sample.txt) files from Yahoo Finance.
- Calculates performance metrics including price growth and volatility.
- Identifies top and bottom performing stocks from the list of stocks provided.
- Generates visual plots of stock performance.
- Sends an email report with analysis results and attached plots using the Gmail API.
- Logs for tracking the execution and debugging.

## Requirements

- Python 3.11
- Required Python packages:
  - `yfinance`
  - `numpy`
  - `pandas`
  - `matplotlib`
  - `google-auth`
  - `google-auth-oauthlib`
  - `google-api-python-client`
  - `tenacity`

You can install the required packages using pip:

```bash
pip install yfinance numpy pandas matplotlib google-auth google-auth-oauthlib google-api-python-client tenacity
```

## Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/MasoudMiM/stock-performance-analyzer.git
   cd stock-performance-analyzer
   ```

2. **Prepare input files:**
   - Create two text files named `NASDAQ_sample.txt` and `NYSE_sample.txt` in the `data` directory. Each file should contain stock tickers and their names in a tab-delimited format. The first row should be a header.

   Example format:
   ```
   Ticker    Name
   AAPL      Apple Inc.
   MSFT      Microsoft Corp.
   ```

3. **Set up Google API for email:**
   - Go to the [Google Cloud Console](https://console.cloud.google.com/).
   - Create a new project.
   - Enable the Gmail API for your project.
   - Create OAuth 2.0 credentials and download the `client_secret.json` file.
   - Place the `client_secret.json` file in the root directory of the project.

4. **Run the script:**
   - You can run the script with default parameters or specify your own. The default parameters are set to analyze stocks over the last 90 days and send the report to a specified email.

   ```bash
   python stock_analysis.py
   ```

   To customize the parameters, modify the `main` function call at the bottom of the script:

   ```python
   if __name__ == '__main__':
       main(days=DAYS, top_n=N_STOCK, recipient_email=MY_EMAIL)
   ```
   
## Example Output 

You can find a sample output [here](./outputs/results_20250306_020506/) for the given sample stock names in the text files under [data folder](./data/).

## Usage

- The script will log its progress and results in a log file located in the `logs` directory.
- The analysis results will be saved in the `outputs` directory, including CSV files for top and bottom performing stocks and plots of their performance.
- An email report will be sent to the specified recipient email if provided.
