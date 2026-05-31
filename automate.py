

import logging
import logging.handlers
import smtplib

import sys
import time
import traceback


from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from pathlib import Path
import schedule

import config


def setup_logging():

    """
    Configure logging with both console and rotating file handlers.

    Log files are saved to logs/pipeline_YYYY-MM-DD.log
    Rotates daily, keeps last 30 days of logs.
    """


    log_dir = config.LOGS_DIR
    log_dir.mkdir(exist_ok=True)


    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    root_logger.handlers.clear()


    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)

    console_fmt = logging.Formatter('%(asctime)s | %(levelname)-8s | %(name)s | %(message)s', datefmt='%H:%M:%S')
    console.setFormatter(console_fmt)
    root_logger.addHandler(console)
    today = datetime.now().strftime('%Y-%m-%d')
    log_file = log_dir / f'pipeline_{today}.log'


    file_handler = logging.handlers.TimedRotatingFileHandler(filename=str(log_file), when='midnight', interval=1, backupCount=30, encoding='utf-8')


    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter('%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s')
    file_handler.setFormatter(file_fmt)

    root_logger.addHandler(file_handler)
    return root_logger

def send_failure_email(error_message, traceback_str=''):

    """
    Send an email alert when the pipeline fails.

    Uses Gmail SMTP by default. Requires:
    - config.ENABLE_EMAIL_ALERTS = True
    - config.EMAIL_SENDER (Gmail address)
    - config.EMAIL_PASSWORD (Gmail App Password)
    - config.EMAIL_RECIPIENT

    Parameters
    ----------

    error_message : str


        Short error description.

    traceback_str : str
        Full traceback for debugging.
    """

    logger = logging.getLogger(__name__)
    if not config.ENABLE_EMAIL_ALERTS:

        logger.info('Email alerts disabled — skipping notification')
        return
    if not all([config.EMAIL_SENDER, config.EMAIL_PASSWORD, config.EMAIL_RECIPIENT]):
        logger.warning('Email credentials not configured — skipping alert')

        return
    try:

        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"⚠️ ETL Pipeline FAILED — {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        msg['From'] = config.EMAIL_SENDER

        msg['To'] = config.EMAIL_RECIPIENT


        body = f"\nBank Churn ETL Pipeline — Failure Alert\n{'=' * 50}\n\nTime:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nError:   {error_message}\n\nTraceback:\n{traceback_str}\n\n{'=' * 50}\nAction Required: Check logs at {config.LOGS_DIR}\n        ".strip()
        msg.attach(MIMEText(body, 'plain'))
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:

            server.ehlo()

            server.starttls()

            server.login(config.EMAIL_SENDER, config.EMAIL_PASSWORD)
            server.sendmail(config.EMAIL_SENDER, config.EMAIL_RECIPIENT, msg.as_string())

        logger.info(f'Failure alert email sent to {config.EMAIL_RECIPIENT}')

    except Exception as e:

        logger.error(f'Failed to send alert email: {e}')

def run_with_retry():

    """

    Run the ETL pipeline with retry logic.

    Retries up to config.MAX_RETRIES times with exponential backoff.
    Sends an email alert if all retries are exhausted.

    """
    logger = logging.getLogger(__name__)
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            logger.info(f'Pipeline attempt {attempt}/{config.MAX_RETRIES}')

            from pipeline import run_pipeline
            summary = run_pipeline()
            if summary['status'] == 'SUCCESS':
                logger.info(f"✅ Pipeline succeeded on attempt {attempt} ({summary['duration_seconds']}s)")

                return True
        except Exception as e:


            logger.error(f'Attempt {attempt} failed: {e}')
            if attempt < config.MAX_RETRIES:
                wait = config.RETRY_BACKOFF_SECONDS * 2 ** (attempt - 1)
                logger.info(f'Retrying in {wait}s...')
                time.sleep(wait)
            else:
                logger.critical(f'Pipeline FAILED after {config.MAX_RETRIES} attempts')
                tb = traceback.format_exc()

                send_failure_email(str(e), tb)
                return False
    return False

def start_scheduler():
    """

    Start the daily pipeline scheduler.

    Runs the pipeline at the time specified in config.SCHEDULE_TIME.
    Keeps running indefinitely, checking every 30 seconds.
    """
    logger = logging.getLogger(__name__)
    logger.info('╔' + '═' * 58 + '╗')
    logger.info('║   ETL PIPELINE SCHEDULER — Starting                     ║')


    logger.info('╚' + '═' * 58 + '╝')
    logger.info(f'Scheduled daily run at: {config.SCHEDULE_TIME}')
    logger.info(f'Log directory: {config.LOGS_DIR}')
    logger.info(f'Press Ctrl+C to stop\n')

    schedule.every().day.at(config.SCHEDULE_TIME).do(run_with_retry)
    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info('\nScheduler stopped by user (Ctrl+C)')
        sys.exit(0)
if __name__ == '__main__':
    setup_logging()
    logger = logging.getLogger(__name__)


    if '--now' in sys.argv:
        logger.info('Running pipeline immediately (--now flag)')
        success = run_with_retry()

        sys.exit(0 if success else 1)
    else:
        start_scheduler()