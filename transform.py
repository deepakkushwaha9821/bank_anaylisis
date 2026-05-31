"""
transform.py — Phase 2: Data Transformation

Cleans raw data, engineers new features, and produces aggregated
summary tables ready for the Load phase.

"""
import logging
import numpy as np
import pandas as pd
logger = logging.getLogger(__name__)

def clean_data(df):
    """


    Clean the raw churn DataFrame.

    Steps:
    1. Drop the meaningless RowNumber column
    2. Remove duplicate CustomerId rows
    3. Handle null values (fill or flag)
    4. Cast boolean-like columns to actual booleans
    5. Standardize categorical columns to title case

    Parameters
    ----------
    df : pd.DataFrame

        Raw extracted DataFrame.

    Returns
    -------
    pd.DataFrame

        Cleaned DataFrame.
    """
    logger.info('Cleaning data...')


    df = df.copy()
    initial_rows = len(df)
    if 'RowNumber' in df.columns:


        df = df.drop(columns=['RowNumber'])
        logger.info('  Dropped column: RowNumber')

    dupes = df.duplicated(subset=['CustomerId'], keep='first').sum()
    if dupes > 0:
        df = df.drop_duplicates(subset=['CustomerId'], keep='first')
        logger.warning(f'  Removed {dupes} duplicate CustomerId rows')
    else:
        logger.info('  No duplicate CustomerIds found')
    null_counts = df.isnull().sum()
    total_nulls = null_counts.sum()
    if total_nulls > 0:
        logger.warning(f'  Found {total_nulls} null values:')

        for (col, cnt) in null_counts[null_counts > 0].items():

            logger.warning(f'    {col}: {cnt} nulls')
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        categorical_cols = df.select_dtypes(include=['object']).columns
        for col in numeric_cols:
            if df[col].isnull().any():
                median_val = df[col].median()
                df[col] = df[col].fillna(median_val)
                logger.info(f'    Filled {col} nulls with median: {median_val}')
        for col in categorical_cols:
            if df[col].isnull().any():
                mode_val = df[col].mode()[0]
                df[col] = df[col].fillna(mode_val)
                logger.info(f'    Filled {col} nulls with mode: {mode_val}')
    else:
        logger.info('  No null values found')
    bool_columns = {'HasCrCard': 'has_credit_card', 'IsActiveMember': 'is_active_member', 'Exited': 'exited'}
    for (old_name, new_name) in bool_columns.items():
        if old_name in df.columns:

            df[new_name] = df[old_name].astype(bool)

            if new_name != old_name:
                df = df.drop(columns=[old_name])


    if 'Geography' in df.columns:

        df['Geography'] = df['Geography'].str.strip().str.title()
    if 'Gender' in df.columns:
        df['Gender'] = df['Gender'].str.strip().str.title()


    rename_map = {'CustomerId': 'customer_id', 'Surname': 'surname', 'CreditScore': 'credit_score', 'Geography': 'geography', 'Gender': 'gender', 'Age': 'age', 'Tenure': 'tenure', 'Balance': 'balance', 'NumOfProducts': 'num_of_products', 'EstimatedSalary': 'estimated_salary'}


    df = df.rename(columns={k: v for (k, v) in rename_map.items() if k in df.columns})
    final_rows = len(df)

    logger.info(f'  Cleaning complete: {initial_rows:,} → {final_rows:,} rows ({initial_rows - final_rows} removed)')
    return df

def engineer_features(df):
    """
    Create derived columns for analysis and segmentation.

    New columns:
    - age_group: binned age ranges
    - balance_category: Zero / Low / Medium / High
    - credit_tier: Poor / Fair / Good / Excellent
    - salary_quartile: Q1-Q4 based on estimated salary
    - customer_value_score: weighted composite score


    - is_high_value: top 25% by value score

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned DataFrame.

    Returns

    -------
    pd.DataFrame
        DataFrame with new feature columns.
    """
    logger.info('Engineering features...')
    df = df.copy()
    age_bins = [0, 25, 35, 45, 55, 100]
    age_labels = ['18-25', '26-35', '36-45', '46-55', '56+']
    df['age_group'] = pd.cut(df['age'], bins=age_bins, labels=age_labels, right=True)


    logger.info('  Created: age_group')

    def categorize_balance(bal):
        if bal == 0:
            return 'Zero'
        elif bal < 50000:
            return 'Low'
        elif bal < 100000:
            return 'Medium'
        else:
            return 'High'
    df['balance_category'] = df['balance'].apply(categorize_balance)
    logger.info('  Created: balance_category')
    credit_bins = [0, 579, 669, 739, 850]
    credit_labels = ['Poor', 'Fair', 'Good', 'Excellent']
    df['credit_tier'] = pd.cut(df['credit_score'], bins=credit_bins, labels=credit_labels, right=True)
    logger.info('  Created: credit_tier')
    df['salary_quartile'] = pd.qcut(df['estimated_salary'], q=4, labels=['Q1', 'Q2', 'Q3', 'Q4'])
    logger.info('  Created: salary_quartile')


    def normalize(series):
        (s_min, s_max) = (series.min(), series.max())
        if s_max == s_min:

            return pd.Series(0.5, index=series.index)
        return (series - s_min) / (s_max - s_min)
    weights = {'balance': 0.35, 'num_of_products': 0.2, 'tenure': 0.25, 'estimated_salary': 0.2}
    df['customer_value_score'] = sum((normalize(df[col]) * weight for (col, weight) in weights.items()))
    df['customer_value_score'] = (df['customer_value_score'] * 100).round(2)
    logger.info('  Created: customer_value_score (0-100 scale)')

    q75 = df['customer_value_score'].quantile(0.75)
    df['is_high_value'] = df['customer_value_score'] >= q75

    logger.info(f"  Created: is_high_value (threshold: {q75:.2f}, count: {df['is_high_value'].sum():,})")
    return df

