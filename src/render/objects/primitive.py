from ..drawer import ImageDrawCombination
from ..component import DrawableComponent, get_box_from_transform
from ..transform import Transform


class RectangleComponent(DrawableComponent):
    def __init__(self, scene, width, height, fill):
        super().__init__(scene)

        self.fill = fill
        self.height = height
        self.width = width

        self.rectangle_optimization = True

    def _draw(self, target: ImageDrawCombination, transform: Transform):
        if self.rectangle_optimization and transform.angle == 0:
            target.draw.rectangle((
                transform.position[0] - (transform.scale[0] * transform.anchor[0]),
                transform.position[1] - (transform.scale[1] * transform.anchor[1]),
                (transform.position[0] + self.width) - (transform.scale[0] * transform.anchor[0]),
                (transform.position[1] + self.height) - (transform.scale[1] * transform.anchor[1])
            ), fill=self.fill)

        else:
            points = (
                transform.solve((0, 0)),
                transform.solve((0, self.height)),
                transform.solve((self.width, self.height)),
                transform.solve((self.width, 0))
            )

            target.draw.polygon(points, self.fill)

    def get_active_box(self):
        return get_box_from_transform(self.transform, (
            (0, 0),
            (0, self.height),
            (self.width, self.height),
            (self.width, 0)
        ))
