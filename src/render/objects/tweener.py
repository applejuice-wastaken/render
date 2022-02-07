from __future__ import annotations

import inspect
import types
import typing

import pytweening

from ..component import Component

if typing.TYPE_CHECKING:
    from ..scene import Scene


class TweenComponent(Component):
    def __init__(self, scene: Scene, tween, callback, *, duration, start_second=None, begin_value=0, end_value=1,
                 required=True):
        super().__init__(scene)
        self.required = required
        self.callback = callback

        self.start_second = scene.current_second if start_second is None else start_second
        self.duration = duration

        self.end_value = end_value
        self.begin_value = begin_value

        self.tween: types.FunctionType = getattr(pytweening, tween, lambda: None)

        if len(inspect.signature(self.tween).parameters) != 1:
            raise ValueError(f"{tween} is not a valid tween name")

    def get_next_update(self, t) -> typing.Optional[typing.Tuple[typing.Optional[float], typing.Callable, bool]]:
        if t < self.start_second:
            return self.start_second, lambda _: self.callback(self.begin_value), self.required

        else:
            step_size = 1 / 60

            next_update = self.start_second

            while next_update < self.start_second + self.duration:
                next_update += step_size

                if t < next_update < self.start_second + self.duration:
                    tween_progress = (next_update - self.start_second) / self.duration
                    return next_update, lambda _: self.callback(self.tween(tween_progress) *
                                                                (self.end_value - self.begin_value)
                                                                + self.begin_value), self.required

            return self.start_second + self.duration, lambda _: self.callback(self.end_value), self.required
