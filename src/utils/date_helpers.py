"""
Date and time utility functions
"""
from datetime import date, datetime, timedelta
from pytz import timezone, utc

from src.config.settings import TIMEZONE, TIMEZONE_OFFSET_FROM_GMT


def now_to_datetime_string():
    """Returns the current date and time as a string"""
    # Adding +1 minute prevents timing conflicts during sync
    now = datetime.now() + timedelta(minutes=1)
    return now.strftime('%Y-%m-%dT%H:%M:%S')


def datetime_to_string(date_time):
    """Returns dateTime as a string"""
    return date_time.strftime('%Y-%m-%dT%H:%M:%S')


def date_to_string(date_obj):
    """Returns date as a string"""
    return date_obj.strftime('%Y-%m-%d')


def parse_datetime_string(datetime_string, format_str):
    """Returns dateTimeString as a datetime object"""
    return datetime.strptime(datetime_string, format_str)


def parse_date_string(date_string, format_str):
    """Returns dateString as a datetime object with date only"""
    return datetime.strptime(date_string, format_str)


def add_timezone_for_notion(datetime_string):
    """Adds timezone indicator to dateTimeString"""
    return datetime_string + TIMEZONE_OFFSET_FROM_GMT


def convert_timezone(date_time, new_timezone=TIMEZONE):
    """Convert dateTime from UTC to newTimeZone"""
    return utc.localize(date_time).astimezone(timezone(new_timezone)).replace(tzinfo=None)