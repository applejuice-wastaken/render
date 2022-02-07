import typing

from PIL import Image

from ..component import DrawableComponent
from ..drawer import ImageDrawCombination
from ..transform import Transform


class TextComponent(DrawableComponent):
    def __init__(self, scene, text="", font=None):
        super().__init__(scene)

        self.text = text
        self.font = font

    def _draw(self, target: ImageDrawCombination, transform: Transform):
        if transform.scale == (1, 1) and transform.angle == 0:
            # just a simple paste
            target.draw.text((int(transform.position[0] - transform.anchor[0]),
                              int(transform.position[1] - transform.anchor[1])), self.text)
        else:
            with self.scene.image_pool.request_image(target.width, target.height) as image:
                image.draw.text((0, 0), self.text)

                with self.scene.image_pool.request_image(target.width, target.height) as intermediary:
                    intermediary.image.im.transform2((0, 0, intermediary.image.width, intermediary.image.height),
                                                     image.im, Image.AFFINE, tuple(transform), Image.NEAREST, 0)

                    target.image.alpha_composite(intermediary.image)

    def get_active_box(self) -> typing.Tuple[float, float, float, float]:
        pass
