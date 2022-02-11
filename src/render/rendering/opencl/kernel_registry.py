from __future__ import annotations

import contextlib
import typing
from typing import TYPE_CHECKING

import pyopencl as cl

if TYPE_CHECKING:
    pass


class BoundKernel:
    def __init__(self, program: KernelRegistryProgram, name: str):
        self.name = name
        self.program = program

    @property
    def kernel(self) -> typing.Optional[cl.Kernel]:
        return self.program.get_kernel(self.name)


class KernelRegistryIsolation:
    def __init__(self, program: KernelRegistryProgram):
        self.idx = 0
        self.program = program
        self.unique_name_bind = {}
        self.kernel_bindings = {}

    def get_or_create(self, func_name: str) -> str:
        if func_name not in self.unique_name_bind:
            name = f"_{self.program.isolation_idx}_{self.idx}"
            self.unique_name_bind[func_name] = name
            self.idx += 1
            return name

        return self.unique_name_bind[func_name]

    def register_kernel(self, func_name: str, code: str):
        name = self.get_or_create(func_name)
        self.unique_name_bind[func_name] = name
        self.program.funcs[name] = code.replace("__NAME", name)

        bind = BoundKernel(self.program, name)
        self.kernel_bindings[func_name] = bind

        return bind

    def __getitem__(self, item):
        return self.get_or_create(item)


class KernelRegistryProgram:
    def __init__(self, registry: KernelRegistry):
        self._registry = registry
        self._compiled: typing.Optional[cl.Program] = None

        self.funcs: typing.Dict[str, str] = {}
        self.isolation_idx: int = 0

    @contextlib.contextmanager
    def isolate(self):
        try:
            yield KernelRegistryIsolation(self)

        finally:
            self.isolation_idx += 1

    def get_kernel(self, name):
        if self._compiled is None:
            return None

        try:
            return getattr(self._compiled, name)

        except cl.LogicError:
            return None

    def compile(self):
        if self._compiled is not None:
            return

        if self.funcs:
            c_program = cl.Program(self._registry.context, "".join(self.funcs.values())).build()
            self._compiled = c_program


class KernelRegistry:
    def __init__(self, context: cl.Context):
        self.context = context

    def create_program(self):
        return KernelRegistryProgram(self)
