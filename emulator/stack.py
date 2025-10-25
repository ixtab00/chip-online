from emulator.register import Register

class Stack:
    def __init__(self, level: int):
        self._contains = []
        self._level = level
        
    def append(self, value: int) -> None:
        #assert len(self._contains) < self._level - 1
        reg = Register(3)
        reg.set(value)
        self._contains.append(reg)

    def pop(self) -> int:
        return self._contains.pop().get()
    
    