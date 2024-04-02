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

    def draw(self, dr: svgwrite.Drawing, size: XY, offset: XY):
        """For each track, draw it on the poster."""
        if self.poster.tracks is None:
            raise PosterError("No tracks to draw.")

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
