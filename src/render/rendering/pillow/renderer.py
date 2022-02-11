from __future__ import annotations

from typing import TYPE_CHECKING

import numpy

from render.rendering.abc import Renderer
from render.rendering.pillow.drawing import ImagePool

if TYPE_CHECKING:
    pass


class PillowRenderer(Renderer):
    NAME = "PILLOW"

    def __init__(self):
        super().__init__()
        self.pool = ImagePool()

    def init_scene(self, scene):
        super(PillowRenderer, self).init_scene(scene)

    def render_frame(self):
        with self.pool.request_image(self.scene.width, self.scene.height) as image:
            for obj in self.scene.drawing_objects:
                obj.renderer.draw(image, self.scene.initial_transform)

            return numpy.array(image.image)
