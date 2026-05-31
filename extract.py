
import logging
import pandas as pd
import requests
import config
logger = logging.getLogger(__name__)

def extract_from_csv(path=None):
    """

    Extract raw data from the Churn_Modelling.csv file.


    Parameters


    ----------
    path : str or Path, optional
        Path to the CSV file. Defaults to config.RAW_CSV_PATH.

    Returns
    -------
    pd.DataFrame
        Raw DataFrame with all original columns.

    Raises
    ------
    FileNotFoundError
        If the CSV file does not exist at the specified path.

    ValueError
        If the CSV is empty or has unexpected columns.
    """

    path = path or config.RAW_CSV_PATH
    logger.info(f'Extracting data from CSV: {path}')
    if not path.exists():
        raise FileNotFoundError(f'Raw CSV not found: {path}')
    dtype_map = {'RowNumber': 'int64', 'CustomerId': 'int64', 'Surname': 'str', 'CreditScore': 'int64', 'Geography': 'str', 'Gender': 'str', 'Age': 'int64', 'Tenure': 'int64', 'NumOfProducts': 'int64', 'HasCrCard': 'int64', 'IsActiveMember': 'int64', 'Exited': 'int64'}
    df = pd.read_csv(path, dtype=dtype_map)
    if df.empty:
        raise ValueError('CSV file is empty — no rows found.')
    expected_columns = {'RowNumber', 'CustomerId', 'Surname', 'CreditScore', 'Geography', 'Gender', 'Age', 'Tenure', 'Balance', 'NumOfProducts', 'HasCrCard', 'IsActiveMember', 'EstimatedSalary', 'Exited'}
    actual_columns = set(df.columns)

    missing = expected_columns - actual_columns
    if missing:
        raise ValueError(f'Missing expected columns: {missing}')
    logger.info(f'CSV extraction complete — {len(df):,} rows, {len(df.columns)} columns')
    return df

def extract_from_api(symbol=None, api_key=None):
    """
    (Optional) Extract daily stock price data from Alpha Vantage API.

    This demonstrates API-based extraction for portfolio purposes.
    Requires a free API key from https://www.alphavantage.co/

    Parameters
    ----------
    symbol : str, optional
        Stock ticker symbol. Defaults to config.ALPHA_VANTAGE_SYMBOL.
    api_key : str, optional
        Alpha Vantage API key. Defaults to config.ALPHA_VANTAGE_API_KEY.

    Returns
    -------
    pd.DataFrame or None
        DataFrame with daily stock prices, or None if API key not set.
    """
    symbol = symbol or config.ALPHA_VANTAGE_SYMBOL
    api_key = api_key or config.ALPHA_VANTAGE_API_KEY
    if not api_key:
        logger.info('Alpha Vantage API key not configured — skipping API extraction. Set ALPHA_VANTAGE_API_KEY in config.py or as an env var.')

        return None

    url = 'https://www.alphavantage.co/query'
    params = {'function': 'TIME_SERIES_DAILY', 'symbol': symbol, 'outputsize': 'compact', 'apikey': api_key}
    logger.info(f'Extracting stock data for {symbol} from Alpha Vantage API...')
    try:
        response = requests.get(url, params=params, timeout=30)


        response.raise_for_status()

        data = response.json()
        if 'Time Series (Daily)' not in data:
            logger.warning(f'Unexpected API response: {list(data.keys())}. Check your API key or rate limits.')
            return None
        ts = data['Time Series (Daily)']

        df = pd.DataFrame.from_dict(ts, orient='index')
        df.index = pd.to_datetime(df.index)
        df.index.name = 'date'

        df.columns = ['open', 'high', 'low', 'close', 'volume']
        df = df.astype({'open': 'float64', 'high': 'float64', 'low': 'float64', 'close': 'float64', 'volume': 'int64'})

        df = df.sort_index()
        logger.info(f'API extraction complete — {len(df)} trading days for {symbol}')
        return df
    except requests.RequestException as e:
        logger.error(f'Alpha Vantage API request failed: {e}')
        return None

def extract():
    """
    Master extraction function — runs all data sources.


    Returns

    -------
    dict[str, pd.DataFrame]


        Dictionary of named DataFrames:
        - "churn": the main bank churn dataset (always present)
        - "stock": Alpha Vantage stock data (None if not configured)
    """
    logger.info('=' * 60)
    logger.info('PHASE 1: EXTRACTION — Starting')
    logger.info('=' * 60)
    results = {}

    results['churn'] = extract_from_csv()
    results['stock'] = extract_from_api()

    sources_loaded = sum((1 for v in results.values() if v is not None))
    logger.info(f'Extraction complete — {sources_loaded} source(s) loaded successfully')
    return results
if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s')
    data = extract()
    print(f"\n{'-' * 40}")

    print(f"Churn dataset: {data['churn'].shape}")
    if data['stock'] is not None:
        print(f"Stock dataset: {data['stock'].shape}")
    else:
        print('Stock dataset: not loaded (API key not set)')
    print(f"{'-' * 40}")
