import argparse
import calendar
import datetime
import json
import logging
import os
import sys
import cv2

import utils
from config import SQL_FILE
from gpxtrackposter import (
    circular_drawer,
    github_drawer,
    grid_drawer,
    poster,
    track_loader,
    month_of_life_drawer,
    calendar_drawer,
    heatmap_drawer,
    laps_drawer
)
from gpxtrackposter.exceptions import ParameterError, PosterError

# from flopp great repo
__app_name__ = "create_poster"
__app_author__ = "flopp.net"

from synced_data_file_logger import load_generated_activity_list, save_generated_activity_list


def main():
    """Handle command line arguments and call other modules as needed."""

    p = poster.Poster()
    drawers = {
        "grid": grid_drawer.GridDrawer(p),
        "circular": circular_drawer.CircularDrawer(p),
        "github": github_drawer.GithubDrawer(p),
        "monthoflife": month_of_life_drawer.MonthOfLifeDrawer(p),
        "calendar": calendar_drawer.CalendarDrawer(p),
        "heatmap": heatmap_drawer.HeatmapDrawer(p),
        "laps": laps_drawer.LapsDrawer(p),
    }

    args_parser = argparse.ArgumentParser()
    args_parser.add_argument(
        "--gpx-dir",
        dest="gpx_dir",
        metavar="DIR",
        type=str,
        default=".",
        help="Directory containing GPX files (default: current directory).",
    )
    args_parser.add_argument(
        "--output",
        metavar="FILE",
        type=str,
        default="poster.svg",
        help='Name of generated SVG image file (default: "poster.svg").',
    )
    args_parser.add_argument(
        "--language",
        metavar="LANGUAGE",
        type=str,
        default="",
        help="Language (default: english).",
    )
    args_parser.add_argument(
        "--year",
        metavar="YEAR",
        type=str,
        default="all",
        help='Filter tracks by year; "NUM", "NUM-NUM", "all" (default: all years)',
    )
    args_parser.add_argument(
        "--title", metavar="TITLE", type=str, help="Title to display."
    )
    args_parser.add_argument(
        "--athlete",
        metavar="NAME",
        type=str,
        default="John Doe",
        help='Athlete name to display (default: "John Doe").',
    )
    args_parser.add_argument(
        "--special",
        metavar="FILE",
        action="append",
        default=[],
        help="Mark track file from the GPX directory as special; use multiple times to mark "
        "multiple tracks.",
    )
    types = '", "'.join(drawers.keys())
    args_parser.add_argument(
        "--type",
        metavar="TYPE",
        default="grid",
        choices=drawers.keys(),
        help=f'Type of poster to create (default: "grid", available: "{types}").',
    )
    args_parser.add_argument(
        "--background-color",
        dest="background_color",
        metavar="COLOR",
        type=str,
        default="#222222",
        help='Background color of poster (default: "#222222").',
    )
    args_parser.add_argument(
        "--track-color",
        dest="track_color",
        metavar="COLOR",
        type=str,
        default="#4DD2FF",
        help='Color of tracks (default: "#4DD2FF").',
    )
    args_parser.add_argument(
        "--track-color2",
        dest="track_color2",
        metavar="COLOR",
        type=str,
        help="Secondary color of tracks (default: none).",
    )
    args_parser.add_argument(
        "--text-color",
        dest="text_color",
        metavar="COLOR",
        type=str,
        default="#FFFFFF",
        help='Color of text (default: "#FFFFFF").',
    )
    args_parser.add_argument(
        "--special-color",
        dest="special_color",
        metavar="COLOR",
        default="#FFFF00",
        help='Special track color (default: "#FFFF00").',
    )
    args_parser.add_argument(
        "--special-color2",
        dest="special_color2",
        metavar="COLOR",
        help="Secondary color of special tracks (default: none).",
    )
    args_parser.add_argument(
        "--units",
        dest="units",
        metavar="UNITS",
        type=str,
        choices=["metric", "imperial"],
        default="metric",
        help='Distance units; "metric", "imperial" (default: "metric").',
    )
    args_parser.add_argument(
        "--verbose", dest="verbose", action="store_true", help="Verbose logging."
    )
    args_parser.add_argument("--logfile", dest="logfile", metavar="FILE", type=str)
    args_parser.add_argument(
        "--special-distance",
        dest="special_distance",
        metavar="DISTANCE",
        type=float,
        default=10.0,
        help="Special Distance1 by km and color with the special_color",
    )
    args_parser.add_argument(
        "--special-distance2",
        dest="special_distance2",
        metavar="DISTANCE",
        type=float,
        default=20.0,
        help="Special Distance2 by km and corlor with the special_color2",
    )
    args_parser.add_argument(
        "--min-distance",
        dest="min_distance",
        metavar="DISTANCE",
        type=float,
        default=1.0,
        help="min distance by km for track filter",
    )
    args_parser.add_argument(
        "--use-localtime",
        dest="use_localtime",
        action="store_true",
        help="Use utc time or local time",
    )

    args_parser.add_argument(
        "--from-db",
        dest="from_db",
        action="store_true",
        help="activities db file",
    )

    args_parser.add_argument(
        "--github-style",
        dest="github_style",
        metavar="GITHUB_STYLE",
        type=str,
        default="align-firstday",
        help='github svg style; "align-firstday", "align-monday" (default: "align-firstday").',
    )

    args_parser.add_argument(
        "--only-run",
        dest="only_run",
        action="store_true",
        help="if is only for running",
    )

    args_parser.add_argument(
        "--with-mp4",
        dest="with_mp4",
        action="store_true",
        help="add animation to the poster",
    )

    args_parser.add_argument(
        "--with-animation",
        dest="with_animation",
        action="store_true",
        help="add animation to the poster",
    )
    args_parser.add_argument(
        "--animation-time",
        dest="animation_time",
        type=int,
        default=10,
        help="animation duration (default: 10s)",
    )
    args_parser.add_argument(
        "--no-background",
        dest="no_background",
        action="store_true",
        help="no draw background",
    )
    args_parser.add_argument(
        "--blog-dir",
        dest="blog_dir",
        metavar="DIR",
        type=str,
        default=".",
        help="Directory containing blog files (default: current directory).",
    )

    for _, drawer in drawers.items():
        drawer.create_args(args_parser)

    args = args_parser.parse_args()
    global track_color, special_color, special_color2
    track_color = args.track_color
    special_color = args.special_color
    special_color2 = args.special_color2

    for _, drawer in drawers.items():
        drawer.fetch_args(args)

    log = logging.getLogger("gpxtrackposter")
    log.setLevel(logging.INFO if args.verbose else logging.ERROR)
    if args.logfile:
        handler = logging.FileHandler(args.logfile)
        log.addHandler(handler)

    loader = track_loader.TrackLoader()
    if args.use_localtime:
        loader.use_local_time = True
    if not loader.year_range.parse(args.year):
        raise ParameterError(f"Bad year range: {args.year}.")

    loader.special_file_names = args.special
    loader.min_length = args.min_distance * 1000

    if args.from_db:
        # for svg from db here if you want gpx please do not use --from-db
        # args.type == "grid" means have polyline data or not
        tracks = loader.load_tracks_from_db(
            SQL_FILE, args.type == "grid", args.type == "circular", args.only_run
        )
    else:
        tracks = loader.load_tracks(args.gpx_dir)
    if not tracks:
        return

    is_circular = args.type == "circular"
    is_mol = args.type == "monthoflife"

    if not is_circular and not is_mol and not args.type == "calendar":
        print(
            f"Creating poster of type {args.type} with {len(tracks)} tracks and storing it in file {args.output}..."
        )
    p.set_language(args.language)
    p.set_with_animation(args.with_animation)
    p.set_animation_time(args.animation_time)
    p.athlete = args.athlete
    if args.title:
        p.title = args.title
    else:
        p.title = p.trans("MY TRACKS")

    if args.no_background:
        p.no_background = True
    else:
        p.no_background = False

    p.special_distance = {
        "special_distance": args.special_distance,
        "special_distance2": args.special_distance2,
    }

    p.colors = {
        "background": args.background_color,
        "track": args.track_color,
        "track2": args.track_color2 or args.track_color,
        "special": args.special_color,
        "special2": args.special_color2 or args.special_color,
        "text": args.text_color,
    }
    p.units = args.units
    p.set_tracks(tracks)
    length_range = p.length_range
    length_range_by_date = p.length_range_by_date
    # circular not add footer and header
    p.drawer_type = "plain" if is_circular and not args.with_mp4 else "title"
    if is_mol:
        p.drawer_type = "monthoflife"
    if args.type == "github":
        p.height = 55 + p.years.real_year * 43
    p.github_style = args.github_style
    # for special circular
    if is_circular:
        years = p.years.all()[:]
        for y in years:
            if args.with_mp4:
                date = datetime.date(y, 1, 1)
                m_count = 0
                svg_files = []
                while date.year == y:
                    text_date = date.strftime("%Y-%m-%d")
                    m_tracks = [t for t in tracks if t.start_time_local.strftime("%Y-%m-%d") <= text_date]
                    length = sum([t.length for t in tracks if t.start_time_local.strftime("%Y-%m-%d") == text_date])
                    p.years.from_year, p.years.to_year = y, y
                    # may be refactor
                    if len(m_tracks) != m_count:
                        p.set_tracks(m_tracks)
                        p.length_range = length_range
                        p.length_range_by_date = length_range_by_date
                        p.draw(drawers[args.type], os.path.join("assets", f"circular_{text_date}.svg"))
                        from cairosvg import svg2png
                        svg2png(url=os.path.join("assets", f"circular_{text_date}.svg"),
                                write_to=os.path.join("assets", f"circular_{text_date}.png"))
                        svg_files.append(f"circular_{text_date}")
                    date += datetime.timedelta(1)
                    m_count = len(m_tracks)
                if len(svg_files) != 0:
                    w, h = None, None
                    for file in svg_files:
                        frame = cv2.imread(os.path.join("assets", f"{file}.png"))

                        if w is None:
                            # Setting up the video writer
                            h, w, _ = frame.shape
                            fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
                            writer = cv2.VideoWriter(os.path.join("assets", f'circular_{y}.mp4'), fourcc,
                                                     len(svg_files) / args.animation_time, (w, h))

                        writer.write(frame)
                    writer.release()

                    os.system('ffmpeg -i %s -i %s -map 0:v -map 1:a -c:v copy -shortest -y %s' % (
                        os.path.join("assets", f'circular_{y}.mp4'),
                        os.path.join("assets", 'background_wake.mp3'),
                        os.path.join("assets", f'circular_{y}_bg.mp4')
                    ))
                    for file in svg_files:
                        os.remove(os.path.join("assets", f"{file}.svg"))
                        os.remove(os.path.join("assets", f"{file}.png"))
                    os.remove(os.path.join("assets", f"circular_{y}.mp4"))
                    os.rename(os.path.join("assets", f"circular_{y}_bg.mp4"),
                              os.path.join("assets", f"circular_{y}.mp4"))
            else:
                p.years.from_year, p.years.to_year = y, y
                # may be refactor
                p.set_tracks([t for t in tracks if t.start_time_local.strftime("%Y") == str(y)])
                p.draw(drawers[args.type], os.path.join("assets", f"year_{str(y)}.svg"))
                # from cairosvg import svg2png
                # svg2png(url=os.path.join("assets", f"year_{str(y)}.svg"),
                #         write_to=os.path.join("assets", f"year_{str(y)}.png"))
    if args.type == 'calendar':
        years = p.years.all()[:]
        for y in years:
            p.years.from_year, p.years.to_year = y, y
            # may be refactor
            p.set_tracks([t for t in tracks if t.start_time_local.strftime("%Y") == str(y)])
            p.draw(drawers[args.type], os.path.join("assets", f"calendar_{str(y)}.svg"))
    if args.type == 'laps':
        generated_activity = load_generated_activity_list()
        for track in tracks:
            # t = Track()
            # t.load_fit("FIT_OUT/251304010.fit")
            if track.run_id in generated_activity:
                continue

            if track.polylines is None or len(track.polylines) == 0 or len(track.polylines[0]) == 0:
                continue

            file_name = track.start_time_local.strftime("%Y%m%d") + "_" + str(track.run_id)
            # file_name = str(track.run_id)

            year = track.start_time_local.year
            directory = os.path.join(f"{args.blog_dir}/../../../assets", f"run_{year}")
            if not os.path.exists(directory):
                os.makedirs(directory)

            p.width = 120
            p.height = 190
            p.drawer_type = "plain"
            p.set_tracks([track])
            p.draw(drawers[args.type], os.path.join(directory, f"{file_name}.svg"))

            directory = os.path.join(f"{args.blog_dir}/run", f"{year}")
            if not os.path.exists(directory):
                os.makedirs(directory)

            month_tracks = get_tracks_by_month(tracks, year, track.start_time_local.month)
            generate_month_page(month_tracks, year, track.start_time_local.month, args.blog_dir)

            # generate_track_page(args, file_name, track, year)

            generated_activity.append(track.run_id)
        save_generated_activity_list(generated_activity)
    else:
        p.draw(drawers[args.type], args.output)
        from cairosvg import svg2png
        svg2png(url=args.output, write_to=args.output.replace('svg', 'png'))


