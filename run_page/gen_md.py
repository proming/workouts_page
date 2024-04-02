import argparse
import sys
from datetime import datetime

import svgwrite

from config import SQL_FILE
from gpxtrackposter import track_loader
from gpxtrackposter.exceptions import ParameterError
from synced_data_file_logger import load_generated_activity_list

track_color = "#4DD2FF"
special_color = "#FFFF00"
special_color2 = None

def main():
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument(
        "--from-db",
        dest="from_db",
        action="store_true",
        help="activities db file",
    )
    args_parser.add_argument(
        "--use-localtime",
        dest="use_localtime",
        action="store_true",
        help="Use utc time or local time",
    )
    args_parser.add_argument(
        "--year",
        metavar="YEAR",
        type=str,
        default="all",
        help='Filter tracks by year; "NUM", "NUM-NUM", "all" (default: all years)',
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
        "--special",
        metavar="FILE",
        action="append",
        default=[],
        help="Mark track file from the GPX directory as special; use multiple times to mark "
        "multiple tracks.",
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
        "--only-run",
        dest="only_run",
        action="store_true",
        help="if is only for running",
    )
    args_parser.add_argument(
        "--gpx-dir",
        dest="gpx_dir",
        metavar="DIR",
        type=str,
        default=".",
        help="Directory containing GPX files (default: current directory).",
    )
    args_parser.add_argument(
        "--blog-dir",
        dest="blog_dir",
        metavar="DIR",
        type=str,
        default=".",
        help="Directory containing blog files (default: current directory).",
    )
    args = args_parser.parse_args()

    global track_color, special_color, special_color2
    track_color = args.track_color
    special_color = args.special_color
    special_color2 = args.special_color2

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
            SQL_FILE, False, False, args.only_run
        )
    else:
        tracks = loader.load_tracks(args.gpx_dir)
    if not tracks:
        return

    total_stats = {}
    year_stats = {}
    month_stats = {}
    day_stats = {}
    for t in tracks:
        total_stats = add_total_stats(total_stats, t)
        year_stats = add_year_stats(year_stats, t)
        month_stats = add_month_stats(month_stats, t)
        day_stats = add_day_stats(day_stats, t)

    with open(f"{args.blog_dir}/run/run_stats.md", "w") as f:
        f.write(f"---\n")
        # f.write(f"layout: post\n")
        f.write(f"title: 跑步总结（{datetime.now().strftime('%Y-%m-%d')} 更新）\n")
        f.write(f"created: 2018-12-15T07:33:48+08:00\n")
        f.write(f"date: {datetime.now().strftime('%Y-%m-%dT%H:%M:%S+08:00')}\n")
        f.write(f"author: Jogger\n")
        f.write(f"tags: [跑步]\n")
        f.write(f"---\n")
        f.write(f"\n")
        f.write("## 累计数据  \n")
        f.write(f"累计跑步: {total_stats['runs']} 天  \n")
        f.write(f"累计里程: {total_stats['distance']:.2f} km  \n")
        f.write(f"平均心率: {total_stats['average_heartrate']:.0f} bpm  \n")
        generate_year_stat_svg(None, year_stats, args.blog_dir)
        f.write(f"![run-stats](/assets/run-stats.svg)\n")

        sorted_keys = sorted(year_stats.keys())
        for key in sorted_keys:
            f.write(f"\n")
            f.write(f"---\n")
            f.write(f"## {key}\n")
            f.write(f"累计跑步: {year_stats[key]['runs']} 天  \n")
            f.write(f"累计里程: {year_stats[key]['distance']:.2f} km  \n")
            f.write(f"平均心率: {year_stats[key]['average_heartrate']:.0f} bpm  \n")

            generate_year_stat_svg(key, month_stats[key], args.blog_dir)
            f.write(f"![stat-{key}](/assets/stat-{key}.svg)\n")
            f.write(f"\n")
            f.write("| 1月 | 2月 | 3月 | 4月 | 5月 | 6月 |\n")
            f.write("| :-: | :-: | :-: | :-: | :-: | :-: |\n")
            f.write(f"| {get_day_stat_detail(key, 1, day_stats)} |"
                    f" {get_day_stat_detail(key, 2, day_stats)} |"
                    f" {get_day_stat_detail(key, 3, day_stats)} |"
                    f" {get_day_stat_detail(key, 4, day_stats)} |"
                    f" {get_day_stat_detail(key, 5, day_stats)} |"
                    f" {get_day_stat_detail(key, 6, day_stats)} |\n")
            f.write("| **7月** | **8月** | **9月** | **10月** | **11月** | **12月** |\n")
            f.write(f"| {get_day_stat_detail(key, 7, day_stats)} |"
                    f" {get_day_stat_detail(key, 8, day_stats)} |"
                    f" {get_day_stat_detail(key, 9, day_stats)} |"
                    f" {get_day_stat_detail(key, 10, day_stats)} |"
                    f" {get_day_stat_detail(key, 11, day_stats)} |"
                    f" {get_day_stat_detail(key, 12, day_stats)} |\n")
            f.write(f"\n")


