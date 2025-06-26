import os
from config import SYNCED_FILE, GENERATED_ACTIVITY_FILE, FIT_CACHE_FILE
import json


def save_synced_data_file_list(file_list: list):
    old_list = load_synced_file_list()

    with open(SYNCED_FILE, "w") as f:
        file_list.extend(old_list)

        json.dump(file_list, f)


def load_synced_file_list():
    if os.path.exists(SYNCED_FILE):
        with open(SYNCED_FILE, "r") as f:
            try:
                return json.load(f)
            except Exception as e:
                print(f"json load {SYNCED_FILE} \nerror {e}")
                pass

    return []


def save_generated_activity_list(activity_list: list):
    with open(GENERATED_ACTIVITY_FILE, "w") as f:
        json.dump(activity_list, f)


def load_generated_activity_list():
    if os.path.exists(GENERATED_ACTIVITY_FILE):
        with open(GENERATED_ACTIVITY_FILE, "r") as f:
            try:
                return json.load(f)
            except Exception as e:
                print(f"json load {GENERATED_ACTIVITY_FILE} \nerror {e}")
                pass

    return []


def save_fit_cache_list(fit_cache_list):
    with open(FIT_CACHE_FILE, "w") as f:
        json.dump(fit_cache_list, f)


def load_fit_cache_list():
    if os.path.exists(FIT_CACHE_FILE):
        with open(FIT_CACHE_FILE, "r") as f:
            try:
                return json.load(f)
            except Exception as e:
                print(f"json load {FIT_CACHE_FILE} \nerror {e}")
                pass

    return {}
