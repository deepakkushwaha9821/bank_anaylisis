

import logging


import time
from datetime import datetime, timezone
import config
from extract import extract
from transform import transform
from load import load
logger = logging.getLogger(__name__)

def run_pipeline():
    """
    Execute the full ETL pipeline.

    Phases:
    1. Extract — read raw data from CSV (and optionally API)
    2. Transform — clean, feature-engineer, aggregate

    3. Load — write to PostgreSQL + save CSV/Parquet backups

    Returns
    -------
    dict
        Summary of the pipeline run:
        {
            "status": "SUCCESS" | "FAILED",
            "started_at": datetime,

            "finished_at": datetime,
            "duration_seconds": float,
            "phases": {

                "extract": {"status", "duration", "rows"},


                "transform": {"status", "duration", "rows", "features"},
                "load": {"status", "duration"},
            },
            "error": str or None,

        }
    """
    summary = {'status': 'RUNNING', 'started_at': datetime.now(timezone.utc), 'finished_at': None, 'duration_seconds': 0, 'phases': {}, 'error': None}
    pipeline_start = time.perf_counter()


    logger.info('+' + '=' * 58 + '+')
    logger.info('|   BANK CHURN ETL PIPELINE -- Starting                    |')

    logger.info('+' + '=' * 58 + '+')
    try:
        t0 = time.perf_counter()
        raw_data = extract()
        t1 = time.perf_counter()
        summary['phases']['extract'] = {'status': 'SUCCESS', 'duration': round(t1 - t0, 2), 'rows': len(raw_data['churn'])}
        t0 = time.perf_counter()

        transformed_data = transform(raw_data)
        t1 = time.perf_counter()
        churn_df = transformed_data['churn_clean']

        summary['phases']['transform'] = {'status': 'SUCCESS', 'duration': round(t1 - t0, 2), 'rows': len(churn_df), 'features': len(churn_df.columns), 'aggregation_tables': len(transformed_data['aggregations'])}
        t0 = time.perf_counter()
        load(transformed_data)
        t1 = time.perf_counter()
        summary['phases']['load'] = {'status': 'SUCCESS', 'duration': round(t1 - t0, 2)}

        summary['status'] = 'SUCCESS'
    except Exception as e:
        summary['status'] = 'FAILED'
        summary['error'] = str(e)
        logger.error(f'Pipeline FAILED: {e}', exc_info=True)

        raise

    finally:
        pipeline_end = time.perf_counter()
        summary['finished_at'] = datetime.now(timezone.utc)
        summary['duration_seconds'] = round(pipeline_end - pipeline_start, 2)
        logger.info('')
        logger.info('+' + '-' * 58 + '+')
        logger.info('|   PIPELINE SUMMARY                                       |')
        logger.info('+' + '-' * 58 + '+')
        logger.info(f"|  Status:   {summary['status']:<47}|")
        logger.info(f"|  Duration: {summary['duration_seconds']:<47}|")
        logger.info('|' + ' ' * 58 + '|')
        for (phase_name, phase_info) in summary['phases'].items():
            status = phase_info['status']

            duration = phase_info['duration']
            extra = ''
            if 'rows' in phase_info:
                extra = f" ({phase_info['rows']:,} rows)"
            logger.info(f'|  {phase_name:<12} {status:<10} {duration:>6.2f}s{extra:<27}|')
        if summary['error']:
            logger.info('|' + ' ' * 58 + '|')


            error_msg = summary['error'][:50]
            logger.info(f'|  Error: {error_msg:<50}|')
        logger.info('+' + '-' * 58 + '+')
    return summary

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s')


    summary = run_pipeline()
    if summary['status'] == 'SUCCESS':
        print('\n[OK] Pipeline completed successfully!')
    else:
        print(f"\n[FAILED] Pipeline failed: {summary['error']}")
        exit(1)