from __future__ import annotations

import typing

import numpy
import pyopencl as cl
import pyopencl.array

from render.rendering.pillow.drawing import ImageDrawCombination
from ..component import DrawableComponent
from ..rendering.opencl.component import DrawableComponentHAPillowRenderer
from ..rendering.opencl.renderer import HAPillowRenderer
from ..rendering.pillow.component import DrawableComponentPillowRenderer
from ..rendering.pillow.renderer import PillowRenderer
from ..transform import Transform


if typing.TYPE_CHECKING:
    from ..rendering.opencl.kernel_registry import ClassBoundKernelRegistry


class RectanglePillowRenderer(DrawableComponentPillowRenderer):
    def _draw(self, target: ImageDrawCombination, transform: Transform):
        if self.component.rectangle_optimization and transform.angle == 0:
            target.draw.rectangle((
                transform.position[0] - (transform.scale[0] * transform.anchor[0]),
                transform.position[1] - (transform.scale[1] * transform.anchor[1]),
                (transform.position[0] + self.component.width) - (transform.scale[0] * transform.anchor[0]),
                (transform.position[1] + self.component.height) - (transform.scale[1] * transform.anchor[1])
            ), fill=self.component.fill)

        else:
            points = (
                transform.solve((0, 0)),
                transform.solve((0, self.component.height)),
                transform.solve((self.component.width, self.component.height)),
                transform.solve((self.component.width, 0))
            )

            target.draw.polygon(points, self.component.fill)


draw_rectangle = """
__kernel void draw_rectangle(__write_only image2d_t target, float4 color, float2 size, 
                        float t1, float t2, float t3, float t4, float t5, float t6)
{
    int x = get_global_id(0);
    int y = get_global_id(1);
    
    int2 coords = {
        x * t1 + y * t2 + t3,
        x * t4 + y * t5 + t6
    };
    
    if(coords.x > 0 && coords.x < size.x && coords.y > 0 && coords.y < size.y) {
        write_imagef(target, (int2)(x, y), color);
    }
}
"""


class RectangleHAPillowRenderer(DrawableComponentHAPillowRenderer):
    component: RectangleComponent

    def _enqueue(self, target: cl.Image, transform: Transform, *, event=None) -> cl.Event:
        rectangle_kernel: cl.Kernel = self.programs["draw_rectangle"]

        rectangle_kernel.set_arg(0, target)
        rectangle_kernel.set_arg(1, numpy.array(self.component.fill))
        rectangle_kernel.set_arg(2, numpy.array((self.component.width, self.component.height),
                                                dtype=cl.array.vec.float2))

        for idx, val in enumerate(transform.reverse_matrix_values()):
            rectangle_kernel.set_arg(idx + 3, cl.cltypes.float(val))

        return cl.enqueue_nd_range_kernel(self.renderer.queue, rectangle_kernel, self.renderer.scene_shape, None,
                                          wait_for=None if event is None else [event])

    @classmethod
    def register_programs(cls, renderer: HAPillowRenderer, reg: ClassBoundKernelRegistry):
        reg.register_program("draw_rectangle", draw_rectangle)


class RectangleComponent(DrawableComponent):
    def __init__(self, scene, width, height, fill):
        super().__init__(scene)

        self.fill = fill
        self.height = height
        self.width = width

        self.rectangle_optimization = True

    def get_renderers(self):
        return {
            PillowRenderer: RectanglePillowRenderer,
            HAPillowRenderer: RectangleHAPillowRenderer
        }
