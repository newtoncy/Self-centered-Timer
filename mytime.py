# -*- coding: utf-8 -*-
# @File    : mytime.py
# @Date    : 2023-01-17
# @Author  : 王超逸
# @Brief   :
from __future__ import annotations

import sys
from collections import defaultdict
from functools import total_ordering
from datetime import datetime, timedelta, timezone, tzinfo
import time
import math
from pathlib import WindowsPath, PosixPath, Path
import json
from typing import Callable

import path_def

CHINA_TIMEZONE = timezone(timedelta(hours=8))
UTC_TIMEZONE = timezone(timedelta())


#################################################
def _check_int_field(value):
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        raise TypeError('integer argument expected, got float')
    try:
        value = value.__index__()
    except AttributeError:
        pass
    else:
        if not isinstance(value, int):
            raise TypeError('__index__ returned non-int (type %s)' %
                            type(value).__name__)
        return value
    orig = value
    try:
        value = value.__int__()
    except AttributeError:
        pass
    else:
        if not isinstance(value, int):
            raise TypeError('__int__ returned non-int (type %s)' %
                            type(value).__name__)
        import warnings
        warnings.warn("an integer is required (got type %s)" %
                      type(orig).__name__,
                      DeprecationWarning,
                      stacklevel=2)
        return value
    raise TypeError('an integer is required (got type %s)' %
                    type(value).__name__)


class FileCacheLine:
    """
    表示一个文件的缓存
    """

    def __init__(self, path=None):
        self.path: Path = path
        self._file_data: None | list = None

    def __bool__(self):
        return bool(self.path)

    @property
    def file_data(self):
        if self._file_data is not None:
            return self._file_data
        self.reload()
        return self._file_data

    def _bin_search(self, t: float):
        day_time_list = self.file_data
        assert t >= day_time_list[0]
        a = 0
        b = len(day_time_list)
        while b - a != 1:
            mid = (a + b) // 2
            if day_time_list[mid] <= t:
                a = mid
            else:
                b = mid
        assert 0 <= a < b < len(day_time_list)
        return a, t - day_time_list[a]

    def get_last_time_last_day(self, zero_point_time: int):
        day_time_list = self.file_data
        if not day_time_list:
            day_time_list.append(zero_point_time)
        last_time = day_time_list[-1]
        day = len(day_time_list) - 1
        return last_time, day

    def get_zero_point(self, zero_point_time: int):
        if self.file_data:
            return self.file_data[0]
        return zero_point_time

    def get_day(self, t: float, default_day_sec: int, zero_point_time: int):
        day_time_list = self.file_data
        assert t >= self.get_zero_point(zero_point_time)
        if day_time_list and day_time_list[-1] > t:
            return self._bin_search(t)

        last_time, day = self.get_last_time_last_day(zero_point_time)
        day += (int(t) - last_time) // default_day_sec  # python整除，浮点数作为操作数，则是浮点数
        return round(day), (t - last_time) % default_day_sec

    calc_timestamp_until: Callable[[float], None]

    def _calc_timestamp_until(self, t, default_day_sec: int, zero_point_time: int):
        day_time_list = self.file_data
        last_time, _ = self.get_last_time_last_day(zero_point_time)
        while last_time + default_day_sec < t:
            last_time += default_day_sec
            day_time_list.append(last_time)

    def get_timestamp(self, total_day: int, sec: float, default_day_sec: int, zero_point_time: int):
        last_time, last_day = self.get_last_time_last_day(zero_point_time)
        if total_day > last_day:
            return (total_day - last_day) * default_day_sec + last_time + sec
        return self.file_data[total_day] + sec

    @property
    def bak_file_path(self):
        bak_file_name = self.path.name + ".bak"
        return self.path.parent / bak_file_name

    def reload(self):
        load_path = self.path
        if not load_path.exists():
            load_path = self.bak_file_path
        if not load_path.exists():
            self._file_data = []
            return

        with load_path.open("rt", encoding="utf-8") as fp:
            try:
                self._file_data = json.load(fp)["day_time_map"]
            except Exception as e:
                print(e)
                self._file_data = []
                return

    def save(self):
        if not self or self._file_data is None:
            # 没有更改
            return False

        assert self
        # 确保路径存在
        if not self.path.parent.exists():
            self.path.parent.mkdir(parents=True)
        # 备份
        if self.path.exists():
            if self.bak_file_path.exists():
                self.bak_file_path.unlink()
            self.path.rename(self.bak_file_path)
        data = {"day_time_map": self._file_data}
        with self.path.open("wt", encoding="utf-8") as fp:
            json.dump(data, fp)
        return True


