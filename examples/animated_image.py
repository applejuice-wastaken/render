from __future__ import annotations

import math
import time
from functools import partial
from typing import TYPE_CHECKING

from render.execute import run_scene
from render.rendering.opencl.renderer import HAPillowRenderer
from render.rendering.pillow.renderer import PillowRenderer
from render.scene import Scene
import pyopencl as cl

if TYPE_CHECKING:
    from render.objects.primitive import RectangleComponent

# since this scene has animated objects
# it will output a sequence of images
# run_scene will catch that and return an inherently animated image

# in this case the animated object is a tween object that animates the position of a rectangle object
# animated objects may update other's properties like this example


class MyScene(Scene):
    def lifecycle(self, t):
        self.width = 100
        self.height = 100

        for i in range(100):
            rect: RectangleComponent = self.create_rectangle(10, 10, (255, 255, 255, 255))
            self.draw_object(rect)

            def u(r, value):
                r.transform.position = (value, r.transform.position[1])

            self.create_tween("easeInOutQuad", partial(u, rect), duration=10, begin_value=0, end_value=100)

            def u(r, value):
                r.transform.position = (r.transform.position[0], value)

            self.create_tween("linear", partial(u, rect), duration=10, begin_value=0, end_value=100)

            def u(r, value):
                r.transform.angle = value

            self.create_tween("easeInSine", partial(u, rect), duration=10, begin_value=0, end_value=math.tau)

            yield 0.1

        return 0


platforms = cl.get_platforms()  # a platform corresponds to a driver (e.g. AMD)
platform = platforms[0]  # take first platform
devices = platform.get_devices(cl.device_type.GPU)  # get GPU devices of selected platform
device = devices[0]  # take first GPU
context = cl.Context([device])  # put selected GPU into context object

io, animated = run_scene(MyScene(renderer=HAPillowRenderer(context=context)))

# proof that it's animated
assert animated

with open("out.gif", "wb") as fp:
    fp.write(io.getvalue())