def add_year_stats(year_stat, track):
    year = track.start_time_local.year

    if year not in year_stat:
        year_stat[year] = {'runs': 1, 'distance': track.length / 1000,
                           'sum_heartrate': track.average_heartrate,
                           'average_heartrate': track.average_heartrate
                           }
    else:
        year_stat[year] = {
            'runs': year_stat[year]['runs'] + 1,
            'distance': year_stat[year]['distance'] + track.length / 1000,
            'sum_heartrate': year_stat[year]['sum_heartrate'] + track.average_heartrate,
            'average_heartrate': (year_stat[year]['sum_heartrate'] + track.average_heartrate) / (year_stat[year]['runs'] + 1)
        }

    return year_stat

def add_total_stats(total_stat, track):
    if 'runs' not in total_stat:
        total_stat['runs'] = 1
        total_stat['distance'] = track.length / 1000
        total_stat['sum_heartrate'] = track.average_heartrate
        total_stat['average_heartrate'] = track.average_heartrate
    else:
        total_stat['runs'] += 1
        total_stat['distance'] += track.length / 1000
        total_stat['sum_heartrate'] += track.average_heartrate
        total_stat['average_heartrate'] = total_stat['sum_heartrate'] / total_stat['runs']

    return total_stat


def add_month_stats(month_stat, track):
    year = track.start_time_local.year
    month = track.start_time_local.month

    if year not in month_stat:
        month_stat[year] = {month: {'runs': 1, 'distance': track.length / 1000,
                                    'average_heartrate': track.average_heartrate,
                                    'sum_heartrate': track.average_heartrate}}
    else:
        if month not in month_stat[year]:
            month_stat[year][month] = {'runs': 1, 'distance': track.length / 1000,
                                    'average_heartrate': track.average_heartrate,
                                    'sum_heartrate': track.average_heartrate}
        else:
            month_stat[year][month] = {
                'runs': month_stat[year][month]['runs'] + 1,
                'distance': month_stat[year][month]['distance'] + track.length / 1000,
                'average_heartrate': (month_stat[year][month]['sum_heartrate'] + track.average_heartrate) / (month_stat[year][month]['runs'] + 1),
                'sum_heartrate': month_stat[year][month]['sum_heartrate'] + track.average_heartrate
            }

    return month_stat

def add_day_stats(day_stat, track):
    year = track.start_time_local.year
    month = track.start_time_local.month

    if year not in day_stat:
        day_stat[year] = {}

    if month not in day_stat[year]:
        day_stat[year][month] = [{'run_id': track.run_id,
                                    'day': track.start_time_local.day,
                                    'distance': track.length / 1000,
                                    'average_heartrate': track.average_heartrate,
                                    'start_time': track.start_time_local
                                  }]
    else:
        day_stat[year][month].append({'run_id': track.run_id,
                                        'day': track.start_time_local.day,
                                        'distance': track.length / 1000,
                                        'average_heartrate': track.average_heartrate,
                                        'start_time': track.start_time_local
                                      })

    return day_stat


