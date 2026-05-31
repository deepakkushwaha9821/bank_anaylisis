

import logging
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker


import numpy as np

import pandas as pd

import seaborn as sns

import config
logger = logging.getLogger(__name__)
COLORS = {'primary': '#1B365D', 'secondary': '#4A90D9', 'accent': '#F5A623', 'success': '#27AE60', 'danger': '#E74C3C', 'light_bg': '#F7F9FC', 'grid': '#E8ECF1'}
PALETTE_BARS = ['#1B365D', '#4A90D9', '#7AB8F5', '#F5A623', '#E74C3C']
PALETTE_CHURN = ['#4A90D9', '#E74C3C']

def apply_style():
    """Apply a consistent premium style to all charts."""
    plt.rcParams.update({'figure.facecolor': 'white', 'axes.facecolor': COLORS['light_bg'], 'axes.edgecolor': COLORS['grid'], 'axes.grid': True, 'grid.color': COLORS['grid'], 'grid.alpha': 0.7, 'grid.linestyle': '--', 'font.family': 'sans-serif', 'font.sans-serif': ['Segoe UI', 'Arial', 'Helvetica'], 'font.size': 11, 'axes.titlesize': 14, 'axes.titleweight': 'bold', 'axes.labelsize': 12, 'xtick.labelsize': 10, 'ytick.labelsize': 10, 'legend.fontsize': 10, 'figure.dpi': 150, 'savefig.dpi': 150, 'savefig.bbox': 'tight', 'savefig.pad_inches': 0.3})

def chart_churn_by_geography(df, output_dir):
    """

    Grouped bar chart: total customers vs. churned, with churn rate labels.


    """
    logger.info('Generating chart: Churn Rate by Geography')

    geo = df.groupby('geography').agg(total=('customer_id', 'count'), churned=('exited', 'sum')).reset_index()


    geo['retained'] = geo['total'] - geo['churned']

    geo['churn_rate'] = (geo['churned'] / geo['total'] * 100).round(1)
    (fig, ax) = plt.subplots(figsize=(10, 6))

    x = np.arange(len(geo))


    width = 0.35
    bars1 = ax.bar(x - width / 2, geo['retained'], width, label='Retained', color=COLORS['secondary'], edgecolor='white', linewidth=0.5)
    bars2 = ax.bar(x + width / 2, geo['churned'], width, label='Churned', color=COLORS['danger'], edgecolor='white', linewidth=0.5)
    for (i, (_, row)) in enumerate(geo.iterrows()):
        ax.annotate(f"{row['churn_rate']}%", xy=(i + width / 2, row['churned']), xytext=(0, 8), textcoords='offset points', ha='center', va='bottom', fontsize=11, fontweight='bold', color=COLORS['danger'])
    ax.set_xlabel('Geography')
    ax.set_ylabel('Number of Customers')

    ax.set_title('Customer Churn Rate by Geography', pad=15)
    ax.set_xticks(x)


    ax.set_xticklabels(geo['geography'])
    ax.legend(frameon=True, fancybox=True, shadow=True)

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
    for (i, (_, row)) in enumerate(geo.iterrows()):
        ax.text(i, -max(geo['total']) * 0.05, f"n={row['total']:,}", ha='center', va='top', fontsize=9, color='gray')
    plt.tight_layout()
    path = output_dir / '01_churn_by_geography.png'

    fig.savefig(path)
    plt.close(fig)


    logger.info(f'  Saved: {path}')
    return path

