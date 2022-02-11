from __future__ import annotations

from typing import TYPE_CHECKING

import numpy
import numpy as np

from render.rendering.abc import Renderer
import pyopencl as cl

from render.rendering.opencl.kernel_registry import KernelRegistry

if TYPE_CHECKING:
    pass

affine_transform = """
int2 transform(int2 coords, float3* transformationMatrix) {
    return (int2)(
        coords.x * transformationMatrix[0].x + coords.y * transformationMatrix[0].y + transformationMatrix[0].z, 
        coords.x * transformationMatrix[1].x + coords.y * transformationMatrix[1].y + transformationMatrix[1].z
    );
}
"""


def include_general_functions(code):
    return affine_transform + code


class BoundProgramRegistry:
    def __init__(self, renderer: HAPillowRenderer, cls):
        self.cls = cls
        self.renderer = renderer

    def __getitem__(self, item):
        return self.renderer.registered_classes[self.cls][item].kernel


class HAPillowRenderer(Renderer):
    def __init__(self, context):
        super().__init__()

        self.context = context
        self.queue = cl.CommandQueue(context)

        self.registered_classes = {}

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
        chunk_program = None

        for obj in self.scene.drawing_objects:
            if type(obj.renderer) not in self.registered_classes:
                if chunk_program is None:
                    chunk_program = self.kernel_registry.create_program()

                with chunk_program.isolate() as isolation:
                    type(obj.renderer).register_programs(self, isolation)

                    self.registered_classes[type(obj.renderer)] = isolation.kernel_bindings

        if chunk_program is not None:
            chunk_program.compile()
