from __future__ import annotations

import abc
import typing
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from render.scene import Scene


class Renderer(abc.ABC):
    NAME = None

    def __init__(self):
        self._initialized = False
        self._scene: typing.Optional[Scene] = None

    @property
    def scene(self):
        return self._scene

    def init_scene(self, scene):
        if self._initialized:
            raise RuntimeError("A renderer can only be used once")

        self._initialized = True
        self._scene = scene

    @abc.abstractmethod
    def render_frame(self):
        pass

    def cleanup(self):
        pass

    def drawing_objects_changed(self):
        pass