class DatetimeContext:
    """
    表示一个历法规则
    """
    all_instance = {}
    path_map = defaultdict(lambda: {"context_list": [], "file_cache": FileCacheLine()})

    def __new__(cls, zero_point: int, hour_per_day: float, day_per_cycle: int, cycle_per_stage, save_path: Path):
        self = object.__new__(cls)
        self._save_path = save_path.resolve()
        self._cycle_per_stage = cycle_per_stage
        self._day_per_cycle = day_per_cycle
        self._hour_per_day = hour_per_day
        self._zero_point = zero_point
        if self in cls.all_instance:
            return cls.all_instance[self]

        self._bind_dt = {}
        cls.all_instance[self] = self
        cls.path_map[self._save_path]["context_list"].append(self)
        if not cls.path_map[self._save_path]["file_cache"]:
            cls.path_map[self._save_path]["file_cache"].path = self._save_path
        self._file_cache = cls.path_map[self._save_path]["file_cache"]
        return self

    def bind(self, dt):
        self._bind_dt[id(dt)] = dt

    def unbind(self, dt):
        del self._bind_dt[id(dt)]

    def on_change(self, save=True):
        if save:
            self._file_cache.save()
        for context in self.path_map[self.save_path]["context_list"]:
            assert isinstance(context, DatetimeContext)
            for obj in context._bind_dt.values():
                obj.re_calc_datetime()

    class EditDate:
        def __init__(self, context: DatetimeContext):
            self.context = context

        def __enter__(self):
            def helper_func(t=...):
                if t is ...:
                    t = time.time()
                self.context._file_cache._calc_timestamp_until(t, int(self.context.hour_per_day * 3600),
                                                               self.context.zero_point)

            self.context._file_cache.calc_timestamp_until = helper_func
            return self.context._file_cache

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.context.on_change()

    def edit_date(self):
        return self.EditDate(self)

    def get_total_day(self, t: float):
        return self._file_cache.get_day(t, int(self.hour_per_day * 3600), self.zero_point)

    def get_tuple(self):
        return self._zero_point, self._hour_per_day, self._day_per_cycle, self._cycle_per_stage, self._save_path

    def __eq__(self, other: DatetimeContext):
        return self.get_tuple() == other.get_tuple()

    def __hash__(self):
        return hash(self.get_tuple())

    @property
    def save_path(self):
        return self._save_path

    @property
    def zero_point(self):
        return self._zero_point

    @property
    def hour_per_day(self):
        return self._hour_per_day

    @property
    def day_per_cycle(self):
        return self._day_per_cycle

    @property
    def cycle_per_stage(self):
        return self._cycle_per_stage


Default_File_Path = None


def _get_default_context():
    path = Default_File_Path
    if not path:
        path = path_def.ENTRY_POINT_DIR / "saves" / "save_data.txt"
    return DatetimeContext(int(datetime(2023, 1, 16, 18, tzinfo=CHINA_TIMEZONE).timestamp()), 26, 7, 4, path)


