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

import pprint
from datetime import datetime, timedelta

from .data_analyzer import analyze_data
from .data_formatter import format_data_with_parser
from .data_getter import get_data
from .message_builder import build_message
from .notification_system import notify


def monitor(
    start_date=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
    end_date=datetime.now().strftime("%Y-%m-%d"),
    node_ids=None,
    project="ALL",
    no_email=False,
):

    # Step 1: Get the data
    print(f"--Beginning data retrieval--")
    data_frame = get_data(start_date, end_date, project, node_ids)
    print(f"--Data retrieval complete--")

    # Step 2: Format the data
    print(f"--Beginning data formatting--")
    formatted_data = format_data_with_parser(data_frame)
    print(f"--Data formatting complete--")

    # Step 3: Analyze the data
    print(f"--Beginning data analysis--")
    analysis_dict = analyze_data(formatted_data)
    print(f"--Data analysis complete--")

    # Step 4: Build notification messages
    print(f"--Beginning message building--")
    message_dict = build_message(analysis_dict)
    print(f"--Message building complete--")

    # Step 5: Notify the user with the message
    print("\n--Notification Results--\n")
    notify(message_dict, no_email=no_email)