def generate_track_page(args, file_name, track, year):
    with open(os.path.join(f"{args.blog_dir}/run/{year}", f"{file_name}.md"), "w") as f:
        f.write(f"---\n")
        # f.write(f"layout: post\n")
        f.write(f"title: {track.start_time_local.strftime('%Y-%m-%d')} 跑步日记\n")
        f.write(f"created: {track.start_time_local.strftime('%Y-%m-%dT%H:%M:%S+08:00')}\n")
        f.write(f"date: {track.start_time_local.strftime('%Y-%m-%dT%H:%M:%S+08:00')}\n")
        f.write(f"author: Jogger\n")
        f.write(f"tags: [跑步]\n")
        f.write(f"---\n")
        f.write(f"**时间：** {track.start_time_local.strftime('%Y-%m-%d %H:%M:%S')}  \n")
        f.write(f"**距离：** {track.length / 1000:.2f} km  \n")
        f.write(f"**时长：** {utils.get_time_delta(track.start_time, track.end_time)}  \n")
        f.write(f"**配速：** {utils.speed_to_pace(track.average_speed * 3.6)} / km  \n")
        f.write(f"**心率：** {int(track.average_heartrate)} bpm  \n")
        f.write(f"![{file_name}](/assets/run_{year}/{file_name}.svg)\n")