def _check_time_fields(hour, minute, second, microsecond, context: DatetimeContext):
    hour = _check_int_field(hour)
    minute = _check_int_field(minute)
    second = _check_int_field(second)
    microsecond = _check_int_field(microsecond)
    if not 0 <= hour:
        raise ValueError(f'hour must more than 0', hour)
    if not 0 <= minute <= 59:
        raise ValueError('minute must be in 0..59', minute)
    if not 0 <= second <= 59:
        raise ValueError('second must be in 0..59', second)
    if not 0 <= microsecond <= 999999:
        raise ValueError('microsecond must be in 0..999999', microsecond)
    return hour, minute, second, microsecond


def _check_date_field(stage, cycle, day, context: DatetimeContext):
    stage = _check_int_field(stage)
    cycle = _check_int_field(cycle)
    day = _check_int_field(day)
    if 1 <= stage and 1 <= cycle <= context.cycle_per_stage and 1 <= day <= context.day_per_cycle:
        return stage, cycle, day
    raise ValueError()


@total_ordering
class MyDateTime:
    _default_context = None

    @classmethod
    def get_default_context(cls):
        if cls._default_context is None:
            cls._default_context = _get_default_context()
        return cls._default_context

    def __init__(self, stage: int = 1, cycle: int = 1, day: int = 1, hour=0, minute=0, second=0,
                 microsecond=0, context=..., **kwargs):
        if context is ...:
            context = self.get_default_context()
        context.bind(self)
        if not kwargs.get("skip_check", False):
            hour, minute, second, microsecond = _check_time_fields(
                hour, minute, second, microsecond, context)

            stage, cycle, day = _check_date_field(stage, cycle, day, context)
        self._stage = stage
        self._cycle = cycle
        self._day = day
        self._hour = hour
        self._minute = minute
        self._second = second
        self._microsecond = microsecond
        self._hashcode = -1
        self._context = context
        self._timestamp = kwargs.get("_force_timestamp")
        if self._timestamp is None:
            self.timestamp()
        self.re_calc_datetime()  # 要判断一个日期是合法的，太难了，所以重新从时间戳中计算一次

    def re_calc_datetime(self):
        self._stage, self._cycle, self._day, self._hour, self._minute, self._second, self._microsecond \
            = self._from_timestamp_internal(self._timestamp, self._context)

    @classmethod
    def _from_timestamp_internal(cls, t: float, context: DatetimeContext):
        total_day, t = context.get_total_day(t)
        frac, t = math.modf(t)
        t = int(t)
        us = round(frac * 1e6)
        if us >= 1000000:
            t += 1
            us -= 1000000
        elif us < 0:
            t -= 1
            us += 1000000

        ss = t % 60
        t //= 60
        mm = t % 60
        t //= 60
        hh = t

        d = total_day % context.day_per_cycle + 1
        total_day //= context.day_per_cycle
        c = total_day % context.cycle_per_stage + 1
        s = total_day // context.cycle_per_stage + 1
        return s, c, d, hh, mm, ss, us

    @classmethod
    def from_timestamp(cls, t: float, context=...):
        if context is ...:
            context = cls.get_default_context()
        if t - context.zero_point < 0:
            raise ValueError("纪元前时间无定义")

        return cls(*cls._from_timestamp_internal(t, context), _force_timestamp=t)

    def timestamp(self) -> float:
        if self._timestamp is not None:
            return self._timestamp
        t = 0
        context = self._context

        t += self.stage - 1
        t *= context.cycle_per_stage
        t += self.cycle - 1
        t *= context.day_per_cycle
        t += self.day - 1
        total_day = t
        t = 0
        t += self.hour
        t *= 60
        t += self.minute
        t *= 60
        t += self.second
        t += self.microsecond * 1e-6
        sec = t
        self._timestamp = context._file_cache \
            .get_timestamp(total_day, sec,
                           int(context.hour_per_day * 3600),
                           context.zero_point)
        return self._timestamp

    def __hash__(self):
        hash(self.timestamp())

    def __lt__(self, other):
        if isinstance(other, MyDateTime):
            return self.timestamp() < other.timestamp()

        if isinstance(other, datetime):
            if other.tzinfo and other.tzinfo.utcoffset(other):
                return self.timestamp() < other.timestamp()
            raise TypeError("必须是带有时区的绝对时间")
        raise TypeError("不支持比较")

    def __eq__(self, other):
        if isinstance(other, MyDateTime):
            return self.timestamp() == other.timestamp()

        if isinstance(other, datetime):
            if other.tzinfo and other.tzinfo.utcoffset(other):
                return self.timestamp() == other.timestamp()
            raise TypeError("必须是带有时区的绝对时间")
        raise TypeError("不支持比较")

    def __add__(self, other: timedelta):
        return self.from_timestamp(self.timestamp() + other.total_seconds())

    __radd__ = __add__

    def __sub__(self, other: timedelta | MyDateTime | datetime):
        if isinstance(other, timedelta):
            return self.from_timestamp(self.timestamp() - other.total_seconds())

        if isinstance(other, MyDateTime):
            other_timestamp = other.timestamp()
        elif isinstance(other, datetime):
            other_timestamp = other.timestamp()
        else:
            raise TypeError()
        return timedelta(seconds=self.timestamp() - other_timestamp)

    def __rsub__(self, other):
        return -(self - other)

    @property
    def hour(self):
        """hour (0-23)"""
        return self._hour

    @property
    def minute(self):
        """minute (0-59)"""
        return self._minute

    @property
    def second(self):
        """second (0-59)"""
        return self._second

    @property
    def microsecond(self):
        """microsecond (0-999999)"""
        return self._microsecond

    @property
    def day(self):
        return self._day

    @property
    def cycle(self):
        return self._cycle

    @property
    def stage(self):
        return self._stage

    @property
    def context(self):
        return self._context

    @classmethod
    def from_datetime(cls, dt: datetime) -> MyDateTime:
        if dt.tzinfo and dt.tzinfo.utcoffset(dt):
            return cls.from_timestamp(dt.timestamp())
        raise TypeError("必须是带有时区的绝对时间")

    def to_datetime(self, tzinfo_: tzinfo = None):
        return datetime.fromtimestamp(self.timestamp(),
                                      tz=tzinfo_ if tzinfo_ else datetime(2000, 1, 1).astimezone().tzinfo)

    @classmethod
    def now(cls) -> MyDateTime:
        return cls.from_timestamp(time.time())

    def __str__(self):
        return f"{self.stage}-{self.cycle}-{self.day} " + \
               f"{self.hour}:{self.minute}:{self.microsecond:06}"

    def __repr__(self):
        return f"<MyDatetime {self!s}>"


