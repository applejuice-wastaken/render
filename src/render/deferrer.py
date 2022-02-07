import enum
from collections import namedtuple
from enum import Enum


class AccessType(Enum):
    ATTR = enum.auto()
    ITEM = enum.auto()


Access = namedtuple("Access", "value kind")


class DeferredSetter:
    def __init__(self, target, access_stack=()):
        self.access_stack = access_stack
        self.target = target

    def __call__(self, value):
        current = self.target

        for idx, access in enumerate(self.access_stack):
            if idx == len(self.access_stack) - 1:
                if access.kind == AccessType.ATTR:
                    setattr(current, access.value, value)

                else:
                    current[access.value] = value

            if access.kind == AccessType.ATTR:
                current = getattr(current, access.value)

            else:
                current = current[access.value]

    def __getattr__(self, item):
        return DeferredSetter(self.target, self.access_stack + (Access(item, AccessType.ATTR),))

    def __getitem__(self, item):
        return DeferredSetter(self.target, self.access_stack + (Access(item, AccessType.ITEM),))