def get_tracks_by_month(tracks, year, month):
    month_tracks = []
    for track in tracks:
        if track.start_time_local.year == year and track.start_time_local.month == month:
            month_tracks.append(track)

    return month_tracks


def generate_month_page(tracks, year, month, blog_dir):
    if len(tracks) == 0:
        return

    month_stats = {}
    for t in tracks:
        month_stats = add_month_stats(month_stats, t)

    with open(os.path.join(f"{blog_dir}/run/{year}", f"{year}-{month:02d}.md"), "w") as f:
        f.write(f"---\n")
        f.write(f"title: {year}-{month:02d} 跑步日记\n")
        f.write(f"created: {tracks[0].start_time_local.strftime('%Y-%m-%dT%H:%M:%S+08:00')}\n")
        f.write(f"date: {tracks[-1].start_time_local.strftime('%Y-%m-%dT%H:%M:%S+08:00')}\n")
        f.write(f"author: Jogger\n")
        f.write(f"tags: [跑步]\n")
        f.write(f"---\n")
        f.write(f"## {year}-{month:02d}\n")
        f.write(f"运动次数: {month_stats[year][month]['runs']}  \n")
        f.write(f"运动距离: {month_stats[year][month]['distance']:.2f} km  \n")
        f.write(f"运动时长: {utils.format_duration(month_stats[year][month]['moving_time'])}  \n")
        f.write(f"平均距离: {month_stats[year][month]['distance'] / month_stats[year][month]['runs']:.2f} km  \n")
        f.write(f"平均心率: {month_stats[year][month]['average_heartrate']:.0f} bpm  \n")
        f.write(
            f"平均配速: {utils.speed_to_pace(month_stats[year][month]['distance'] * 3600 / month_stats[year][month]['moving_time'])} / km  \n")

        days = generate_days(year, month)
        days_distance, days_heartrate = get_days_distance(tracks, days)

        f.write("```echarts {height=300}\n")
        echart_option = {
            "tooltip": {
                "trigger": "axis",
                "triggerOn": "click",
                "enterable": True,
                "show": True,
                "formatter": "function (params) {\n      if (params[0].data == '-') return '';\n      return '<a href=\"#" + f"{year}-{month:02d}-" + "' + params[0].name.padStart(2, '0') + '\">' +\n        '" + f"{year}-{month:02d}-" + "' + params[0].name.padStart(2, '0') + '</a> <br>' +\n        params[0].seriesName + ': ' + params[0].data + '<br>' +\n        params[1].seriesName + ': ' + params[1].data;\n    }"
            },
            "xAxis": {
                "type": "category",
                "data": days,
                "name": "日期",
                "nameLocation": "center",
                "nameGap": 30,
                "nameTextStyle": {
                    "color": f'{track_color}'
                },
                "axisLabel": {
                    "textStyle": {
                        "color": f'{track_color}'
                    }
                },
                "axisTick": {
                    "lineStyle": {
                        "color": f'{track_color}'
                    }
                },
                "axisLine": {
                    "lineStyle": {
                        "color": f'{track_color}'
                    }
                }
            },
            "yAxis": [
                {
                    "name": "跑步距离(km)",
                    "type": "value",
                    "scale": True,
                    "splitLine": False,
                    "nameLocation": "center",
                    "nameRotate": "90",
                    "nameGap": 30,
                    "nameTextStyle": {
                        "color": f'{track_color}'
                    },
                    "axisLabel": {
                        "textStyle": {
                            "color": f'{track_color}'
                        }
                    }
                },
                {
                    "name": "平均心率(bpm)",
                    "type": "value",
                    "scale": True,
                    "splitLine": False,
                    "nameLocation": "center",
                    "nameRotate": "90",
                    "nameGap": 30,
                    "nameTextStyle": {
                        "color": f"{special_color2}"
                    },
                    "axisLabel": {
                        "textStyle": {
                            "color": f"{special_color2}"
                        }
                    }
                }
            ],
            "series": [
                {
                    "name": "跑步距离(km)",
                    "data": days_distance,
                    "itemStyle": {
                        "color": f'{track_color}'
                    },
                    "yAxisIndex": 0,
                    "type": "bar",
                    "markLine": {
                        "data": [
                            {
                                "type": "average",
                                "name": "平均值"
                            }
                        ],
                        "symbol": [
                            "none",
                            "none"
                        ],
                        "position": "insideTopCenter",
                        "itemStyle": {
                            "normal": {
                                "lineStyle": {
                                    "type": "dashed",
                                    "color": f'{track_color}'
                                },
                                "label": {
                                    "show": True,
                                    "position": "start",
                                    "color": f'{track_color}'
                                }
                            }
                        }
                    }
                },
                {
                    "name": "平均心率(bpm)",
                    "data": days_heartrate,
                    "connectNulls": True,
                    "itemStyle": {
                        "color": f"{special_color2}"
                    },
                    "yAxisIndex": 1,
                    "type": "line"
                }
            ]
        }
        f.write(json.dumps(echart_option, ensure_ascii=False, indent=2))
        f.write("\n")
        f.write("```\n")

        for track in tracks:
            svg_name = track.start_time_local.strftime("%Y%m%d") + "_" + str(track.run_id)
            f.write(f"\n")
            f.write(f"---\n")
            f.write(f"## {year}-{month:02d}-{track.start_time_local.day:02d}\n")
            f.write(f"**时间：** {track.start_time_local.strftime('%Y-%m-%d %H:%M:%S')}  \n")
            f.write(f"**距离：** {track.length / 1000:.2f} km  \n")
            f.write(f"**时长：** {utils.get_time_delta(track.start_time, track.end_time)}  \n")
            f.write(f"**配速：** {utils.speed_to_pace(track.average_speed * 3.6)} / km  \n")
            f.write(f"**心率：** {int(track.average_heartrate)} bpm  \n")
            f.write(f"![{svg_name}](/assets/run_{year}/{svg_name}.svg)\n")