__all__ = ["DatetimeContext", "MyDateTime"]

# 测试样例
# with MyDateTime.get_default_context().edit_date() as c:
#     a = c.file_data
#     while len(a) < 2:
#         a.append(None)
#     a[0] = datetime(2000, 1, 1, tzinfo=CHINA_TIMEZONE).timestamp()
#     a[1] = (datetime.now().astimezone() + timedelta(minutes=1)).timestamp()
#
# t = time.time()
# dt = datetime.fromtimestamp(t)
# dt = dt.astimezone()
# mydt = MyDateTime.from_datetime(dt)
# print(repr(mydt))
# assert mydt == dt
# mydt2 = MyDateTime(mydt.stage, mydt.cycle, mydt.day, mydt.hour, mydt.minute, mydt.second, mydt.microsecond)
# assert mydt == mydt2
# mydt += timedelta(hours=1)
# print(repr(mydt))
# assert mydt > dt
# assert dt < mydt
# dt += timedelta(hours=1)
# assert mydt == dt
# zp = datetime.fromtimestamp(MyDateTime.default_context.zero_point, tz=CHINA_TIMEZONE)
# assert mydt - zp == dt - zp
# print(mydt.to_datetime())
# assert mydt.to_datetime() - zp == dt - zp
# assert zp - mydt == -(dt - zp)
