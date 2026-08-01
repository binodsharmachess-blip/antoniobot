import json
import os
from datetime import datetime
import pytz

DATA_FILE = "data.json"
RECORDS_FILE = "records.json"
NPT = pytz.timezone('Asia/Kathmandu')

def get_now():
    return datetime.now(NPT)

def load_json(filename, default):
    if not os.path.exists(filename):
        return default
    with open(filename, 'r') as f:
        try:
            return json.load(f)
        except:
            return default

def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

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
    return load_json(DATA_FILE, default)

def get_records():
    return load_json(RECORDS_FILE, {})

def update_study_record(seconds):
    now = get_now()
    year = str(now.year)
    month = f"{now.month:02d}"
    day = f"{now.day:02d}"
    
    records = get_records()
    if year not in records: records[year] = {}
    if month not in records[year]: records[year][month] = {}
    
    current = records[year][month].get(day, 0)
    records[year][month][day] = current + seconds
    save_json(RECORDS_FILE, records)
    
    # Update daily streak/stars logic
    data = get_data()
    today_str = f"{year}-{month}-{day}"
    
    if data["last_study_date"] != today_str:
        data["total_seconds_today"] = seconds
        data["last_study_date"] = today_str
    else:
        data["total_seconds_today"] += seconds
        
    save_json(DATA_FILE, data)
