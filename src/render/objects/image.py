from __future__ import annotations

import typing

import numpy
import pyopencl as cl
from PIL import Image

from render.rendering.pillow.drawing import ImageDrawCombination
from ..component import DrawableComponent, get_box_from_transform
from ..rendering.opencl.component import DrawableComponentHAPillowRenderer
from ..rendering.opencl.renderer import HAPillowRenderer, include_general_functions
from ..rendering.pillow.component import DrawableComponentPillowRenderer

from ..transform import Transform


class ImagePillowRenderer(DrawableComponentPillowRenderer):
    component: ImageComponent

    # noinspection PyProtectedMember
    def _draw(self, target: ImageDrawCombination, transform: Transform):
        if transform.scale == (1, 1) and transform.angle == 0 and False:
            # just a simple paste
            target.image.paste(self.component._image, (int(transform.position[0] - transform.anchor[0]),
                                                       int(transform.position[1] - transform.anchor[1])))
        else:
            # use internal methods to prevent creating more non-pooled images

            self.component._image.load()

            if self.component._image.mode != "RGBA":
                with self.renderer.image_pool.request_image(self.component._image.width,
                                                            self.component._image.height) as image:
                    image.image.paste(self.component._image)

                    target.image.im.transform2((0, 0, target.image.width, target.image.height),
                                               image.image.im, Image.AFFINE, tuple(transform),
                                               self.component.image_resample, 0)

            else:
                target.image.im.transform2((0, 0, target.image.width, target.image.height),
                                           self.component._image.im, Image.AFFINE, tuple(transform),
                                           self.component.image_resample, 0)


draw_image = """
__constant sampler_t sampler = CLK_NORMALIZED_COORDS_FALSE | CLK_FILTER_NEAREST | CLK_ADDRESS_CLAMP_TO_EDGE;

__kernel void __NAME(__write_only image2d_t target, __read_only image2d_t image, 
                        float t1, float t2, float t3, float t4, float t5, float t6)
{
    int x = get_global_id(0);
    int y = get_global_id(1);

    int2 coords = {
        x * t1 + y * t2 + t3,
        x * t4 + y * t5 + t6
    };
    
    int2 size = get_image_dim(image);

    if(coords.x > 0 && coords.x < size.x && coords.y > 0 && coords.y < size.y) {
        float4 color = read_imagef(image, sampler, coords);
        write_imagef(target, (int2)(x, y), color);
    }
}
"""


class RectangleHAPillowRenderer(DrawableComponentHAPillowRenderer):
    component: ImageComponent

    def _enqueue(self, target: cl.Image, transform: Transform, *, event=None) -> cl.Event:
        rectangle_kernel: cl.Kernel = self.renderer.programs["draw_rectangle"].draw_rect

        rectangle_kernel.set_arg(0, target)
        rectangle_kernel.set_arg(1, numpy.array(self.component.image))

        for idx, val in enumerate(transform.reverse_matrix_values()):
            rectangle_kernel.set_arg(idx + 3, cl.cltypes.float(val))

        return cl.enqueue_nd_range_kernel(self.renderer.queue, rectangle_kernel, self.renderer.scene_shape, None)

    @classmethod
    def register_programs(cls, renderer: HAPillowRenderer, isolation):
        cls.mask_image_binding = isolation.register_kernel("draw_image", draw_image)


class ImageComponent(DrawableComponent):
    def __init__(self, scene, image):
        super().__init__(scene)

        self._image: Image.Image = image
        self.image_resample = Image.BICUBIC

        self.loop = -1
        self.required_loop = 1
        self.start_second = scene.current_second

    @property
    def image(self):
        return self._image

    @image.setter
    def image(self, value):
        self._image = value
        self.cache = None

    @property
    def width(self):
        return self._image.width

    @property
    def height(self):
        return self._image.height

    @property
    def size(self):
        return self._image.size

    @property
    def animated(self):
        # only certain formats having is_animated is a bit of a bad decision but alright
        return getattr(self.image, "is_animated", False)

    @property
    def duration(self):
        if self.animated:
            return sum(self.get_durations())

    def get_durations(self):
        cache = self.cache

        if cache is None:
            # get durations of all frames

            cache = []
            self._image.seek(0)

            while True:
                try:
                    cache.append(self._image.info['duration'] / 1000)
                    self._image.seek(self._image.tell() + 1)
                except EOFError:
                    break

            self.cache = cache

        return cache

    def cleanup(self):
        self._image.close()

    def reset(self):
        self.start_second = self.scene.current_second

    def get_next_update(self, t) -> typing.Optional[typing.Tuple[typing.Optional[float], typing.Callable, bool]]:
        if self.animated and self.loop != 0:
            durations = self.get_durations()
            anim_second = t - self.start_second

            if anim_second < 0:
                return self.start_second, lambda _: self._image.seek(0), self.required_loop in (-1, 0)

            current_frame = 0
            current_loop = 1
            current_duration = 0

            while current_duration <= anim_second:
                if current_frame >= len(durations):
                    current_frame = 0
                    current_loop += 1

                    if current_loop > self.loop != -1:
                        return

                current_duration += durations[current_frame]
                current_frame += 1

            return (current_duration + self.start_second, lambda _: self._image.seek(current_frame - 1),
                    current_loop <= self.required_loop or self.required_loop == -1)

    def get_renderers(self):
        from ..rendering.pillow.renderer import PillowRenderer

        return {
            PillowRenderer: ImagePillowRenderer
        }
