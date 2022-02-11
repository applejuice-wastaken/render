from __future__ import annotations

import os
import typing
from typing import TYPE_CHECKING

from render.execute import run_scene
from render.rendering.opencl.renderer import HAPillowRenderer
from render.rendering.pillow.renderer import PillowRenderer
from render.scene import Scene

import pyopencl as cl

if TYPE_CHECKING:
    pass

# since the scene has no animated objects
# it will output a single image
# run_scene will catch that and return an inherently static image


class MyScene(Scene):
    def lifecycle(self, t):
        self.width = 100
        self.height = 100

        rect = self.create_rectangle(10, 10, (255, 255, 255, 255))
        self.draw_object(rect)
        return 0


platforms = cl.get_platforms()
platform = platforms[0]
devices = platform.get_devices(cl.device_type.GPU)
device = devices[0]
context = cl.Context([device])

renderer = HAPillowRenderer(context)
io, animated = run_scene(MyScene(renderer=renderer))

# proof that it's not animated
assert not animated

renderer.queue.finish()
with open("out.png", "wb") as fp:
    fp.write(io.getvalue())
