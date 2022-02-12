from __future__ import annotations

import math
import time
import typing
from typing import TYPE_CHECKING
from bisect import insort


if TYPE_CHECKING:
    from render.processing.component import PassivelyUpdatedComponent, ActivelyUpdatedComponent
    from render.processing.types import Update


class PassiveUpdateFramesTracker:
    __slots__ = (
        "_update_dict",
        "_ordered_updates",
        "_required_updates"
    )

    def __init__(self):
        """This class is to be made as time-efficient as possible"""

        self._update_dict: typing.Dict[float, typing.List[typing.Callable]] = {}
        self._ordered_updates = []
        self._required_updates = []

    def add_update(self, update: Update):
        second = update.second

        if second not in self._update_dict:  # O(1) complexity compared to O(n) of the list
            insort(self._ordered_updates, second)
            self._update_dict[second] = [update.func]

        else:
            self._update_dict[second].append(update.func)

        if update.required:
            insort(self._required_updates, update.second)

    def remove_update(self, update: Update):
        second = update.second

        if second in self._update_dict:
            updates = self._update_dict[second]
            updates.remove(update.func)

            if not updates:
                del self._update_dict[second]

            self._ordered_updates.remove(update)

            if update.required:
                self._required_updates.remove(update.second)

    def get_next(self):
        if not self._ordered_updates:
            return None, None

        second = self._ordered_updates[0]
        return second, self._update_dict[second]

    def discard(self):
        del self._update_dict[self._ordered_updates.pop(0)]


class Scheduler:
    __slots__ = (
        "__passive_tracker",
        "__dirty_update_frames",
        "__last_required_update_frame",

        "__actively_processed_objects",

        "current_second",
        "current_frame_second",

        "__first_frame",
        "__has_yielded",

        "min_duration",
        "min_frame_duration"
    )

    def __init__(self):
        self.__passive_tracker = PassiveUpdateFramesTracker()
        self.__last_required_update_frame: int = -1

        self.__actively_processed_objects: typing.List[ActivelyUpdatedComponent] = []

        self.current_second: float = 0
        self.current_frame_second: float = 0

        self.__first_frame: bool = True
        self.__has_yielded: bool = False

        self.min_duration: float = 0
        self.min_frame_duration: float = 1 / 60

    def __iter__(self):
        while True:
            next_second, update_funcs = self.__passive_tracker.get_next()

            if next_second is None:
                next_second = math.inf
                update_funcs = []
                update_required = False
                pop_passive = False

            else:
                update_required = True
                pop_passive = True

            for obj in self.__actively_processed_objects:
                candidate_update_collection = obj.get_next_update(self.current_second)

                if candidate_update_collection is not None:
                    candidate_second, candidate_func, is_required = candidate_update_collection

                    if self.__first_frame:
                        should_add = 0 <= candidate_second <= next_second

                    else:
                        should_add = self.current_second < candidate_second <= next_second

                    if should_add:
                        if candidate_second < next_second:
                            update_funcs = []
                            pop_passive = False
                            next_second = candidate_second

                        update_funcs.append(candidate_func)

                        update_required = update_required or is_required

            if update_funcs and (update_required or self.min_duration > self.current_second):
                self.current_second = next_second

                for func in update_funcs:
                    func(next_second)

                if pop_passive:
                    self.__passive_tracker.discard()

                if self.__first_frame or self.min_frame_duration <= self.current_second - self.current_frame_second:
                    yield "render"

                    self.current_frame_second = self.current_second

                    if not self.__first_frame:
                        yield self.current_second
                        self.__has_yielded = True

                    self.__first_frame = False

            else:
                if self.min_duration > self.current_second or not self.__has_yielded:
                    yield self.min_duration
                    self.__has_yielded = True

                return

    def add_passive_object(self, obj: PassivelyUpdatedComponent):
        for update in obj.get_all_updates():
            if self.__first_frame:
                should_add = 0 <= update.second

            else:
                should_add = self.current_second < update.second

            if should_add:
                self.__passive_tracker.add_update(update)

    def add_active_object(self, obj: ActivelyUpdatedComponent):
        self.__actively_processed_objects.append(obj)

    def remove_passive_object(self, obj: PassivelyUpdatedComponent):
        for update in obj.get_all_updates():
            self.__passive_tracker.remove_update(update)

    def remove_active_object(self, obj: ActivelyUpdatedComponent):
        self.__actively_processed_objects.remove(obj)

    @property
    def first_frame(self):
        return self.__first_frame
