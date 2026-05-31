
import logging
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import create_engine, Column, Integer, BigInteger, String, Float, Boolean, Date, DateTime, text
from sqlalchemy.orm import declarative_base, sessionmaker
import config
logger = logging.getLogger(__name__)
Base = declarative_base()


class DimCustomer(Base):
    """Dimension table: customer demographics."""
    __tablename__ = 'dim_customer'
    customer_id = Column(BigInteger, primary_key=True, autoincrement=False)
    surname = Column(String(100))
    geography = Column(String(50))
    gender = Column(String(20))
    age = Column(Integer)

    age_group = Column(String(10))

    credit_tier = Column(String(20))

class FactChurn(Base):

    """Fact table: customer churn metrics and scores."""
    __tablename__ = 'fact_churn'
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(BigInteger, nullable=False, index=True)
    credit_score = Column(Integer)
    tenure = Column(Integer)
    balance = Column(Float)
    num_of_products = Column(Integer)
    has_credit_card = Column(Boolean)
    is_active_member = Column(Boolean)


    estimated_salary = Column(Float)

    customer_value_score = Column(Float)
    is_high_value = Column(Boolean)
    exited = Column(Boolean)

    balance_category = Column(String(20))
    salary_quartile = Column(String(5))
    loaded_at = Column(DateTime, default=lambda : datetime.now(timezone.utc))

class AggGeographyChurn(Base):
    """Aggregation table: churn metrics by geography."""
    __tablename__ = 'agg_geography_churn'
    id = Column(Integer, primary_key=True, autoincrement=True)
    geography = Column(String(50))

    total_customers = Column(Integer)
    churned_customers = Column(Integer)
    churn_rate = Column(Float)
    avg_balance = Column(Float)

    avg_credit_score = Column(Float)
    avg_age = Column(Float)
    avg_tenure = Column(Float)
    avg_salary = Column(Float)
    snapshot_date = Column(Date)

class AggAgeGroupChurn(Base):
    """Aggregation table: churn metrics by age group."""
    __tablename__ = 'agg_age_group_churn'
    id = Column(Integer, primary_key=True, autoincrement=True)
    age_group = Column(String(10))
    total_customers = Column(Integer)
    churned_customers = Column(Integer)
    churn_rate = Column(Float)
    avg_tenure = Column(Float)

    avg_products = Column(Float)
    avg_balance = Column(Float)
    avg_value_score = Column(Float)
    snapshot_date = Column(Date)

def get_engine(url=None):
    """Create a SQLAlchemy engine."""
    url = url or config.DATABASE_URL
    return create_engine(url, echo=False, pool_pre_ping=True)

def create_tables(engine):
    """Create all tables if they don't exist."""


    logger.info('Creating database tables (if not exists)...')

    Base.metadata.create_all(engine)


    logger.info('  Tables created/verified: ' + ', '.join((t.name for t in Base.metadata.sorted_tables)))

def load_dimension(df, engine):
    """
    Load/upsert data into dim_customer.

    Uses pandas to_sql with 'replace' strategy for simplicity,
    or row-by-row upsert for production use.

    Parameters


    ----------
    df : pd.DataFrame
        Cleaned churn DataFrame with customer columns.
    engine : sqlalchemy.Engine
    """
    logger.info('Loading dim_customer...')
    dim_cols = ['customer_id', 'surname', 'geography', 'gender', 'age', 'age_group', 'credit_tier']
    dim_df = df[dim_cols].copy()


    for col in ['age_group', 'credit_tier']:
        dim_df[col] = dim_df[col].astype(str)


    with engine.begin() as conn:
        conn.execute(text('DELETE FROM dim_customer'))

    dim_df.to_sql('dim_customer', engine, if_exists='append', index=False, method='multi', chunksize=1000)

    logger.info(f'  Loaded {len(dim_df):,} rows into dim_customer')

