import typing

from PIL import Image

from ..drawer import ImageDrawCombination
from ..component import DrawableComponent, get_box_from_transform
from ..transform import Transform


class ImageComponent(DrawableComponent):
    def __init__(self, scene, image):
        super().__init__(scene)

        self._image: Image.Image = image
        self.image_resample = Image.BICUBIC

        self.loop = -1
        self.required_loop = 1
        self.start_second = scene.current_second

    def _draw(self, target: ImageDrawCombination, transform: Transform):
        if transform.scale == (1, 1) and transform.angle == 0 and False:
            # just a simple paste
            target.image.paste(self._image, (int(transform.position[0] - transform.anchor[0]),
                                             int(transform.position[1] - transform.anchor[1])))
        else:
            # use internal methods to prevent creating more non-pooled images

            self._image.load()

            if self._image.mode != "RGBA":
                with self.scene.image_pool.request_image(self._image.width, self._image.height) as image:
                    image.image.paste(self._image)

                    target.image.im.transform2((0, 0, target.image.width, target.image.height),
                                               image.image.im, Image.AFFINE, tuple(transform), self.image_resample, 0)

            else:
                target.image.im.transform2((0, 0, target.image.width, target.image.height),
                                           self._image.im, Image.AFFINE, tuple(transform), self.image_resample, 0)

    @property
    def image(self):
        return self._image

    @image.setter
    def image(self, value):
        self._image = value
        self.cache = None

    @property
    def width(self):
        return self._image.width

    @property
    def height(self):
        return self._image.height

    @property
    def size(self):
        return self._image.size

    @property
    def animated(self):
        # only certain formats having is_animated is a bit of a bad decision but alright
        return getattr(self.image, "is_animated", False)

    @property
    def duration(self):
        if self.animated:
            return sum(self.get_durations())

    def get_durations(self):
        cache = self.cache

        if cache is None:
            # get durations of all frames

            cache = []
            self._image.seek(0)

            while True:
                try:
                    cache.append(self._image.info['duration'] / 1000)
                    self._image.seek(self._image.tell() + 1)
                except EOFError:
                    break

            self.cache = cache

        return cache

    def get_active_box(self):
        return get_box_from_transform(self.transform, (
            (0, 0),
            (0, self.height),
            (self.width, self.height),
            (self.width, 0)
        ))

    def cleanup(self):
        self._image.close()

    def reset(self):
        self.start_second = self.scene.current_second

    def get_next_update(self, t) -> typing.Optional[typing.Tuple[typing.Optional[float], typing.Callable, bool]]:
        if self.animated and self.loop != 0:
            durations = self.get_durations()
            anim_second = t - self.start_second

            if anim_second < 0:
                return self.start_second, lambda _: self._image.seek(0), self.required_loop in (-1, 0)

            current_frame = 0
            current_loop = 1
            current_duration = 0

            while current_duration <= anim_second:
                if current_frame >= len(durations):
                    current_frame = 0
                    current_loop += 1

                    if current_loop > self.loop != -1:
                        return

                current_duration += durations[current_frame]
                current_frame += 1

            return (current_duration + self.start_second, lambda _: self._image.seek(current_frame - 1),
                    current_loop <= self.required_loop or self.required_loop == -1)
