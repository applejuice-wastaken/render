from __future__ import annotations

import inspect
import types
import typing

import pytweening

from ..processing.component import PassivelyUpdatedComponent
from ..processing.types import Update

if typing.TYPE_CHECKING:
    from ..scene import Scene


class TweenComponent(PassivelyUpdatedComponent):
    def __init__(self, scene: Scene, tween: typing.Union[str, typing.Callable], callback, *,
                 duration, start_second=None, begin_value=0, end_value=1, required=True):

        super().__init__(scene)
        self.required = required
        self.callback = callback

        self.start_second = scene.scheduler.current_second if start_second is None else start_second
        self.duration = duration

        self.end_value = end_value
        self.begin_value = begin_value

        if isinstance(tween, str):
            self.tween: types.FunctionType = getattr(pytweening, tween, lambda: None)

            if len(inspect.signature(self.tween).parameters) != 1:
                raise ValueError(f"{tween} is not a valid tween name")

        else:
            self.tween = tween

    def _get_all_updates(self):
        ret = []
        second = self.start_second

        def u(ti):
            tween_progress = (ti - self.start_second) / self.duration

            if 0 < tween_progress < 1:
                self.callback(self.tween(tween_progress) * (self.end_value - self.begin_value) + self.begin_value)

        while second < self.start_second + self.duration:
            ret.append(Update(second, u, self.required))

            second += 1 / 60

        ret.append(Update(self.start_second + self.duration, u, self.required))

        return ret
