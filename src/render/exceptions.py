from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class RendererCompatibilityException(Exception):
    def __init__(self, renderer, component):
        super(RendererCompatibilityException, self).__init__(
            f"Component {component!r} is not compatible with renderer {type(renderer)!r}"
        )
