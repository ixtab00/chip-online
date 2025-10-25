from typing import List
import itertools

class Display:
    def __init__(self, size_x: int, size_y: int):
        self._size_x = size_x
        self._size_y = size_y
        self._contains = [[0 for _ in range(size_x)] for _ in range(size_y)]

    @property
    def contains(self):
        return list(itertools.chain(*self._contains))

    def set(self, x: int, y: int, value: int) -> bool:
        x %= self._size_x
        y %= self._size_y
        old_value = self._contains[y][x]
        new_value = old_value ^ value
        self._contains[y][x] = new_value
        return old_value == 1 and new_value == 0

    def draw(self, bytes: List[int], x: int, y: int) -> bool:
        collision = False
        for row, byte in enumerate(bytes):
            for col in range(8):
                bit = (byte >> (7 - col)) & 1
                if bit:
                    if self.set(x + col, y + row, 1):
                        collision = True
        return collision

    def clear(self):
        self._contains = [[0 for _ in range(self._size_x)] for _ in range(self._size_y)]
