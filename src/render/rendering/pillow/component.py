from __future__ import annotations

import abc
from typing import TYPE_CHECKING

from render.rendering.abc import DrawableComponentRenderer

from render.transform import Transform, transform_in_transform

try:
    import PIL

except ModuleNotFoundError:
    pillow_installed = False
else:
    pillow_installed = True

if TYPE_CHECKING:
    from .drawing import ImageDrawCombination


class DrawableComponentPillowRenderer(DrawableComponentRenderer):
    def draw(self, target: ImageDrawCombination, transform: Transform):
        if self.component.mask is not None:
            self_new_transform = transform_in_transform(transform, self.component.transform)

            with self.renderer.image_pool.request_image(target.image.width, target.image.height,
                                                        exact_dimensions=False) as self_image:
                self._draw(self_image, self_new_transform)

                # self_image.image.show()
                # we calculate the mask transform

                if self.component.local_mask:
                    mask_new_transform = transform_in_transform(transform, self.component.transform)
                else:
                    mask_new_transform = transform

                with self.renderer.image_pool.request_image(self_image.image.width,
                                                            self_image.image.height) as mask_image:

                    self.component.mask.renderer.draw(mask_image, mask_new_transform)

                    with self.renderer.image_pool.request_image(self_image.image.width, self_image.image.height,
                                                                exact_dimensions=False) as intermediate:

                        # masks do not blend with the target image, has to create another intermediate image

                        if self.component.mask_channel != "A":
                            image = mask_image.image.getchannel(self.component.mask_channel)

                            intermediate.image.paste(self_image.image,
                                                     (0, 0),
                                                     mask=image)
                        else:

                            intermediate.image.paste(self_image.image,
                                                     (0, 0),
                                                     mask=mask_image.image)

                        target.image.alpha_composite(intermediate.image,
                                                     (0, 0))

        else:
            self._draw(target, transform_in_transform(transform, self.component.transform))

    @abc.abstractmethod
    def _draw(self, target: ImageDrawCombination, transform: Transform):
        pass
