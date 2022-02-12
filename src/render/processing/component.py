from __future__ import annotations

import abc
import typing
from typing import TYPE_CHECKING

from render.component import Component
from render.processing.types import Update

if TYPE_CHECKING:
    pass


class ProcessedComponent(Component, abc.ABC):
    pass


class PassivelyUpdatedComponent(ProcessedComponent, abc.ABC):
    def __init__(self, scene):
        super().__init__(scene)

        self.updates = None

    def get_all_updates(self):
        if self.updates is None:
            self.updates = self._get_all_updates()

        return self.updates

    @abc.abstractmethod
    def _get_all_updates(self,) -> typing.List[Update]:
        pass

    def mark_dirty(self):
        self.scene.scheduler.remove_passive_object(self)
        self.updates = None
        self.scene.scheduler.add_passive_object(self)


class ActivelyUpdatedComponent(ProcessedComponent, abc.ABC):
    def get_next_update(self, t) -> typing.Optional[Update]:
        pass
