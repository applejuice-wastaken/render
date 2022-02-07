import copy
import math
import typing

import numpy as np


def _solve(pos, matrix) -> typing.Tuple[float, float]:
    matrix = matrix * (*pos, 1)
    matrix = matrix.sum(1)
    return tuple(matrix[:2])


def _values_from_matrix(matrix):
    yield from matrix[0]
    yield from matrix[1]


def transform_in_transform(t1, t2):
    t1.angle *= -1
    rotated_position = t1.angle_point(t2.position[0], t2.position[1])
    t1.angle *= -1
    rotated_transform = copy.copy(t2)
    rotated_transform.position = (rotated_position[0] * t1.scale[0],
                                  rotated_position[1] * t1.scale[1])

    # rotated_transform += Transform(position=(t1.anchor[0] * t1.scale[0], t1.anchor[1] * t1.scale[1]))

    rotated_transform += t1
    rotated_transform.anchor = t2.anchor

    t1.angle *= -1
    rotated_transform -= Transform(position=t1.angle_point(t1.anchor[0] * t1.scale[0], t1.anchor[1] * t1.scale[1]))
    t1.angle *= -1

    return rotated_transform


class Transform:
    def __init__(self, *, scale=(1, 1), position=(0, 0), angle=0, anchor=(0, 0)):
        self._anchor = anchor
        self._angle = angle
        self._position = position
        self._scale = scale

        self._rm = None
        self._m = None

    @property
    def anchor(self):
        return self._anchor

    @anchor.setter
    def anchor(self, value):
        self._anchor = value
        self._rm = None
        self._m = None

    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, value):
        self._angle = value % (math.pi * 2)
        self._rm = None
        self._m = None

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, value):
        self._position = value
        self._rm = None
        self._m = None

    @property
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, value):
        self._scale = value
        self._rm = None
        self._m = None

    def __add__(self, other):
        if isinstance(other, Transform):
            return Transform(scale=(
                self.scale[0] * other.scale[0],
                self.scale[1] * other.scale[1]
            ), position=(
                self.position[0] + other.position[0],
                self.position[1] + other.position[1]
            ), angle=self.angle + other.angle,
                anchor=(
                    self.anchor[0] + other.anchor[0],
                    self.anchor[1] + other.anchor[1]
                )
            )

        else:
            raise TypeError(f'can only add {Transform.__name__} '
                            f'(not "{type(other).__name__}") to {type(self).__name__}')

    def __sub__(self, other):
        if isinstance(other, Transform):
            return Transform(scale=(
                self.scale[0] / other.scale[0],
                self.scale[1] / other.scale[1]
            ), position=(
                self.position[0] - other.position[0],
                self.position[1] - other.position[1]
            ), angle=self.angle - other.angle,
                anchor=(
                    self.anchor[0] - other.anchor[0],
                    self.anchor[1] - other.anchor[1]
                )
            )

        else:
            raise TypeError(f'can only subtract {Transform.__name__} '
                            f'(not "{type(other).__name__}") to {type(self).__name__}')

    def __neg__(self):
        return Transform(scale=(
            1 / self.scale[0],
            1 / self.scale[1]
        ), position=(
            -self.position[0],
            -self.position[1]
        ), angle=-self.angle,
            anchor=(
                -self.anchor[0],
                -self.anchor[1]
            )
        )

    def __repr__(self):
        anchor, angle, position, scale = self.anchor, self.angle, self.position, self.scale
        return f"{type(self).__name__}({scale=}, {position=}, {angle=}, {anchor=})"

    def matrix(self):
        if self._m is None:
            translation = np.array([
                [1, 0, self.position[0] - self.anchor[0]],
                [0, 1, self.position[1] - self.anchor[1]],
                [0, 0, 1]
            ])

            anchor_matrix = np.array([
                [1, 0, self.anchor[0]],
                [0, 1, self.anchor[1]],
                [0, 0, 1]
            ])

            anchor_i = np.array([
                [1, 0, -self.anchor[0]],
                [0, 1, -self.anchor[1]],
                [0, 0, 1]
            ])

            rotation = np.array([
                [math.cos(self.angle), math.sin(self.angle), 0],
                [-math.sin(self.angle), math.cos(self.angle), 0],
                [0, 0, 1]
            ])

            scale = np.array([
                [self.scale[0], 0, 0],
                [0, self.scale[1], 0],
                [0, 0, 1]
            ])

            self._m = np.dot(translation, np.dot(anchor_matrix, np.dot(scale, np.dot(rotation, anchor_i))))

        return self._m

    def reverse_matrix(self):
        if self._rm is None:
            translation = np.array([
                [1, 0, -self.position[0] + self.anchor[0]],
                [0, 1, -self.position[1] + self.anchor[1]],
                [0, 0, 1]
            ])

            anchor_matrix = np.array([
                [1, 0, -self.anchor[0]],
                [0, 1, -self.anchor[1]],
                [0, 0, 1]
            ])

            anchor_i = np.array([
                [1, 0, self.anchor[0]],
                [0, 1, self.anchor[1]],
                [0, 0, 1]
            ])

            rotation = np.array([
                [math.cos(-self.angle), math.sin(-self.angle), 0],
                [-math.sin(-self.angle), math.cos(-self.angle), 0],
                [0, 0, 1]
            ])

            scale = np.array([
                [1 / self.scale[0], 0, 0],
                [0, 1 / self.scale[1], 0],
                [0, 0, 1]
            ])

            self._rm = np.dot(anchor_i, np.dot(rotation, np.dot(scale, np.dot(anchor_matrix, translation))))

        return self._rm

    def solve_reverse(self, pos):
        return _solve(pos, self.reverse_matrix())

    def solve(self, pos):
        return _solve(pos, self.matrix())

    @classmethod
    def default(cls):
        return cls()

    def __iter__(self):
        yield from self.reverse_matrix_values()

    def reverse_matrix_values(self):
        yield from _values_from_matrix(self.reverse_matrix())

    def matrix_values(self):
        yield from _values_from_matrix(self.matrix())

    def angle_point(self, x, y):
        qx = math.cos(self.angle) * x - math.sin(self.angle) * y
        qy = math.sin(self.angle) * x + math.cos(self.angle) * y
        return qx, qy
