
from datetime import datetime
import time

def get_current_seconds():
    return time.time()

def get_current_time_string_with_milliseconds():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]