import argparse
import asyncio
import os
from datetime import datetime

from config import FIT_FOLDER
from garmin_sync import Garmin
from gpxtrackposter.track_loader import TrackLoader, load_fit_file
from synced_data_file_logger import load_fit_cache_list, save_fit_cache_list


def upload_files_to_garmin(options):
    print("Need to load all fit files maybe take some time")

    fit_cache_list = load_fit_cache_list()

    file_names = []

    for file_name in os.listdir(FIT_FOLDER):
        if file_name.endswith('.fit') and file_name not in fit_cache_list:
            file_names.append(file_name)

    for file_name in file_names:
        track = load_fit_file(os.path.join(FIT_FOLDER, file_name))
        if track.start_time_local:
            fit_cache_list[file_name] = datetime.strftime(track.start_time_local, "%Y-%m-%d:%H:%M:%S")
        save_fit_cache_list(fit_cache_list)

    to_upload_files = []
    if options.dt is not None:
        dts = options.dt.split(",")
        for dt in dts:
            for file_name in fit_cache_list:
                if fit_cache_list[file_name].startswith(dt):
                    to_upload_files.append(os.path.join(FIT_FOLDER, file_name))
                    break
    print("Uploading files to Garmin...")
    garmin_auth_domain = "CN" if options.is_cn else ""
    garmin_client = Garmin(options.secret_string, garmin_auth_domain)
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(
        garmin_client.upload_activities_files(to_upload_files)
    )
    loop.run_until_complete(future)



if __name__ == "__main__":
    if not os.path.exists(FIT_FOLDER):
        os.mkdir(FIT_FOLDER)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "secret_string", nargs="?", help="secret_string fro get_garmin_secret.py"
    )
    parser.add_argument(
        "--dt",
        dest="dt",
        help="if upload to strava all without check last time",
    )
    parser.add_argument(
        "--is-cn",
        dest="is_cn",
        action="store_true",
        help="if garmin account is cn",
    )

    upload_files_to_garmin(parser.parse_args())
