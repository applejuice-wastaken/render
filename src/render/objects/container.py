import typing

from ..component import DrawableComponent
from render.rendering.pillow.drawing import ImageDrawCombination
from ..rendering.pillow.component import DrawableComponentPillowRenderer
from ..transform import Transform


class ContainerPillowRenderer(DrawableComponentPillowRenderer):
    def _draw(self, target: ImageDrawCombination, transform: Transform):
        for obj in self.component.__drawing_objects:
            obj.draw(target, transform)


class ContainerComponent(DrawableComponent):
    def __init__(self, scene):
        super().__init__(scene)
        self.drawing_objects: typing.List[DrawableComponent] = []

    def draw_object(self, obj):
        self.drawing_objects.append(obj)

    def remove_draw_object(self, obj):
        self.drawing_objects.remove(obj)

    def get_renderers(self):
        from render.rendering.pillow.renderer import PillowRenderer
        return {
            PillowRenderer: ContainerPillowRenderer
        }