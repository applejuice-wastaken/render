import typing

from PIL import Image

from ..component import DrawableComponent
from render.rendering.pillow.drawing import ImageDrawCombination
from ..rendering.pillow.component import DrawableComponentPillowRenderer
from ..transform import Transform


class TextPillowRenderer(DrawableComponentPillowRenderer):
    def _draw(self, target: ImageDrawCombination, transform: Transform):
        if transform.scale == (1, 1) and transform.angle == 0:
            # just a simple paste
            target.draw.text((int(transform.position[0] - transform.anchor[0]),
                              int(transform.position[1] - transform.anchor[1])), self.component.text)
        else:
            with self.renderer.image_pool.request_image(target.width, target.height) as image:
                image.draw.text((0, 0), self.component.text)

                with self.renderer.image_pool.request_image(target.width, target.height) as intermediary:
                    intermediary.image.im.transform2((0, 0, intermediary.image.width, intermediary.image.height),
                                                     image.im, Image.AFFINE, tuple(transform), Image.NEAREST, 0)

                    target.image.alpha_composite(intermediary.image)


class TextComponent(DrawableComponent):
    def __init__(self, scene, text="", font=None):
        super().__init__(scene)

        self.text = text
        self.font = font

    def get_renderers(self):
        from render.rendering.pillow.renderer import PillowRenderer
        return {
            PillowRenderer: TextPillowRenderer
        }
