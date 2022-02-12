from __future__ import annotations

import dataclasses
import typing
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclasses.dataclass(frozen=True, slots=True)
class Update:
    second: float
    func: typing.Callable[[float], None]
    required: bool
