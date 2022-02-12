from __future__ import annotations

import abc
import typing

from PIL import Image

from .deferrer import DeferredSetter
from .exceptions import RendererCompatibilityException

from .transform import Transform

if typing.TYPE_CHECKING:
    from .rendering.abc import Renderer, DrawableComponentRenderer
    from .scene import Scene


def normalize_box(box):
    if len(box) == 2 and all(isinstance(sub, tuple) and len(sub) == 2 for sub in box):
        return *box[0], *box[1]

    elif len(box) == 4 and all(isinstance(n, (int, float)) for n in box):
        return box

    raise ValueError("Unknown box format")


def get_box_from_transform(transform, raw_points):
    box = None

    for point in raw_points:
        transformed = transform.solve(point)

        if box is None:
            box = [transformed[0], transformed[1], transformed[0], transformed[1]]

        else:
            if transformed[0] < box[0]:
                box[0] = transformed[0]

            if transformed[1] < box[1]:
                box[1] = transformed[1]

            if transformed[0] > box[2]:
                box[2] = transformed[0]

            if transformed[1] > box[3]:
                box[3] = transformed[1]

    return tuple(box)


class Component:
    def __init__(self, scene: Scene, *, key=None):
        self.scene = scene
        self._key = key
        self._cache_value = None  # only set when there's no key for consistency

    @property
    def cache(self):
        if self._key is None:
            return self._cache_value

        return self.scene.cache_keys.get(self._key, None)

    @cache.setter
    def cache(self, value):
        if self._key is None:
            self._cache_value = value

        else:
            self.scene.cache_keys[self._key] = value

    @property
    def has_cache_key(self):
        return self._key is not None

    def cleanup(self):
        pass

    @property
    def defer(self):
        return DeferredSetter(self)


class DrawableComponent(Component, abc.ABC):
    def __init__(self, scene):
        super().__init__(scene)
        self.mask: typing.Optional[DrawableComponent] = None
        self.mask_channel = "A"
        self.local_mask = True
        self.mask_transform_resample = Image.BICUBIC
        self.transform = Transform()
        self.z = 0

        renderers = self.get_renderers()

        try:
            self.renderer = renderers[type(scene.renderer)](scene.renderer, self)

        except KeyError:
            raise RendererCompatibilityException(scene.renderer, self) from None

    @abc.abstractmethod
    def get_renderers(self) -> typing.Dict[typing.Type[Renderer], typing.Type[DrawableComponentRenderer]]:
        pass
