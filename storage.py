import json
import os
import calendar
from datetime import datetime
import pytz

DATA_FILE = "data.json"
RECORDS_FILE = "records.json"
NPT = pytz.timezone('Asia/Kathmandu')

# Daily goal used for streak evaluation — matches the 🔥 threshold in !streak
STUDY_GOAL_SECONDS = 18000  # 5 hours

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def get_now():
    return datetime.now(NPT)


def load_json(filename, default):
    if not os.path.exists(filename):
        return default
    with open(filename, 'r') as f:
        try:
            return json.load(f)
        except Exception:
            return default


def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)


def _date_str(dt):
    return f"{dt.year}-{dt.month:02d}-{dt.day:02d}"


def _day_total(records, dt):
    """Look up total studied seconds for a given date from records.json."""
    y, m, d = str(dt.year), f"{dt.month:02d}", f"{dt.day:02d}"
    return records.get(y, {}).get(m, {}).get(d, 0)


def _check_rollover(data):
    """
    Runs every time data is loaded. If the NPT date has moved on since
    last_study_date:
      - total_seconds_today is recomputed from records.json for *today*
        (so !dailyrec never shows yesterday's stale total).
      - streak is evaluated: continues only if exactly one day passed
        and yesterday's total hit STUDY_GOAL_SECONDS, otherwise resets to 0.
    """
    now = get_now()
    today_str = _date_str(now)
    last_str = data.get("last_study_date", "")

    if last_str == today_str:
        return data  # already current, nothing to do

    records = get_records()

    if last_str:
        try:
            last_dt = NPT.localize(datetime.strptime(last_str, "%Y-%m-%d"))
            gap_days = (now.date() - last_dt.date()).days
            last_day_total = _day_total(records, last_dt)

            if gap_days == 1 and last_day_total >= STUDY_GOAL_SECONDS:
                data["streak"] = data.get("streak", 0) + 1
                data["stars"] = data.get("stars", 0) + 1
            else:
                # missed a day entirely, or didn't hit the goal on the last one
                data["streak"] = 0
        except ValueError:
            pass  # malformed date on file, don't crash — just skip streak logic

    data["total_seconds_today"] = _day_total(records, now)
    data["last_study_date"] = today_str
    save_json(DATA_FILE, data)
    return data


def get_data():
    default = {
        "tdl": [],
        "notes": [],
        "status": None,
        "status_msg": "",
        "streak": 0,
        "stars": 0,
        "last_study_date": "",
        "total_seconds_today": 0
    }
    data = load_json(DATA_FILE, default)
    # backfill any keys missing from an older data.json
    for k, v in default.items():
        data.setdefault(k, v)
    return _check_rollover(data)


def get_records():
    return load_json(RECORDS_FILE, {})


def get_monthly_total(year, month):
    """Sum all recorded seconds for a given year+month (month: 1-12)."""
    records = get_records()
    month_data = records.get(str(year), {}).get(f"{int(month):02d}", {})
    return sum(month_data.values())


def get_yearly_total(year):
    """Sum all recorded seconds for a given year."""
    records = get_records()
    year_data = records.get(str(year), {})
    return sum(sum(month.values()) for month in year_data.values())


def get_monthly_breakdown(year, month):
    """Return [(day_str, seconds), ...] for every day in the given month
    (28-31 entries depending on the month), zero-filled for days with
    no recorded study."""
    records = get_records()
    month_data = records.get(str(year), {}).get(f"{int(month):02d}", {})
    days_in_month = calendar.monthrange(int(year), int(month))[1]
    return [(f"{d:02d}", month_data.get(f"{d:02d}", 0)) for d in range(1, days_in_month + 1)]


def get_yearly_breakdown(year):
    """Return [(month_name, seconds), ...] for all 12 months, zero-filled
    for months with no recorded study. Naturally resets each new year since
    records.json is keyed by year."""
    records = get_records()
    year_data = records.get(str(year), {})
    result = []
    for i in range(1, 13):
        mkey = f"{i:02d}"
        month_data = year_data.get(mkey, {})
        result.append((MONTH_NAMES[i - 1], sum(month_data.values())))
    return result


def update_study_record(seconds):
    now = get_now()
    year = str(now.year)
    month = f"{now.month:02d}"
    day = f"{now.day:02d}"

    records = get_records()
    if year not in records:
        records[year] = {}
    if month not in records[year]:
        records[year][month] = {}

    current = records[year][month].get(day, 0)
    records[year][month][day] = current + seconds
    save_json(RECORDS_FILE, records)

    # get_data() already rolled last_study_date/total_seconds_today forward
    # to "today" if needed, so we can just accumulate safely here.
    data = get_data()
    data["total_seconds_today"] += seconds
    data["last_study_date"] = f"{year}-{month}-{day}"
    save_json(DATA_FILE, data)
