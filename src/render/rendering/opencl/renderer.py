from __future__ import annotations

import typing
from typing import TYPE_CHECKING

import numpy
import numpy as np

from render.rendering.abc import Renderer
import pyopencl as cl

from render.rendering.opencl.kernel_registry import KernelRegistry

if TYPE_CHECKING:
    from render.rendering.opencl.component import DrawableComponentHAPillowRenderer


class BoundProgramRegistry:
    def __init__(self, renderer: HAPillowRenderer, cls):
        self.cls = cls
        self.renderer = renderer

    # noinspection PyProtectedMember
    def __getitem__(self, item):
        return self.renderer.kernel_registry.registered_classes[self.cls][item].kernel


class HAPillowRenderer(Renderer):
    def __init__(self, context):
        super().__init__()

        self.context = context
        self.queue = cl.CommandQueue(context)

        self.output_arr = None
        self.output = None

        self.kernel_registry = KernelRegistry(context)

    def init_scene(self, scene):
        super(HAPillowRenderer, self).init_scene(scene)
        self.output_arr = np.zeros((scene.width, scene.height, 4), np.uint8)
        self.output = self.create_blank_image()

    def render_frame(self):
        events = []

        cl.enqueue_fill_image(self.queue, self.output, numpy.zeros(self.scene_shape), (0, 0), self.scene_shape).wait()

        for obj in self.scene.drawing_objects:
            events.append(obj.renderer.enqueue(self.output, self.scene.initial_transform))

        cl.enqueue_copy(self.queue, self.output_arr, self.output, origin=(0, 0), region=self.scene_shape,
                        is_blocking=True)

        return self.output_arr

    def create_blank_image(self):
        f = cl.ImageFormat(cl.channel_order.RGBA, cl.channel_type.UNSIGNED_INT8)
        return cl.Image(self.context, cl.mem_flags.READ_WRITE, f, shape=self.scene_shape)

    def create_blank_np_array(self):
        return np.zeros((self.scene.width, self.scene.height), np.uint8)

    @property
    def scene_shape(self):
        return self.scene.width, self.scene.height

    def drawing_objects_changed(self):
        for obj in self.scene.drawing_objects:
            if type(obj.renderer) not in self.kernel_registry.registered_classes:
                self.register_class(type(obj.renderer))

    def register_class(self, cls: typing.Type[DrawableComponentHAPillowRenderer]):
        from render.rendering.opencl.component import DrawableComponentHAPillowRenderer  # circular import

        reg = self.kernel_registry.init_class(cls)
        cls.register_programs(self, reg)

        for supercls in cls.__bases__:
            if (issubclass(supercls, DrawableComponentHAPillowRenderer) and
                    "register_programs" in supercls.__dict__ and
                    not self.kernel_registry.registered(supercls)
            ):
                self.register_class(supercls)
