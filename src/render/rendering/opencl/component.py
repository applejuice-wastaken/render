from __future__ import annotations

import abc
import typing
from typing import TYPE_CHECKING

from render.rendering.abc import DrawableComponentRenderer
from render.transform import Transform, transform_in_transform
import pyopencl as cl
from render.rendering.opencl.renderer import BoundProgramRegistry

if TYPE_CHECKING:
    from render.rendering.opencl.kernel_registry import KernelRegistryIsolation
    from render.rendering.opencl.renderer import HAPillowRenderer

masking_code = """
__constant sampler_t sampler = CLK_NORMALIZED_COORDS_FALSE | CLK_FILTER_NEAREST | CLK_ADDRESS_CLAMP_TO_EDGE;

float blend(float start, float end, float percentage) {
    return start * (1 - percentage) + end * percentage;
}

__kernel void __NAME(__write_only image2d_t target, __read_only image2d_t image, __read_only image2d_t mask, 
                         short channel)
{
    int x = get_global_id(0);
    int y = get_global_id(1);
    
    float4 mask_color = read_imagef(mask, sampler, (int2)(x, y));
    float4 image_color = read_imagef(image, sampler, (int2)(x, y));
    float4 target_color = read_imagef(target, sampler, (int2)(x, y));
    
    float blend = mask_color[channel];
    
    float4 blended = (float4)(blend(target_color[0], image_color[0], blend),
                               blend(target_color[1], image_color[1], blend),
                               blend(target_color[2], image_color[2], blend),
                               blend(target_color[3], image_color[3], blend))
    
    write_imagef(target, (int2)(x, y), blended);
}
"""


class DrawableComponentHAPillowRenderer(DrawableComponentRenderer, abc.ABC):
    renderer: HAPillowRenderer

    def __init__(self, renderer, component):
        super().__init__(renderer, component)

    def enqueue(self, target: cl.Image, transform: Transform, *, event: cl.Event = None) -> cl.Event:
        if self.component.mask is not None:
            self_new_transform = transform_in_transform(transform, self.component.transform)
            self_image = self.renderer.create_blank_image()

            self_event = self._enqueue(self_image, self_new_transform)

            if self.component.local_mask:
                mask_new_transform = transform_in_transform(transform, self.component.transform)
            else:
                mask_new_transform = transform

            mask_image = self.renderer.create_blank_image()

            mask_event = self.component.mask.renderer.enqueue(mask_image, mask_new_transform)
            mask_kernel: cl.Kernel = self.programs["mask_image"]

            mask_kernel.set_arg(0, target)
            mask_kernel.set_arg(1, self_image)
            mask_kernel.set_arg(2, mask_image)
            mask_kernel.set_arg(3, "RGBA".index(self.component.mask_channel))

            return cl.enqueue_nd_range_kernel(self.renderer.queue, mask_kernel, self.renderer.scene_shape, None,
                                              wait_for=[event, self_event, mask_event])
        else:
            return self._enqueue(target, transform_in_transform(transform, self.component.transform), event=event)

    @abc.abstractmethod
    def _enqueue(self, target: cl.Image, transform: Transform, *, event: cl.Event = None) -> cl.Event:
        pass

    @classmethod
    def register_programs(cls, renderer: HAPillowRenderer, isolation: KernelRegistryIsolation):
        cls.mask_image_binding = isolation.register_kernel("mask_image", masking_code)

    @property
    def programs(self):
        return BoundProgramRegistry(self.renderer, type(self))