def add_month_stats(month_stat, track):
    year = track.start_time_local.year
    month = track.start_time_local.month

    if year not in month_stat:
        month_stat[year] = {
            month: {
                'runs': 1,
                'distance': track.length / 1000,
                'average_heartrate': track.average_heartrate,
                'sum_heartrate': track.average_heartrate * track.length / 1000,
                'moving_time': int(track.end_time.timestamp() - track.start_time.timestamp())
            }
        }
    else:
        if month not in month_stat[year]:
            month_stat[year][month] = {
                'runs': 1, 'distance': track.length / 1000,
                'average_heartrate': track.average_heartrate,
                'sum_heartrate': track.average_heartrate * track.length / 1000,
                'moving_time': int(track.end_time.timestamp() - track.start_time.timestamp())
            }
        else:
            month_stat[year][month] = {
                'runs': month_stat[year][month]['runs'] + 1,
                'distance': month_stat[year][month]['distance'] + track.length / 1000,
                'average_heartrate': (month_stat[year][month]['sum_heartrate'] + track.average_heartrate * track.length / 1000) / (month_stat[year][month]['distance'] + track.length / 1000),
                'sum_heartrate': month_stat[year][month]['sum_heartrate'] + track.average_heartrate * track.length / 1000,
                'moving_time': month_stat[year][month]['moving_time'] + int(track.end_time.timestamp() - track.start_time.timestamp())
            }

    return month_stat


def generate_days(year, month):
    # 获取指定年月的天数
    _, num_days = calendar.monthrange(year, month)
    # 生成日期数字数组
    days = list(range(1, num_days + 1))
    return days


def get_days_distance(tracks, days):
    days_distance = [0 for day in days]
    days_heartrate = [0 for day in days]
    runs = [0 for day in days]
    for track in tracks:
        day = track.start_time_local.day
        days_distance[day - 1] += track.length / 1000
        days_heartrate[day - 1] += track.average_heartrate
        runs[day - 1] += 1

    for index, value in enumerate(days_distance):
        if value == 0:
            days_distance[index] = '-'
        else:
            days_distance[index] = round(value, 2)

    for index, value in enumerate(days_heartrate):
        if value == 0:
            days_heartrate[index] = '-'
        else:
            days_heartrate[index] = value / runs[index]

    return days_distance, days_heartrate


if __name__ == "__main__":
    try:
        # generate svg
        main()
    except PosterError as e:
        print(e)
        sys.exit(1)
