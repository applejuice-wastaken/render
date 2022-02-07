import typing

from ..component import DrawableComponent
from ..drawer import ImageDrawCombination
from ..transform import Transform


class ContainerComponent(DrawableComponent):
    def __init__(self, scene):
        super().__init__(scene)
        self.drawing_objects: typing.List[DrawableComponent] = []

    def _draw(self, target: ImageDrawCombination, transform: Transform):
        for obj in self.drawing_objects:
            obj.draw(target, transform)

    def draw_object(self, obj):
        self.drawing_objects.append(obj)

    def remove_draw_object(self, obj):
        self.drawing_objects.remove(obj)
