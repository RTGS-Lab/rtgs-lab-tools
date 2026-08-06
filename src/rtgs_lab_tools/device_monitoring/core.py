"""
Overview:
    - This file is an implementation of the core functionality of device monitoring
Task Description:
    - should organize all the functions from within data_getter, date_formatter, data_analyzer, message_builder, notification system
    - should create the function that the cli.py wraps
Work Flow:
    - data_getter->data_formatter->data_analyzer->message_builder->notification_system
To run:
    - python -m rtgs_lab_tools.device_monitoring.core
"""

import os
import pprint
from datetime import datetime, timedelta

from .config import (
    DATA_COLLECTION_WINDOW_DAYS,
    STEP_TIMEOUT_DATABASE_WRITE,
    STEP_TIMEOUT_DATA_ANALYSIS,
    STEP_TIMEOUT_DATA_FORMATTING,
    STEP_TIMEOUT_DATA_RETRIEVAL,
    STEP_TIMEOUT_MESSAGE_BUILD,
    STEP_TIMEOUT_NOTIFY,
)
from .data_analyzer import analyze_data
from .data_formatter import format_data_with_parser
from .data_getter import get_data
from .message_builder import build_message
from .notification_system import notify
from .timezones import now_utc, utc_stamp
from .watchdog import step_timeout

from .web_app.models import app
from .web_app.produce_db import init_db, build_db, build_logger_info, build_app_config


def _run_timestamp():
    """The monitoring_timestamp every row of this run is filed under.

    scheduled_device_monitoring.sh exports DEVICEMON_RUN_TIMESTAMP once and
    keeps it fixed across retries, so a retried report overwrites the partial
    rows left by the failed attempt instead of adding a second, near-duplicate
    entry to the web app's timestamp list. Falls back to the current time when
    run by hand.

    UTC, like every other timestamp the pipeline stores -- the shell exports it
    with `date -u` for the same reason.
    """
    return os.getenv("DEVICEMON_RUN_TIMESTAMP") or utc_stamp()

def monitor(
    start_date=(now_utc() - timedelta(days=DATA_COLLECTION_WINDOW_DAYS)).strftime(
        "%Y-%m-%d"
    ),
    end_date=now_utc().strftime("%Y-%m-%d"),
    node_ids=None,
    project="ALL",
    no_email=False,
):

    monitoring_timestamp = _run_timestamp()
    print(f"--Monitoring run timestamp: {monitoring_timestamp}--")

    # Step 1: Get the data
    print(f"--Beginning data retrieval--")
    with step_timeout(STEP_TIMEOUT_DATA_RETRIEVAL, "Data retrieval"):
        data_frame = get_data(start_date, end_date, project, node_ids)
    print(f"--Data retrieval complete--")
    data_frame.to_csv('raw_data.csv')
    # Step 2: Format the data
    print(f"--Beginning data formatting--")
    with step_timeout(STEP_TIMEOUT_DATA_FORMATTING, "Data formatting"):
        formatted_data = format_data_with_parser(data_frame)
    print(f"--Data formatting complete--")

    formatted_data["parsed_data"].to_csv('parsed_data.csv')
    formatted_data["error_data_new"].to_csv('parsed_errors.csv')

    # Step 3: Analyze the data
    print(f"--Beginning data analysis--")
    with step_timeout(STEP_TIMEOUT_DATA_ANALYSIS, "Data analysis"):
        analysis_dict = analyze_data(formatted_data)
    print(f"--Data analysis complete--")

    # Step 3.5: Add data to SQLite database
    print(f"--Beginning adding data to SQLite database--")
    with step_timeout(STEP_TIMEOUT_DATABASE_WRITE, "Database write"):
        with app.app_context():
            init_db()
            build_db(analysis_dict, monitoring_timestamp)
            build_logger_info(analysis_dict)
            build_app_config()
    print(f"--Addition to SQLite database complete--")

    # Step 4: Build notification messages
    print(f"--Beginning message building--")
    with step_timeout(STEP_TIMEOUT_MESSAGE_BUILD, "Message building"):
        message_dict = build_message(analysis_dict)
    print(f"--Message building complete--")

    # Step 5: Notify the user with the message
    print("\n--Notification Results--\n")
    with step_timeout(STEP_TIMEOUT_NOTIFY, "Notification"):
        notify(message_dict, no_email=no_email)
