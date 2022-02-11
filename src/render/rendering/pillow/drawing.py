import contextlib
import dataclasses
import gc
import math
import time

import typing
from PIL import Image
from PIL.ImageDraw import ImageDraw


if typing.TYPE_CHECKING:
    class ImageDrawCombination(Image.Image, ImageDraw):
        image: Image.Image
        draw: ImageDraw

else:
    @dataclasses.dataclass
    class ImageDrawCombination:
        image: Image.Image
        draw: ImageDraw

        def __getattr__(self, item):
            if hasattr(self.image, item):
                return getattr(self.image, item)

            else:
                getattr(self.draw, item)


def create_image(width, height):
    print(f"creating {width=} {height=} image")
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    drawer = ImageDraw(image)
    return ImageDrawCombination(image, drawer)


class ImagePool:
    def __init__(self):
        self._images: typing.List[typing.Optional[ImageDrawCombination]] = []
        self._locked: typing.List[int] = []
        self._active = 0
        self.lookup_time = 0

    @contextlib.contextmanager
    def request_image(self, width, height, mode="RGBA", *, clear=True, exact_dimensions=True):
        """
        :param width: The width of the pooled image
        :param height: The height of the pooled image
        :param mode: The mode of the image
        :param clear: Set if the image should be cleared before returning
        :param exact_dimensions: Set if the expected image should match the requested dimensions.
        if False the returned image can be larger than the requested dimensions,
        depending on the currently pooled images
        """
        start = time.perf_counter()

        index = 0

        width = math.ceil(width)
        height = math.ceil(height)

        while (index < len(self._images) and
               (index in self._locked or self._images[index] is None or self._images[index].mode != mode or
                (self._images[index].image.size != (width, height) if exact_dimensions else
                 (self._images[index].image.width < width or self._images[index].image.height < height))
                )):

            index += 1

        if index >= len(self._images):
            clear = False  # newly created image

        while index >= len(self._images):
            self.pool_image(width, height)

        im = self._images[index]
        self._locked.append(index)

        if clear:
            im.draw.rectangle((0, 0, im.image.width, im.image.height), (0, 0, 0, 0))

        try:
            if self._active > 200:
                self.cleanup_dead_images()

            self.lookup_time += time.perf_counter() - start

            yield self._images[index]

        finally:
            self._locked.remove(index)

    def close(self):
        for image in self._images:
            if image is not None:
                image.image.close()

    def cleanup_dead_images(self):
        goal = 100

        for idx, image in enumerate(self._images):
            if self._active < goal:
                break

            if idx not in self._locked and image is not None:
                width, height = self._images[idx].image.size
                print(f"cleaning {width=} {height=} image")
                self._images[idx] = None
                self._active -= 1

        gc.collect()

    def remove_dead_indexes(self):
        print(f"removing dead indexes")

        self._images = [image for image in self._images if image is not None]

    def pool_image(self, width, height):
        self._images.append(create_image(width, height))
        self._active += 1

    def __len__(self):
        return len(self._images)