def chart_churn_by_age_group(df, output_dir):
    """
    Stacked bar chart: retained vs. churned by age group.

    """
    logger.info('Generating chart: Churn by Age Group')

    age = df.groupby('age_group', observed=True).agg(total=('customer_id', 'count'), churned=('exited', 'sum')).reset_index()


    age['retained'] = age['total'] - age['churned']

    age['churn_rate'] = (age['churned'] / age['total'] * 100).round(1)
    (fig, ax) = plt.subplots(figsize=(10, 6))

    x = np.arange(len(age))
    width = 0.6

    ax.bar(x, age['retained'], width, label='Retained', color=COLORS['secondary'], edgecolor='white')
    ax.bar(x, age['churned'], width, bottom=age['retained'], label='Churned', color=COLORS['danger'], edgecolor='white')
    for (i, (_, row)) in enumerate(age.iterrows()):
        ax.text(i, row['total'] + max(age['total']) * 0.02, f"{row['churn_rate']}%", ha='center', va='bottom', fontsize=11, fontweight='bold', color=COLORS['danger'])
    ax.set_xlabel('Age Group')
    ax.set_ylabel('Number of Customers')
    ax.set_title('Customer Churn by Age Group', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(age['age_group'])
    ax.legend(frameon=True, fancybox=True, shadow=True)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
    plt.tight_layout()
    path = output_dir / '02_churn_by_age_group.png'
    fig.savefig(path)
    plt.close(fig)
    logger.info(f'  Saved: {path}')
    return path

def chart_value_distribution(df, output_dir):
    """

    Overlapping histograms: customer value score for retained vs. churned.
    """

    logger.info('Generating chart: Customer Value Distribution')
    (fig, ax) = plt.subplots(figsize=(10, 6))
    retained = df[~df['exited']]['customer_value_score']
    churned = df[df['exited']]['customer_value_score']
    bins = np.linspace(0, 100, 30)
    ax.hist(retained, bins=bins, alpha=0.7, label=f'Retained (n={len(retained):,})', color=COLORS['secondary'], edgecolor='white', linewidth=0.5)
    ax.hist(churned, bins=bins, alpha=0.7, label=f'Churned (n={len(churned):,})', color=COLORS['danger'], edgecolor='white', linewidth=0.5)
    ax.axvline(retained.median(), color=COLORS['primary'], linestyle='--', linewidth=2, label=f'Retained median: {retained.median():.1f}')
    ax.axvline(churned.median(), color=COLORS['accent'], linestyle='--', linewidth=2, label=f'Churned median: {churned.median():.1f}')

    ax.set_xlabel('Customer Value Score')

    ax.set_ylabel('Count')
    ax.set_title('Customer Value Score Distribution: Retained vs. Churned', pad=15)
    ax.legend(frameon=True, fancybox=True, shadow=True, loc='upper right')
    plt.tight_layout()

    path = output_dir / '03_value_distribution.png'

    fig.savefig(path)
    plt.close(fig)
    logger.info(f'  Saved: {path}')
    return path

def chart_correlation_heatmap(df, output_dir):
    """
    Heatmap of correlations between numeric features and churn.
    """
    logger.info('Generating chart: Correlation Heatmap')
    numeric_cols = ['credit_score', 'age', 'tenure', 'balance', 'num_of_products', 'estimated_salary', 'customer_value_score', 'has_credit_card', 'is_active_member', 'exited']
    corr_df = df[numeric_cols].copy()
    for col in corr_df.select_dtypes(include=['bool']).columns:
        corr_df[col] = corr_df[col].astype(int)
    corr_matrix = corr_df.corr()
    (fig, ax) = plt.subplots(figsize=(12, 9))
    cmap = sns.diverging_palette(220, 10, as_cmap=True)
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
    sns.heatmap(corr_matrix, mask=mask, cmap=cmap, vmin=-1, vmax=1, center=0, annot=True, fmt='.2f', square=True, linewidths=0.5, linecolor='white', cbar_kws={'shrink': 0.8, 'label': 'Correlation'}, ax=ax)
    labels = ['Credit Score', 'Age', 'Tenure', 'Balance', '# Products', 'Salary', 'Value Score', 'Has Card', 'Active', 'Churned']
    ax.set_xticklabels(labels, rotation=45, ha='right')
    ax.set_yticklabels(labels, rotation=0)
    ax.set_title('Feature Correlation Heatmap', pad=20)
    plt.tight_layout()
    path = output_dir / '04_correlation_heatmap.png'


    fig.savefig(path)
    plt.close(fig)
    logger.info(f'  Saved: {path}')
    return path

def generate_reports(df=None):
    """

    Generate all report charts.

    Parameters

    ----------


    df : pd.DataFrame, optional
        Cleaned churn DataFrame. If None, reads from the clean CSV.

    Returns
    -------
    list[Path]

        Paths to the generated chart files.
    """

    logger.info('=' * 60)

    logger.info('PHASE 5: REPORTING — Starting')

    logger.info('=' * 60)
    apply_style()


    output_dir = config.REPORTS_DIR
    output_dir.mkdir(exist_ok=True)
    if df is None:
        csv_path = config.CLEAN_CSV_PATH

        if not csv_path.exists():
            raise FileNotFoundError(f'Clean CSV not found: {csv_path}. Run the pipeline first: python pipeline.py')
        df = pd.read_csv(csv_path)
        for col in ['has_credit_card', 'is_active_member', 'exited', 'is_high_value']:
            if col in df.columns:
                df[col] = df[col].astype(bool)
    chart_paths = []

    chart_paths.append(chart_churn_by_geography(df, output_dir))
    chart_paths.append(chart_churn_by_age_group(df, output_dir))


    chart_paths.append(chart_value_distribution(df, output_dir))


    chart_paths.append(chart_correlation_heatmap(df, output_dir))


    logger.info(f'\nAll {len(chart_paths)} charts saved to: {output_dir}')
    logger.info('PHASE 5: REPORTING — Complete')
    return chart_paths

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s')


    paths = generate_reports()

    print(f"\n{'-' * 50}")
    print(f'Generated {len(paths)} report(s):')

    for p in paths:

        print(f'  >> {p}')
    print(f"{'-' * 50}")