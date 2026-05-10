
from datetime import date, datetime
from decimal import Decimal


"""
def orm_to_dict(model):
    return {
        column.name: getattr(model, column.name)
        for column in model.__table__.columns
    }
"""


def orm_to_dict(model):
    result = {}
    for column in model.__table__.columns:
        value = getattr(model, column.name)
        if isinstance(value, datetime):
            value = value.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        elif isinstance(value, date):
            value = value.strftime(
                "%Y-%m-%d"
            )
        elif isinstance(value, Decimal):
            value = float(value)
        result[column.name] = value
    return result
