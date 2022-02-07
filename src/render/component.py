from __future__ import annotations

import abc
import functools
import inspect
import typing

from PIL import Image

from .deferrer import DeferredSetter
from .drawer import ImageDrawCombination
from .transform import Transform, transform_in_transform

if typing.TYPE_CHECKING:
    from .scene import Scene


def _wrap_gen(func):
    """Made to ensure that non-generator functions return a generator anyway.
    This is here to not clobber the LifecycleComponent logic with handling non-generator lifecycles"""

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        val = func(*args, **kwargs)

        if inspect.isgenerator(val):
            return (yield from val)

        else:
            return val

    return wrapped


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

    def get_next_update(self, t) -> typing.Optional[typing.Tuple[typing.Optional[float], typing.Callable, bool]]:
        pass

    def cleanup(self):
        pass

    @property
    def defer(self):
        return DeferredSetter(self)


class BaseLifecycleComponent(Component, abc.ABC):
    def __init__(self, scene):
        super().__init__(scene)

        self._lifecycle_generator = _wrap_gen(self.lifecycle)(scene.current_second)

        self._generator_just_started = True
        self._next_tick = scene.current_second
        self._next_update_required = True
        self._generator_ran = False

    @abc.abstractmethod
    def lifecycle(self, t) -> typing.Union[typing.Optional[float], typing.Generator[float, float, float]]:
        pass

    def get_next_update(self, t):
        if not self._generator_ran:
            return self._next_tick, self._update, self._next_update_required

        else:
            return self._next_tick, lambda _: None, self._next_update_required

    def _update(self, t):
        try:
            if self._generator_just_started:
                to_send = None

            else:
                to_send = t

            yielded = self._lifecycle_generator.send(to_send)

            if isinstance(yielded, tuple):
                next_tick, required = yielded

            else:
                next_tick, required = yielded, True

            if next_tick is None:
                next_tick = 0

            self._next_tick = next_tick + self._next_tick
            self._next_update_required = required

        except StopIteration as e:
            self._generator_ran = True

            if isinstance(e.value, tuple):
                next_tick, required = e.value

            else:
                next_tick, required = e.value, True

            if next_tick is None:
                next_tick = 0

            self._next_update_required = required
            self._next_tick = next_tick + self._next_tick


class LifecycleComponent(BaseLifecycleComponent, abc.ABC):
    def __init__(self, scene):
        super().__init__(scene)
        self._update(scene.current_second)


class DrawableComponent(Component, abc.ABC):
    def __init__(self, scene):
        super().__init__(scene)
        self.mask: typing.Optional[DrawableComponent] = None
        self.mask_channel = "A"
        self.local_mask = True
        self.mask_transform_resample = Image.BICUBIC
        self.transform = Transform()
        self.z = 0

    def draw(self, target: ImageDrawCombination, transform: Transform):
        if self.mask is not None:
            self_new_transform = transform_in_transform(transform, self.transform)

            with self.scene.image_pool.request_image(target.image.width, target.image.height,
                                                     exact_dimensions=False) as self_image:
                self._draw(self_image, self_new_transform)

                # self_image.image.show()
                # we calculate the mask transform

                if self.local_mask:
                    mask_new_transform = transform_in_transform(transform, self.transform)
                else:
                    mask_new_transform = transform

                with self.scene.image_pool.request_image(self_image.image.width, self_image.image.height) as mask_image:

                    self.mask.draw(mask_image, mask_new_transform)

                    with self.scene.image_pool.request_image(self_image.image.width, self_image.image.height,
                                                             exact_dimensions=False) as intermediate:

                        # masks do not blend with the target image, has to create another intermediate image

                        if self.mask_channel != "A":
                            image = mask_image.image.getchannel(self.mask_channel)

                            intermediate.image.paste(self_image.image,
                                                     (0, 0),
                                                     mask=image)
                        else:

                            intermediate.image.paste(self_image.image,
                                                     (0, 0),
                                                     mask=mask_image.image)

                        target.image.alpha_composite(intermediate.image,
                                                     (0, 0))

        else:
            self._draw(target, transform_in_transform(transform, self.transform))

    @abc.abstractmethod
    def _draw(self, target: ImageDrawCombination, transform: Transform):
        pass