def load_fact(df, engine):
    """
    Load data into fact_churn.

    Appends a new batch with a loaded_at timestamp so we can
    track load history.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned churn DataFrame.
    engine : sqlalchemy.Engine
    """


    logger.info('Loading fact_churn...')
    fact_cols = ['customer_id', 'credit_score', 'tenure', 'balance', 'num_of_products', 'has_credit_card', 'is_active_member', 'estimated_salary', 'customer_value_score', 'is_high_value', 'exited', 'balance_category', 'salary_quartile']

    fact_df = df[fact_cols].copy()
    fact_df['loaded_at'] = datetime.now(timezone.utc)

    for col in ['balance_category', 'salary_quartile']:
        fact_df[col] = fact_df[col].astype(str)
    with engine.begin() as conn:
        conn.execute(text('DELETE FROM fact_churn'))
    fact_df.to_sql('fact_churn', engine, if_exists='append', index=False, method='multi', chunksize=1000)
    logger.info(f'  Loaded {len(fact_df):,} rows into fact_churn')

def load_aggregations(aggregations, engine):

    """
    Load aggregation summary tables.

    Parameters


    ----------
    aggregations : dict[str, pd.DataFrame]


        Output from transform.build_aggregations().
    engine : sqlalchemy.Engine
    """
    logger.info('Loading aggregation tables...')


    table_map = {'by_geography': 'agg_geography_churn', 'by_age_group': 'agg_age_group_churn'}
    for (key, table_name) in table_map.items():
        if key in aggregations:
            agg_df = aggregations[key].copy()
            for col in agg_df.select_dtypes(include=['category']).columns:
                agg_df[col] = agg_df[col].astype(str)
            with engine.begin() as conn:
                conn.execute(text(f'DELETE FROM {table_name}'))
            agg_df.to_sql(table_name, engine, if_exists='append', index=False, method='multi')
            logger.info(f'  Loaded {len(agg_df)} rows into {table_name}')

def save_clean_files(df):
    """

    Save the cleaned DataFrame as CSV and Parquet backup files.

    Parameters
    ----------
    df : pd.DataFrame


        Cleaned and featured churn DataFrame.


    """
    logger.info('Saving clean data files...')
    df_out = df.copy()
    for col in df_out.select_dtypes(include=['category']).columns:


        df_out[col] = df_out[col].astype(str)
    df_out.to_csv(config.CLEAN_CSV_PATH, index=False)


    logger.info(f'  Saved: {config.CLEAN_CSV_PATH}')

    try:
        df_out.to_parquet(config.CLEAN_PARQUET_PATH, index=False, engine='pyarrow')
        logger.info(f'  Saved: {config.CLEAN_PARQUET_PATH}')
    except ImportError:
        logger.warning('  pyarrow not installed — skipping Parquet output. Install with: pip install pyarrow')


def load(transformed_data):


    """


    Master load function — creates tables, loads all data,

    and saves clean file backups.



    Parameters
    ----------
    transformed_data : dict

        Output from transform.transform().

    """

    logger.info('=' * 60)

    logger.info('PHASE 3: LOAD — Starting')

    logger.info('=' * 60)

    churn_df = transformed_data['churn_clean']
    aggregations = transformed_data['aggregations']
    save_clean_files(churn_df)

    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        logger.info(f'  Connected to PostgreSQL: {config.PG_DATABASE}')
        create_tables(engine)
        load_dimension(churn_df, engine)
        load_fact(churn_df, engine)
        load_aggregations(aggregations, engine)
        with engine.connect() as conn:
            for table in Base.metadata.sorted_tables:
                result = conn.execute(text(f'SELECT COUNT(*) FROM {table.name}'))
                count = result.scalar()

                logger.info(f'  {table.name}: {count:,} rows')
        logger.info('PostgreSQL load complete')
    except Exception as e:
        logger.error(f'PostgreSQL load failed: {e}')
        logger.info('Clean CSV/Parquet files were still saved successfully. Fix the DB connection and re-run, or use the files directly.')
        raise


    logger.info('PHASE 3: LOAD — Complete')
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s')


    from extract import extract
    from transform import transform


    raw = extract()
    transformed = transform(raw)
    load(transformed)