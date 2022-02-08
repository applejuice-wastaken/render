from __future__ import annotations

import typing
from typing import TYPE_CHECKING

from render.execute import run_scene
from render.scene import Scene

if TYPE_CHECKING:
    pass

# since the scene has no animated objects
# it will output a single image
# run_scene will catch that and return an inherently static image


class MyScene(Scene):
    def lifecycle(self, t):
        self.width = 100
        self.height = 100

        rect = self.create_rectangle(10, 10, (255, 255, 255))
        self.draw_object(rect)
        return 0


io, animated = run_scene(MyScene())

# proof that it's not animated
assert not animated

with open("out.png", "wb") as fp:
    fp.write(io.getvalue())
