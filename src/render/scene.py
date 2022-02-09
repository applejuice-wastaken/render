from __future__ import annotations

import abc
import inspect
import math
import typing
from operator import attrgetter
import time

from .drawer import ImagePool
from .component import Component, BaseLifecycleComponent, DrawableComponent
from .objects.container import ContainerComponent
from .objects.image import ImageComponent
from .objects.primitive import RectangleComponent
from .objects.text import TextComponent
from .objects.thread import ThreadComponent
from .objects.tweener import TweenComponent

from .transform import Transform


class Scene(BaseLifecycleComponent, abc.ABC):
    object_registry: typing.Dict[str, typing.Type[Component]] = {}

    def __init_subclass__(cls, **kwargs):
        cls.cache_keys = {}

    def __init__(self):
        self.current_second = 0
        self.current_frame_second = 0
        self._first_frame = True

        super().__init__(self)

        self.processing_objects: typing.List[Component] = []
        self.processing_objects.append(self)

        self.drawing_objects: typing.List[DrawableComponent] = []

        self.min_frame_duration = 1 / 60
        self.min_duration = 0

        self._width = 0
        self._height = 0

        self.image_pool: typing.Optional[ImagePool] = None

        self.initial_transform = Transform()

        self.render_time = 0
        self.process_time = 0

        self.current_image = None

        self._has_yielded = False

        self.initialize_image_pool()

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @width.setter
    def width(self, value):
        if not self.first_frame:
            raise RuntimeError("Width cannot be set after the first frame")

        self._width = value

    @height.setter
    def height(self, value):
        if not self.first_frame:
            raise RuntimeError("Height cannot be set after the first frame")

        self._height = value

    @property
    def first_frame(self):
        return self._first_frame

    def __iter__(self):
        self._update(self.current_second)

        try:
            while True:
                start = time.perf_counter()
                next_second = math.inf
                update_funcs = []
                update_required = False

                for obj in self.processing_objects:
                    candidate_update_collection = obj.get_next_update(self.current_second)

                    if candidate_update_collection is not None:
                        candidate_second, candidate_func, is_required = candidate_update_collection

                        if self.first_frame:
                            should_add = 0 <= candidate_second <= next_second

                        else:
                            should_add = self.current_second < candidate_second <= next_second

                        if should_add:
                            if candidate_second < next_second:
                                update_funcs.clear()
                                next_second = candidate_second

                            update_funcs.append(candidate_func)

                            update_required = update_required or is_required

                self.process_time += time.perf_counter() - start

                if update_funcs and (update_required or self.min_duration > self.current_second):
                    self.current_second = next_second

                    for func in update_funcs:
                        func(next_second)

                    if self._first_frame or self.min_frame_duration < self.current_second - self.current_frame_second:
                        self.current_image = self.render_frame()
                        old_frame_second = self.current_frame_second
                        self.current_frame_second = self.current_second

                        if not self._first_frame:
                            yield self.current_image.image, self.current_second - old_frame_second
                            self._has_yielded = True

                        self._first_frame = False

                else:
                    if self.min_duration > self.current_second:
                        yield self.current_image.image, self.min_duration - self.current_second
                        self._has_yielded = True

                    if not self._has_yielded:
                        yield self.current_image.image, 0

                    break

        finally:
            self.cleanup_objects()

    def initialize_image_pool(self):
        self.image_pool = ImagePool()

    def draw_object(self, obj):
        self.drawing_objects.append(obj)

    def remove_draw_object(self, obj):
        self.drawing_objects.remove(obj)

    def process_object(self, obj):
        self.processing_objects.append(obj)

    def remove_process_object(self, obj):
        self.processing_objects.remove(obj)

    def render_frame(self):
        start = time.perf_counter()
        with self.image_pool.request_image(self.width, self.height) as comb:
            s = sorted(self.drawing_objects, key=attrgetter("z"))

            for obj in s:
                obj.draw(comb, self.initial_transform)

            self.render_time += time.perf_counter() - start

            return comb

    def cleanup_objects(self):
        for obj in self.processing_objects:
            obj.cleanup()

        if self.image_pool is not None:
            self.image_pool.close()

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

        self.process_object(obj)
        return obj

    def __getitem__(self, item):
        return self.processing_objects[item]

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
