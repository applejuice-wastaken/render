from __future__ import annotations

import abc
import inspect
import typing
import time

from .component import Component, DrawableComponent
from .processing.component import ActivelyUpdatedComponent, ProcessedComponent
from .processing.extras import BaseLifecycleComponent
from .objects.container import ContainerComponent
from .objects.image import ImageComponent
from .objects.primitive import RectangleComponent
from .objects.text import TextComponent
from .objects.thread import ThreadComponent
from .objects.tweener import TweenComponent
from render.processing.scheduler import Scheduler

from .transform import Transform

if typing.TYPE_CHECKING:
    from .rendering.abc import Renderer


class Scene(BaseLifecycleComponent, abc.ABC):
    object_registry: typing.Dict[str, typing.Type[Component]] = {}

    def __init_subclass__(cls, **kwargs):
        cls.cache_keys = {}

    def __init__(self, *, renderer: Renderer):
        self.renderer = renderer
        self.scheduler = Scheduler()

        super().__init__(self)

        self.__drawing_objects: typing.List[DrawableComponent] = []
        self.__dirty_drawing_objects = False

        self._width = 0
        self._height = 0

        self.initial_transform = Transform()

        self.render_time = 0
        self.process_time = 0

        self.current_image = None

        self.scheduler.add_active_object(self)

    @property
    def drawing_objects(self):
        return tuple(self.__drawing_objects)

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @width.setter
    def width(self, value):
        if not self.scheduler.first_frame:
            raise RuntimeError("Width cannot be set after the first frame")

        self._width = value

    @height.setter
    def height(self, value):
        if not self.scheduler.first_frame:
            raise RuntimeError("Height cannot be set after the first frame")

        self._height = value

    @property
    def first_frame(self):
        return self._first_frame

    def __iter__(self):
        self._update(self.scheduler.current_second)
        self.renderer.init_scene(self)

        try:
            frame = None
            last_second = 0

            for command in self.scheduler:
                if isinstance(command, str):
                    frame = self.render_frame()

                else:
                    yield frame, command - last_second
                    last_second = command

        finally:
            self.cleanup_objects()

    def draw_object(self, obj):
        self.__drawing_objects.append(obj)
        self.__dirty_drawing_objects = True

    def remove_draw_object(self, obj):
        self.__drawing_objects.remove(obj)
        self.__dirty_drawing_objects = True

    def process_object(self, obj):
        if isinstance(obj, ActivelyUpdatedComponent):
            self.scheduler.add_active_object(obj)

        else:
            self.scheduler.add_passive_object(obj)

    def remove_process_object(self, obj):
        if isinstance(obj, ActivelyUpdatedComponent):
            self.scheduler.remove_active_object(obj)

        else:
            self.scheduler.remove_passive_object(obj)

    def render_frame(self):
        start = time.perf_counter()

        if self.__dirty_drawing_objects:
            self.__dirty_drawing_objects = False
            self.renderer.drawing_objects_changed()

        res = self.renderer.render_frame()
        self.render_time += time.perf_counter() - start
        return res

    def cleanup_objects(self):
        pass

    def create(self, cls, *args, **kwargs):
        init_kwargs = {}
        set_kwargs = {}

        detected_kwargs = []

        send_all = False

        for name, prop in inspect.signature(cls.__init__).parameters.items():
            if prop.kind == prop.VAR_KEYWORD:
                send_all = True
                break

            elif prop.kind == prop.KEYWORD_ONLY:
                detected_kwargs.append(name)

        for key, val in kwargs.items():
            if key == "key":
                set_kwargs["_key"] = val

            else:
                if send_all or key in detected_kwargs:
                    init_kwargs[key] = val

                set_kwargs[key] = val

        obj = cls(self, *args, **init_kwargs)

        for key, val in set_kwargs.items():
            chunks = key.split("__")
            current = obj

            for idx, chunk in enumerate(chunks):
                if hasattr(current, chunk):
                    if idx == len(chunks) - 1:
                        setattr(current, chunk, val)

                    else:
                        current = getattr(current, chunk)
                else:
                    raise ValueError(f"Object {current!r} has no property {chunk!r} to be set")

        if isinstance(obj, ProcessedComponent):
            self.process_object(obj)

        return obj

    def __getitem__(self, item):
        return self.__processing_objects[item]

    def __getattr__(self, item: str):
        if item.startswith("create_"):
            item = item[7:]

        if item.startswith("_component"):
            item = item[:-10]

        if item in self.object_registry:
            # noinspection PyArgumentList
            def _(*args, **kwargs):
                return self.create(self.object_registry[item], *args, **kwargs)

            return _

        raise AttributeError(item)


Scene.object_registry["image"] = ImageComponent
Scene.object_registry["thread"] = ThreadComponent
Scene.object_registry["rectangle"] = RectangleComponent
Scene.object_registry["tween"] = TweenComponent
Scene.object_registry["text"] = TextComponent
Scene.object_registry["container"] = ContainerComponent
Scene.object_registry["empty"] = Component
