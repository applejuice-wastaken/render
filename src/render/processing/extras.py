from __future__ import annotations

import abc
import functools
import inspect
import typing
from typing import TYPE_CHECKING

from render.processing.component import ActivelyUpdatedComponent

if TYPE_CHECKING:
    pass


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


class BaseLifecycleComponent(ActivelyUpdatedComponent, abc.ABC):
    def __init__(self, scene):
        super().__init__(scene)

        self._lifecycle_generator = _wrap_gen(self.lifecycle)(scene.scheduler.current_second)

        self._generator_just_started = True
        self._next_tick = scene.scheduler.current_second
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