from __future__ import annotations

import queue
import typing
from io import BytesIO
from typing import TYPE_CHECKING

import imageio
import numpy

import threading

if TYPE_CHECKING:
    from .scene import Scene


def run_scene(scene: Scene, io=None, *,
              format_if_animated="gif",
              format_if_static="png",
              callback: typing.Callable[[typing.IO, float], bool] = lambda *_: True,
              kwargs_if_animated: dict = None,
              kwargs_if_static: dict = None):
    first_frame = None
    first_duration = None

    if kwargs_if_static is None:
        kwargs_if_static = {}

    if kwargs_if_animated is None:
        kwargs_if_animated = {}

    if io is None:
        io = BytesIO()

    save_thread = None
    save_queue = queue.Queue()

    try:
        for idx, (image, duration) in enumerate(scene):
            image: numpy.ndarray

            if first_frame is None:
                first_frame = numpy.copy(image, subok=True)
                first_duration = duration

            else:
                if save_thread is None:
                    save_thread = threading.Thread(target=saver_thread, args=(io, save_queue), kwargs={
                        "file_format": format_if_animated,
                        "kwargs": kwargs_if_animated
                    })

                    save_thread.start()

                    save_queue.put((first_frame, first_duration, idx))

                    if not callback(io, scene.scheduler.current_frame_second):
                        raise RuntimeError("Callback stopped execution")

                save_queue.put((numpy.copy(image, subok=True), duration, idx))

                if not callback(io, scene.scheduler.current_frame_second):
                    raise RuntimeError("Callback stopped execution")

        if save_thread is None:
            imageio.imwrite(io, first_frame, format_if_static, **kwargs_if_static)

            if not callback(io, scene.scheduler.current_frame_second):
                raise RuntimeError("Callback stopped execution")

        else:
            print("finished rendering")
            save_queue.put(None)

    finally:
        save_queue.put(None)
        save_thread.join()

    return io, save_thread is not None


def saver_thread(io, q: queue.Queue, *, file_format, kwargs):
    writer = imageio.get_writer(io, file_format, **kwargs)

    while True:
        v = q.get()

        if v is None:
            print("finished saving")
            return io

        else:
            frame, duration, idx = v

            writer._duration = duration
            writer.append_data(frame)
