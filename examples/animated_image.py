from __future__ import annotations

import typing
from typing import TYPE_CHECKING

from render.execute import run_scene
from render.scene import Scene

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

        rect: RectangleComponent = self.create_rectangle(10, 10, (255, 255, 255))
        self.draw_object(rect)

        def u(value):
            rect.transform.position = (value, rect.transform.position[1])

        self.create_tween("easeInOutQuad", u, duration=10, begin_value=0, end_value=100)

        return 0


io, animated = run_scene(MyScene())

# proof that it's animated
assert animated

with open("out.gif", "wb") as fp:
    fp.write(io.getvalue())
