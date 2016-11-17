import math
import time


_MODE_REGISTER = const(0x00)
_FRAME_REGISTER = const(0x01)
_AUTOPLAY1_REGISTER = const(0x02)
_AUTOPLAY2_REGISTER = const(0x03)
_BLINK_REGISTER = const(0x05)
_AUDIOSYNC_REGISTER = const(0x06)
_BREATH1_REGISTER = const(0x08)
_BREATH2_REGISTER = const(0x09)
_SHUTDOWN_REGISTER = const(0x0a)
_GAIN_REGISTER = const(0x0b)
_ADC_REGISTER = const(0x0c)

_CONFIG_BANK = const(0x0b)
_BANK_ADDRESS = const(0xfd)

_PICTURE_MODE = const(0x00)
_AUTOPLAY_MODE = const(0x08)
_AUDIOPLAY_MODE = const(0x18)

_ENABLE_OFFSET = const(0x00)
_BLINK_OFFSET = const(0x12)
_COLOR_OFFSET = const(0x24)

class Matrix:
    width = 16
    height = 9

    def __init__(self, i2c, address=0x74):
        self.i2c = i2c
        self.address = address
        self.temp1 = bytearray(1)
        self.temp2 = bytearray(2)
        self.reset()
        self.init()

    def _bank(self, bank=None):
        if bank is None:
            self.temp1[0] = _BANK_ADDRESS
            self.i2c.writeto(self.address, self.temp1, stop=False)
            self.i2c.readfrom_into(self.address, sef.temp1)
            return self.temp1[0]
        self.temp2[0] = _BANK_ADDRESS
        self.temp2[1] = bank
        self.i2c.writeto(self.address, self.temp2)

    def _register(self, bank, register, value=None):
        self._bank(bank)
        if value is None:
            self.temp1[0] = register
            self.i2c.writeto(self.address, self.temp1, stop=False)
            self.i2c.readfrom_into(self.address, sef.temp1)
            return self.temp1[0]
        self.temp2[0] = register
        self.temp2[1] = value
        self.i2c.writeto(self.address, self.temp2)

    def _mode(self, mode=None):
        return self._register(_CONFIG_BANK, _MODE_REGISTER, mode)

    def init(self):
        self._mode(_PICTURE_MODE)
        self.frame(0)
        for frame in range(8):
            self.fill(0, False, frame=frame)
            for col in range(18):
                self._register(frame, _ENABLE_OFFSET + col, 0xff)
        self.audio_sync(False)

    def reset(self):
        self.sleep(True)
        time.sleep(.0001)
        self.sleep(False)

    def sleep(self, value):
        return self._register(_CONFIG_BANK, _SHUTDOWN_REGISTER, not value)


    def blink(self, rate=None):
        if rate is None:
            return (self._register(_CONFIG_BANK, _BLINK_REGISTER) & 0x07) * 270
        elif rate == 0:
            self._register(_CONFIG_BANK, _BLINK_REGISTER, 0x00)
            return
        rate //= 270
        self._register(_CONFIG_BANK, _BLINK_REGISTER, rate & 0x07 | 0x08)

    def fill(self, color=None, blink=None, frame=None):
        if frame is None:
            frame = self._frame
        self._bank(frame)
        if color is not None:
            if not 0 <= color <= 255:
                raise ValueError("Color out of range")
            data = bytearray([color] * 24)
            for row in range(6):
                self.i2c.writeto_mem(self.address,
                                     _COLOR_OFFSET + row * 24, data)
        if blink is not None:
            data = bool(blink) * 0xff
            for col in range(18):
                self._register(frame, _BLINK_OFFSET + col, data)

    def _pixel_addr(self, x, y):
        return x + y * 16

    def pixel(self, x, y, color=None, blink=None, frame=None):
        if not 0 <= x <= self.width:
            return
        if not 0 <= y <= self.height:
            return
        pixel = self._pixel_addr(x, y)
        if color is None and blink is None:
            return self._register(self._frame, pixel)
        if frame is None:
            frame = self._frame
        if color is not None:
            if not 0 <= color <= 255:
                raise ValueError("Color out of range")
            self._register(frame, _COLOR_OFFSET + pixel, color)
        if blink is not None:
            addr, bit = divmod(pixel, 8)
            bits = self._register(frame, _BLINK_OFFSET + addr)
            if blink:
                bits |= 1 << bit
            else:
                bits &= ~(1 << bit)
            self._register(frame, _BLINK_OFFSET + addr, bits)


class CharlieWing(Matrix):
    width = 15
    height = 7

    def _pixel_addr(self, x, y):
        if x > 7:
            x = 15 - x
            y += 8
        else:
            y = 7 - y
        return x * 16 + y