def generate_year_stat_svg(year, data, blog_dir):
    # Dimensions and margins
    bar_width = 28
    bar_spacing = 7
    height = 200
    margin = 50
    if year is None:
        width = len(data) * bar_width + (len(data) + 1) * bar_spacing + 2 * margin
    else:
        width = 12 * bar_width + 13 * bar_spacing + 2 * margin
    # width = 500

    scales_num = 5

    # Calculate min/max values for axes
    min_distance = min(d['distance'] for d in data.values()) - 0.5
    max_distance = max(d['distance'] for d in data.values()) + 0.5
    min_heartrate = min(d['average_heartrate'] for d in data.values()) - 2
    max_heartrate = max(d['average_heartrate'] for d in data.values()) + 2

    # Calculate bar width and spacing
    # if year is None:
    #     bar_width = 4 * (width - 2 * margin) / (5 * len(data) + 1)
    #     bar_spacing = bar_width / 4
    # else:
    #     bar_width = 13.1147311475 * 2
    #     bar_spacing = bar_width / 4

    scale_height = height - 2 * margin

    distance_len = max_distance - min_distance
    heartrate_len = max_heartrate - min_heartrate
    distance_scale = scale_height / distance_len
    heartrate_scale = scale_height / heartrate_len

    # Create the SVG document
    if year is None:
        dwg = svgwrite.Drawing(f"{blog_dir}/../assets/run-stats.svg", profile='tiny', size=(width, height))
    else:
        dwg = svgwrite.Drawing(f"{blog_dir}/../assets/stat-{year}.svg", profile='tiny', size=(width, height))

    # Add axes
    # dwg.add(dwg.line((margin, height - margin), (width - margin, height - margin), stroke='black'))  # x-axis
    # dwg.add(dwg.line((margin, margin), (margin, height - margin), stroke='blue'))  # y-axis (left)
    # dwg.add(dwg.line((width - margin, margin), (width - margin, height - margin), stroke='red'))  # y-axis (right)
    # 横坐标轴标签
    if year is None:
        for i, (month, stats) in enumerate(data.items()):
            dwg.add(dwg.text(str(month), insert=(margin + i * 5 / 4 * bar_width + 3 / 4 * bar_width, height - margin + 10),
                             font_size=10, fill=track_color, text_anchor='middle'))
    else:
        for i in range(12):
            dwg.add(dwg.text(str(i + 1), insert=(margin + i * 5 / 4 * bar_width + 3 / 4 * bar_width, height - margin + 10),
                             font_size=10, fill=track_color, text_anchor='middle'))

    distance_space = float(distance_len / scales_num)
    heart_space = float(heartrate_len / scales_num)
    for i in range(scales_num + 1):
        # 左坐标轴标签
        dwg.add(dwg.text(f"{i * distance_space + min_distance:.0f}",
                         insert=(margin - 20, height - margin - i * distance_space * distance_scale), font_size=10,
                         fill=track_color))

        # 右坐标轴标签
        dwg.add(dwg.text(f"{i * heart_space + min_heartrate:.0f}",
                         insert=(width - margin + 5, height - margin - i * heart_space * heartrate_scale), font_size=10,
                         fill=special_color2))

    # Add axis labels
    if year is None:
        dwg.add(
            dwg.text('年', insert=(width // 2, height - margin + 20), font_size=12, text_anchor='middle', fill=track_color))
    else:
        dwg.add(
            dwg.text("月", insert=(width // 2, height - margin + 20), font_size=12, text_anchor='middle', fill=track_color))
    dwg.add(dwg.text('距离 (km)', insert=(margin - 30, height // 2), font_size=12, text_anchor='middle',
                     transform='rotate(-90, {}, {})'.format(margin - 30, height // 2), fill=track_color))
    dwg.add(dwg.text('心率 (bpm)', insert=(width - margin + 30, height // 2), font_size=12, text_anchor='middle',
                     transform='rotate(90, {}, {})'.format(width - margin + 30, height // 2), fill=special_color2))

    # Draw bars and line
    if year is None:
        for i, (month, stats) in enumerate(data.items()):
            x = margin + i * (bar_width + bar_spacing) + bar_spacing

            # Bar for distance
            bar_height = (stats['distance'] - min_distance) / (max_distance - min_distance) * (height - 2 * margin)
            rect = dwg.rect((x, height - margin - bar_height), (bar_width, bar_height), fill=track_color)
            rect.set_desc(title=f"{month}年 {stats['distance']:.2f} km")
            dwg.add(rect)

            # Point for heart rate line
            y = height - margin - (stats['average_heartrate'] - min_heartrate) / (max_heartrate - min_heartrate) * (
                    height - 2 * margin)
            circle = dwg.circle((x + bar_width // 2, y), r=3, stroke=special_color2, fill='none', stroke_width=2)
            circle.set_desc(title=f"{month}年 {stats['average_heartrate']:.2f} bpm")
            dwg.add(circle)
    else:
        for i in range(12):
            x = margin + i * (bar_width + bar_spacing) + bar_spacing
            month = i + 1
            if month not in data:
                continue
            stats = data[month]

            # Bar for distance
            bar_height = (stats['distance'] - min_distance) / (max_distance - min_distance) * (height - 2 * margin)
            rect = dwg.rect((x, height - margin - bar_height), (bar_width, bar_height), fill=track_color)
            rect.set_desc(title=f"{year}-{month}月 {stats['distance']:.2f} km")
            dwg.add(rect)

            # Point for heart rate line
            y = height - margin - (stats['average_heartrate'] - min_heartrate) / (max_heartrate - min_heartrate) * (
                height - 2 * margin)
            circle = dwg.circle((x + bar_width // 2, y), r=3, stroke=special_color2, fill='none', stroke_width=2)
            circle.set_desc(title=f"{year}-{month}月 {stats['average_heartrate']:.2f} bpm")
            dwg.add(circle)

    # Connect heart rate points with a line
    heart_rate_points = []
    if year is None:
        for i, (mont, stats) in enumerate(data.items()):
            heart_rate_points.append((margin + i * (bar_width + bar_spacing) + bar_spacing + bar_width // 2,
                              height - margin - (stats['average_heartrate'] - min_heartrate) / (
                                      max_heartrate - min_heartrate) * (height - 2 * margin)))
    else:
        for i in range(12):
            month = i + 1
            if month not in data:
                continue
            stats = data[month]
            heart_rate_points.append((margin + i * (bar_width + bar_spacing) + bar_spacing + bar_width // 2,
                                      height - margin - (stats['average_heartrate'] - min_heartrate) / (
                                              max_heartrate - min_heartrate) * (height - 2 * margin)))
    dwg.add(dwg.polyline(heart_rate_points, stroke=special_color2, fill='none', stroke_width=2))

    # Save the SVG file
    dwg.save()


def get_day_stat_detail(year, month, day_stats, blog_dir="."):
    if year not in day_stats:
        return "-"

    if month not in day_stats[year]:
        return "-"

    day_stat_detail = ""
    for stat in day_stats[year][month]:
        run_id = stat['run_id']
        day = stat['day']
        distance = stat['distance']
        start_time = stat['start_time']
        file_name = start_time.strftime("%Y%m%d") + "_" + str(run_id)
        if day_stat_detail == "":
            day_stat_detail = f"[{day}({distance:.2f} km)]({file_name}.md)"
        else:
            day_stat_detail += f"<br>[{day}({distance:.2f} km)]({file_name}.md)"

    return day_stat_detail


if __name__ == "__main__":
    main()
