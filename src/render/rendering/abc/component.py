from __future__ import annotations

import abc

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from render.rendering.abc.renderer import Renderer
    from render.component import DrawableComponent


class DrawableComponentRenderer(abc.ABC):
    def __init__(self, renderer: Renderer, component: DrawableComponent):
        self._component = component
        self._renderer = renderer

    @property
    def component(self):
        return self._component

    @property
    def renderer(self):
        return self._renderer
