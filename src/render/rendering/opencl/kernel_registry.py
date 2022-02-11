from __future__ import annotations

import contextlib
import math
import string
import typing
from typing import TYPE_CHECKING

import pyopencl as cl

if TYPE_CHECKING:
    from render.rendering.opencl.component import DrawableComponentHAPillowRenderer

header_code = """
__constant sampler_t sampler = ;
"""


def to_letters(i: int):
    return (
            string.ascii_lowercase[i % len(string.ascii_lowercase)] +
            ("" if i < len(string.ascii_lowercase) else to_letters(math.floor(i)))
    )


class BoundKernel:
    def __init__(self, program: cl.Program, name: str):
        self.name = name
        self.program = program

    @property
    def kernel(self) -> typing.Optional[cl.Kernel]:
        return getattr(self.program, self.name)


class KernelRegistry:
    def __init__(self, context: cl.Context):
        self.context = context
        self.registered_classes = {}

    def init_class(self, cls):
        self.registered_classes[cls] = {}
        return ClassBoundKernelRegistry(self, cls)

    def registered(self, cls):
        return cls in self.registered_classes


class ClassBoundKernelRegistry:
    def __init__(self, registry: KernelRegistry, cls: typing.Type[DrawableComponentHAPillowRenderer]):
        self.cls = cls
        self.registry = registry

    # noinspection PyProtectedMember
    def register_program(self, kernel_name, code):
        program = cl.Program(self.registry.context, code).build()
        binding = BoundKernel(program, kernel_name)
        self.registry.registered_classes[self.cls][kernel_name] = binding
