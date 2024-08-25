import logging
from datetime import datetime

logger = logging.getLogger(__name__)

INTEGER_TYPE = "integer"
DATE_TYPE = "date"


def parse_date(value):
    try:
        return datetime.strptime(value, "%d-%m-%Y")
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            logger.error(f"Cannot parse date: {value}")
            return None


def parse_int(value):
    try:
        return int(value)
    except ValueError:
        logger.error(f"Cannot parse int: {value}")
        return None


def as_type(data_type, value):
    if data_type:
        if data_type.lower() == INTEGER_TYPE:
            return parse_int(value)
        elif data_type.lower() == DATE_TYPE:
            return parse_date(value)
    return value
