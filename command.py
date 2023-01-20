# -*- coding: utf-8 -*-

# @File    : command.py
# @Date    : 2023-01-18
# @Author  : 王超逸
# @Brief   :

from mytime import MyDateTime, FileCacheLine
from datetime import timedelta
import time as _time


def default_context():
    if not hasattr(default_context, "cache"):
        default_context.cache = MyDateTime.get_default_context()
    return default_context.cache


def _today_or_yesterday(data_cache: FileCacheLine, ts=..., boundary=0):
    if ts is ...:
        ts = _time.time()
    data_cache.calc_timestamp_until(ts)
    while data_cache.file_data[-1] > ts:
        data_cache.file_data.pop()
    if ts - data_cache.file_data[-1] < timedelta(hours=boundary).total_seconds():
        data_cache.file_data.pop()


def good_night(dt: timedelta = timedelta(minutes=40)):
    with default_context().edit_date() as data_cache:
        ts = _time.time()
        next_day_start_time = ts + dt.total_seconds()
        _today_or_yesterday(data_cache, ts, boundary=12)
        data_cache.file_data.append(int(next_day_start_time))


def set_today_hours(hours: float):
    with default_context().edit_date() as data_cache:
        _today_or_yesterday(data_cache, boundary=4)
        data_cache.file_data.append(int(data_cache.file_data[-1] + 3600 * hours))


def today_is_yesterday():
    with default_context().edit_date() as data_cache:
        ts = _time.time()
        _today_or_yesterday(data_cache, ts=ts)
        data_cache.file_data[-1] = ts + 3600  # 将今天的结束时间调整到一小时后