def build_aggregations(df):

    """
    Build summary aggregation tables for dashboards and reporting.

    Returns
    -------
    dict[str, pd.DataFrame]
        Named aggregation DataFrames:

        - "by_geography": churn metrics by country

        - "by_age_group": churn metrics by age band


        - "by_segment": cross-tab of geography × gender × active status
    """
    logger.info('Building aggregation tables...')

    agg_tables = {}

    geo = df.groupby('geography').agg(total_customers=('customer_id', 'count'), churned_customers=('exited', 'sum'), avg_balance=('balance', 'mean'), avg_credit_score=('credit_score', 'mean'), avg_age=('age', 'mean'), avg_tenure=('tenure', 'mean'), avg_salary=('estimated_salary', 'mean')).reset_index()
    geo['churn_rate'] = (geo['churned_customers'] / geo['total_customers'] * 100).round(2)
    for col in ['avg_balance', 'avg_credit_score', 'avg_age', 'avg_tenure', 'avg_salary']:
        geo[col] = geo[col].round(2)

    geo['snapshot_date'] = pd.Timestamp.now().date()

    agg_tables['by_geography'] = geo
    logger.info(f'  agg_by_geography: {len(geo)} rows')

    age = df.groupby('age_group', observed=True).agg(total_customers=('customer_id', 'count'), churned_customers=('exited', 'sum'), avg_tenure=('tenure', 'mean'), avg_products=('num_of_products', 'mean'), avg_balance=('balance', 'mean'), avg_value_score=('customer_value_score', 'mean')).reset_index()
    age['churn_rate'] = (age['churned_customers'] / age['total_customers'] * 100).round(2)
    for col in ['avg_tenure', 'avg_products', 'avg_balance', 'avg_value_score']:
        age[col] = age[col].round(2)
    age['snapshot_date'] = pd.Timestamp.now().date()
    agg_tables['by_age_group'] = age
    logger.info(f'  agg_by_age_group: {len(age)} rows')
    seg = df.groupby(['geography', 'gender', 'is_active_member'], observed=True).agg(total_customers=('customer_id', 'count'), churned_customers=('exited', 'sum'), avg_balance=('balance', 'mean'), avg_value_score=('customer_value_score', 'mean')).reset_index()
    seg['churn_rate'] = (seg['churned_customers'] / seg['total_customers'] * 100).round(2)
    for col in ['avg_balance', 'avg_value_score']:
        seg[col] = seg[col].round(2)
    seg['snapshot_date'] = pd.Timestamp.now().date()
    agg_tables['by_segment'] = seg
    logger.info(f'  agg_by_segment: {len(seg)} rows')
    return agg_tables


def transform(raw_data):
    """

    Master transform function — runs cleaning, feature engineering,
    and aggregation on the extracted data.


    Parameters
    ----------
    raw_data : dict[str, pd.DataFrame]
        Output from extract.extract().

    Returns
    -------

    dict
        {

            "churn_clean": pd.DataFrame,       # cleaned + featured data
            "aggregations": dict[str, pd.DataFrame],

            "stock": pd.DataFrame or None,      # passthrough
        }
    """
    logger.info('=' * 60)
    logger.info('PHASE 2: TRANSFORMATION — Starting')
    logger.info('=' * 60)
    churn_df = raw_data['churn']
    churn_clean = clean_data(churn_df)
    churn_featured = engineer_features(churn_clean)
    aggregations = build_aggregations(churn_featured)

    logger.info(f'Transform complete — {len(churn_featured):,} rows, {len(churn_featured.columns)} columns, {len(aggregations)} aggregation tables')
    return {'churn_clean': churn_featured, 'aggregations': aggregations, 'stock': raw_data.get('stock')}
if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s')
    from extract import extract
    raw = extract()
    result = transform(raw)
    df = result['churn_clean']
    print(f"\n{'-' * 50}")
    print(f'Cleaned DataFrame: {df.shape}')
    print(f'\nColumns: {list(df.columns)}')

    print(f'\nSample (first 3 rows):')
    print(df.head(3).to_string())
    print(f'\nAggregation tables:')
    for (name, agg_df) in result['aggregations'].items():


        print(f'  {name}: {agg_df.shape}')
    print(f"{'-' * 50}")