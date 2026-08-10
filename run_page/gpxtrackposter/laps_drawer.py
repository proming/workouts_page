"""Draw a grid poster."""
from math import atan2, degrees

# Copyright 2016-2019 Florian Pigorsch & Contributors. All rights reserved.
#
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import svgwrite

from .exceptions import PosterError
from .poster import Poster
from .track import Track
from .tracks_drawer import TracksDrawer
from .utils import compute_grid, format_float, project, filter_route
from .xy import XY


class LapsDrawer(TracksDrawer):
    """Drawer used to draw a laps poster

    Methods:
        draw: For each track, draw it on the poster.
    """

    def __init__(self, the_poster: Poster):
        super().__init__(the_poster)

    @staticmethod
    def _encrypt_location(text: str) -> str:
        """简单加密：字符ASCII码+7，然后反转字符串"""
        encrypted = ''.join(chr(ord(c) + 7) for c in text)
        return encrypted[::-1]

    @staticmethod
    def _decrypt_location(encrypted: str) -> str:
        """解密：反转字符串，然后字符ASCII码-7"""
        reversed_text = encrypted[::-1]
        return ''.join(chr(ord(c) - 7) for c in reversed_text)

    def draw(self, dr: svgwrite.Drawing, size: XY, offset: XY):
        """For each track, draw it on the poster."""
        if self.poster.tracks is None:
            raise PosterError("No tracks to draw.")

        # 获取第一个 track 的第一个坐标点，添加到 SVG 的 defs 中
        if self.poster.tracks and self.poster.tracks[0].polylines:
            first_track = self.poster.tracks[0]
            first_polyline = first_track.polylines[0]
            if first_polyline:
                first_point = first_polyline[0]  # s2.LatLng 对象
                lat = first_point.lat().degrees
                lng = first_point.lng().degrees
                # 加密位置信息
                location_str = f"{lat},{lng}"
                encrypted_location = self._encrypt_location(location_str)
                # 在 defs 中添加一个不可见的 text 元素存储加密后的位置信息
                location_text = dr.text(encrypted_location, id="location", visibility="hidden")
                dr.defs.add(location_text)

            print(first_track.name, first_track.track_name)

            # 提取并保存 name 信息（按空格或" - "分割，取最后的内容）
            if hasattr(first_track, 'name') and first_track.name:
                name = first_track.name.strip()
                # 先尝试按 " - " 分割，如果存在则取后面的部分
                if ' - ' in name:
                    name = name.split(' - ')[-1]
                # 如果包含空格，取最后一部分
                elif ' ' in name:
                    name = name.split()[-1]
                # 在 defs 中添加 name 信息
                name_text = dr.text(name, id="name", visibility="hidden")
                dr.defs.add(name_text)

        for index, tr in enumerate(self.poster.tracks[::-1]):
            if tr.length >= 1500:
                tr.polylines = [filter_route(line, 500) for line in tr.polylines]

            for line in project(tr.bbox(), size, offset, tr.polylines):
                dr.add(
                    dr.path(d="M" + " L".join([f"{x},{y}" for x, y in line]), stroke=self.poster.colors["track"],
                            fill='none', id="runPath", stroke_width=0.5))
                # Draw start and end circles
                start = line[0]
                end = line[-1]
                # Calculate direction for the triangle at start
                next_point = line[1]
                angle = atan2(next_point[1] - start[1], next_point[0] - start[0])
                angle_deg = degrees(angle)

                # Triangle size and drawing
                triangle_size = 2.5
                triangle = dr.add(dr.polygon(points=[(start[0], start[1] - triangle_size),
                                                       (start[0] - triangle_size / 2, start[1]),
                                                       (start[0] + triangle_size / 2, start[1])],
                                             fill=self.poster.colors["special"]))
                # Rotate triangle to match the path direction
                triangle.rotate(angle_deg, center=start)

                # Square size and drawing
                square_size = 2.5
                square_center = (end[0] - square_size / 2, end[1] - square_size / 2)
                dr.add(dr.rect(insert=square_center, size=(square_size, square_size),
                               fill=self.poster.colors["special2"]))

                # Add a circle that will move along the path
                moving_circle = dr.circle(center=start, r=1.25, stroke=self.poster.colors["track"],
                                          fill=self.poster.colors["track"])
                dr.add(moving_circle)

                adjusted_points = [(x - start[0], y - start[1]) for x, y in line]

                # Add animation to the circle to move along the path
                animate_motion = dr.animateMotion(
                  path="M" + " L".join([f"{x},{y}" for x, y in adjusted_points]),
                  dur=f"{self.poster.animation_time}s", begin="0s", fill="freeze", repeatCount="indefinite")
                moving_circle.add(animate_motion)
