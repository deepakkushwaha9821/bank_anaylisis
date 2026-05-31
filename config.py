
import os


from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
RAW_DATA_DIR = BASE_DIR
DATA_DIR = BASE_DIR / 'data'
LOGS_DIR = BASE_DIR / 'logs'

REPORTS_DIR = BASE_DIR / 'reports'

DATA_DIR.mkdir(exist_ok=True)


LOGS_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)
RAW_CSV_PATH = RAW_DATA_DIR / 'Churn_Modelling.csv'
CLEAN_CSV_PATH = DATA_DIR / 'churn_clean.csv'
CLEAN_PARQUET_PATH = DATA_DIR / 'churn_clean.parquet'


import urllib.parse

PG_HOST = os.getenv('PG_HOST', 'localhost')
PG_PORT = os.getenv('PG_PORT', '5432')
PG_DATABASE = os.getenv('PG_DATABASE', 'bank_churn_etl')
PG_USER = os.getenv('PG_USER', 'postgres')
PG_PASSWORD = os.getenv('PG_PASSWORD', 'deep@#1140')

encoded_password = urllib.parse.quote_plus(PG_PASSWORD)
DATABASE_URL = f'postgresql+psycopg2://{PG_USER}:{encoded_password}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}'
SCHEDULE_TIME = '06:00'
ENABLE_EMAIL_ALERTS = False
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
EMAIL_SENDER = os.getenv('EMAIL_SENDER', '')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
EMAIL_RECIPIENT = os.getenv('EMAIL_RECIPIENT', '')
ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY', '')
ALPHA_VANTAGE_SYMBOL = 'JPM'
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 5