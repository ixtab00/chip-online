from typing import List

class Register:
    def __init__(self, size: int):
        self._size = size #size is number of bytes
        self._contains = 0b0

    def set(self, new_value: int) -> None:
        #assert new_value < self._size * 1024
        self._contains = new_value

    def get(self) -> int:
        return self._contains