from emulator.display import Display
from emulator.register import Register
from emulator.stack import Stack
from emulator.memory import RAM
from random import randint
from typing import List, Dict
import asyncio

SCREEN_SIZE_X = 64
SCREEN_SIZE_Y = 32
FONT_START = 0x50
PROGRAM_START = 0x200
MEM_SIZE = 4096
STACK_SIZE = 16
GENERAL_REGISTERS_AMOUNT = 16
COMMANS_PER_CYCLE = 10

class Emulator:
    def __init__(self):
        self._opcodes_per_cycle: int = 10
        self._display: Display = Display(
            SCREEN_SIZE_X, SCREEN_SIZE_Y
        )
        self._ram: RAM = RAM(MEM_SIZE)
        self._stack: Stack = Stack(STACK_SIZE)
        self._general_registers: List[Register] = [
            Register(1) for _ in range(GENERAL_REGISTERS_AMOUNT)
        ]

        self._keys: List[int] = [0] * 16

        self._index_register: Register = Register(3)

        self._pc_register: Register = Register(2)

        self._timer_register: Register = Register(1)

        self._sound_timer_register: Register = Register(1)

    def fetch(self) -> int:
        location: int = self._pc_register.get()

        instruction_1: int = self._ram.get(location)
        instruction_2: int = self._ram.get(location + 1)

        self._pc_register.set((location + 2) & 0xFFF)

        
        return (instruction_1 << 8) + instruction_2

    def execute(self, opcode: int):
        type = (opcode & 0xF000) >> 12

        X = (0x0F00 & opcode) >> 8
        Y = (0x00F0 & opcode) >> 4

        n = opcode & 0x000F
        nn = opcode & 0x00FF
        nnn = opcode & 0x0FFF

        if type == 0xd:
            self._general_registers[0xF].set(0x0)
            addr = self._index_register.get()
            sprite = [self._ram.get(index) for index in range(addr, addr+n)]

            collision = self._display.draw(sprite, self._general_registers[X].get(), self._general_registers[Y].get())
            if collision:
                self._general_registers[0xF].set(0x1)
        
        elif opcode == 0x00E0:
            if Y == 0xE:
                self._display.clear()

        elif opcode == 0x00EE:
            self._pc_register.set(self._stack.pop())
        
        elif type == 0x2:
            self._stack.append(self._pc_register.get())
            self._pc_register.set(nnn)

        elif type == 0x3:
            if self._general_registers[X].get() == nn:
                location = self._pc_register.get()
                self._pc_register.set((location + 2) & 0xFFF)

        elif type == 0x4:
            if self._general_registers[X].get() != nn:
                location = self._pc_register.get()
                self._pc_register.set((location + 2) & 0xFFF)
        
        elif type == 0x5:
            if self._general_registers[X].get() == self._general_registers[Y].get():
                location = self._pc_register.get()
                self._pc_register.set((location + 2) & 0xFFF)
        
        elif type == 0x6:
            self._general_registers[X].set(nn)

        elif type == 0x7:
            initial_value = self._general_registers[X].get()
            self._general_registers[X].set((initial_value + nn) & 0xFF)

        elif type == 0x8:
            if n == 0x0:
                self._general_registers[X].set(self._general_registers[Y].get())
            
            elif n == 0x1:
                self._general_registers[X].set(
                    self._general_registers[X].get() | self._general_registers[Y].get()
                )
            
            elif n == 0x2:
                self._general_registers[X].set(
                    self._general_registers[X].get() & self._general_registers[Y].get()
                )

            elif n == 0x3:
                self._general_registers[X].set(
                    self._general_registers[X].get() ^ self._general_registers[Y].get()
                )

            elif n == 0x4:
                result = self._general_registers[X].get() + self._general_registers[Y].get()
                if result > 0xFF:
                    self._general_registers[0xF].set(0x1)
                    result = result & 0xFF
                self._general_registers[X].set(result)

            elif n == 0x5:
                x_val = self._general_registers[X].get()
                y_val = self._general_registers[Y].get()
                self._general_registers[0xF].set(1 if x_val > y_val else 0)
                self._general_registers[X].set((x_val - y_val) & 0xFF)

            elif n == 0x6:
                val = self._general_registers[X].get()
                self._general_registers[0xF].set(val & 0x1)
                self._general_registers[X].set(val >> 1)

            elif n == 0x7:
                x_val = self._general_registers[X].get()
                y_val = self._general_registers[Y].get()
                self._general_registers[0xF].set(1 if y_val > x_val else 0)
                self._general_registers[X].set((y_val - x_val) & 0xFF)
            
            elif n == 0xE:
                val = self._general_registers[X].get()
                self._general_registers[0xF].set((val >> 7) & 0x1)
                self._general_registers[X].set((val << 1) & 0xFF)

        elif type == 0xA:
            self._index_register.set(nnn)

        elif type == 0x1:
            self._pc_register.set(nnn)

        elif type == 0x9:
            if self._general_registers[X].get() != self._general_registers[Y].get():
                location = self._pc_register.get()
                self._pc_register.set((location + 2) & 0xFFF)
        
        elif type == 0xB:
            self._pc_register.set(nnn + self._general_registers[0].get())

        elif type == 0xC:
            self._general_registers[X].set(randint(0, 255) & nn)

        
        elif type == 0xE:
            if nn == 0x9E:
                if self._keys[self._general_registers[X].get()]:
                    self._pc_register.set((self._pc_register.get() + 2) & 0xFFF)

            elif nn == 0xA1:
                if not self._keys[self._general_registers[X].get()]:
                    self._pc_register.set((self._pc_register.get() + 2) & 0xFFF)


        elif type == 0xF:
            if nn == 0x07:
                self._general_registers[X].set(self._timer_register.get())
            
            elif nn == 0x0A:  
                pressed = None
                for i, state in enumerate(self._keys):
                    if state:
                        pressed = i
                        break
                if pressed is not None:
                    self._general_registers[X].set(pressed)
                else:
                    self._pc_register.set(self._pc_register.get() - 2)
                    
            elif nn == 0x15:
                self._timer_register.set(self._general_registers[X].get())

            elif nn == 0x18:
                self._sound_timer_register.set(self._general_registers[X].get())

            elif nn == 0x1E:
                v_I = self._index_register.get()
                self._index_register.set((v_I + self._general_registers[X].get()) & 0xFFFF)
            
            elif nn == 0x29:
                digit = self._general_registers[X].get() & 0xF
                self._index_register.set(FONT_START + digit * 5)

            elif nn == 0x33:
                val = self._general_registers[X].get()
                self._ram.set(self._index_register.get(), val // 100)
                self._ram.set(self._index_register.get() + 1, (val // 10) % 10)
                self._ram.set(self._index_register.get() + 2, val % 10)

            elif nn == 0x55:
                for i in range(X + 1):
                    self._ram.set(self._index_register.get() + i, self._general_registers[i].get())

            elif nn == 0x65:
                for i in range(X + 1):
                    self._general_registers[i].set(self._ram.get(self._index_register.get() + i))

        
        else:
            print("Incorrect opcode!")

    def get_screen_state(self) -> str:
        return self._display.contains

    def read_rom(self, rom_path: str):
        self._pc_register.set(0x200)

        with open(rom_path, "rb") as file:
            i = 0
            while True:
                byte = file.read(1)
                if not byte:
                    break
                self._ram.set(i + PROGRAM_START, int.from_bytes(byte))
                i+=1
    
    def cycle(self, n_commands: int) -> None:
        for _ in range(n_commands):
            command: int = self.fetch()
            self.execute(command)
            self.tick_timers()

    def set_input(self, user_input: dict) -> None:
        key = user_input.get("key")
        pressed = user_input.get("pressed", False)
        if key is not None:
            self._keys[key] = 1 if pressed else 0

    def tick_timers(self):
        if self._timer_register.get() > 0:
            self._timer_register.set(self._timer_register.get() - 1)
        if self._sound_timer_register.get() > 0:
            self._sound_timer_register.set(self._sound_timer_register.get() - 1)

class AsyncEmulator(Emulator):
    def __init__(self):
        super().__init__()
        self._input_queue = asyncio.Queue()

    async def put_input(self, input_data: Dict):
        await self._input_queue.put(input_data)

    async def cycle(self, n_commands: int):
        while not self._input_queue.empty():
            event = await self._input_queue.get()
            self._keys[event["key"]] = 1 if event["pressed"] else 0
        super().cycle(n_commands)