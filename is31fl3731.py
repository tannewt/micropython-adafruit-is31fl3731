import math


_MODE_REGISTER = const(0x00)
_FRAME_REGISTER = const(0x01)
_AUTOPLAY1_REGISTER = const(0x02)
_AUTOPLAY2_REGISTER = const(0x03)
_BREATH1_REGISTER = const(0x08)
_BREATH2_REGISTER = const(0x09)
_AUDIOSYNC_REGISTER = const(0x06)
_SHUTDOWN_REGISTER = const(0x0a)

_CONFIG_BANK = const(0x0b)
_BANK_ADDRESS = const(0xfd)

_PICTURE_MODE = const(0x00)
_AUTOPLAY_MODE = const(0x08)
_AUDIOPLAY_MODE = const(0x18)


class Matrix:
    def __init__(self, width, height, i2c, address=0x74):
        """
        Driver for the IS31FL3731 charlieplexed LED matrix.

        >>> import is31fl3731
        >>> from machine import I2C, Pin
        >>> i2c = I2C(Pin(5), Pin(4))
        >>> display = is31fl3731.Matrix(16, 9, i2c)
        >>> display.fill(127)
        >>> display.show()
        """
        self.width = width
        self.height = height
        self.i2c = i2c
        self.address = address
        self.init()

    def _bank(self, bank=None):
        if bank is None:
            return self.i2c.readfrom_mem(self.address, _BANK_ADDRESS, 1)[0]
        self.i2c.writeto_mem(self.address, _BANK_ADDRESS, bytearray([bank]))

    def _register(self, bank, register, value=None):
        self._bank(bank)
        if value is None:
            return self.i2c.readfrom_mem(self.address, register, 1)[0]
        self.i2c.writeto_mem(self.address, register, bytearray([value]))

    def init(self):
        """Initialize the display."""
        self._mode(_PICTURE_MODE)
        self.frame(0)
        self.fill(0)
        for frame in range(8):
            for col in range(18):
                self._register(frame, col, 0xff)
        self.audio_sync(False)

    def _mode(self, mode=None):
        return self._register(_CONFIG_BANK, _MODE_REGISTER, mode)

    def sleep(self, value):
        """Enables, disables or gets the sleep mode."""
        return self._register(_CONFIG_BANK, _SHUTDOWN_REGISTER, value)

    def autoplay(self, delay=0, loops=0, frames=0):
        """
        Enables or disables autoplay.

        If ``delay`` is 0, autoplay is disabled. Otherwise the display will
        switch between ``frames`` frames every ``delay`` milliseconds, and
        repeat the cycle ``loops`` times.  If ``loops`` is 0, it will repeat
        indefinitely.
        """
        if delay == 0:
            self._mode(_PICTURE_MODE)
            return
        delay /= 11
        if not 0 <= loops <= 7:
            raise ValueError("Loops out of range")
        if not 0 <= frames <= 7:
            raise ValueError("Frames out of range")
        if not 1 <= delay <= 64:
            raise ValueError("Delay out of range")
        self._register(_CONFIG_BANK, _AUTOPLAY1_REGISTER, loops << 4 | frames)
        self._register(_CONFIG_BANK, _AUTOPLAY2_REGISTER, delay % 64)
        self._mode(_AUTOPLAY_MODE | self._frame)

    def fade(self, fade_in=None, fade_out=None, pause=0):
        """
        Disables or enables and configures fading.

        If called without parameters, disables fading. If ``fade_in`` and/or
        ``fade_out`` are specified, it will take that many milliseconds to
        change between frames, with ``pause`` milliseconds of dark between.
        """
        if fade_in is None and fade_out is None:
            self._register(_CONFIG_BANK, _BREATH2_REGISTER, 0)
        elif fade_in is None:
            fade_in = fade_out
        elif fade_out is None:
            fade_out = fade_in
        fade_in = int(math.log(fade_in / 26, 2))
        fade_out = int(math.log(fade_out / 26, 2))
        pause = int(math.log(pause / 26, 2))
        if not 0 <= fade_in <= 7:
            raise ValueError("Fade in out of range")
        if not 0 <= fade_out <= 7:
            raise ValueError("Fade out out of range")
        if not 0 <= pause <= 7:
            raise ValueError("Pause out of range")
        self._register(_CONFIG_BANK, _BREATH1_REGISTER, fade_out << 4 | fade_in)
        self._register(_CONFIG_BANK, _BREATH2_REGISTER, 1 << 4 | pause)

    def frame(self, frame=None, show=True):
        """
        Change or get active frame.

        If ``frame`` is not specified, returns the active frame, otherwise sets
        it to the value of ``frame``. If ``show`` is ``True``, also shows that
        frame.
        """
        if frame is None:
            return self._frame
        if not 0 <= frame <= 8:
            raise ValueError("Frame out of range")
        self._frame = frame
        if show:
            self._register(_CONFIG_BANK, _FRAME_REGISTER, frame);

    def audio_sync(self, value=None):
        """Enable, disable or get sync of brightness with audio input."""
        return self._register(_CONFIG_BANK, _AUDIOSYNC_REGISTER, value)

    def audio_play(self, value=None):
        """Enable, disable or get frame display according to the audio input."""
        if value is None:
            return self._mode() == _AUDIOPLAY_MODE
        elif value:
            self._mode(_AUDIOPLAY_MODE)
        else:
            self._mode(_PICTURE_MODE)

    def fill(self, color=0, frame=None):
        """Fill the display with specified color."""
        if not 0 <= color <= 255:
            raise ValueError("Color out of range")
        if frame is None:
            frame = self._frame
        self._bank(frame)
        data = bytearray([color] * 24)
        for row in range(6):
            self.i2c.writeto_mem(self.address, 0x24 + row * 24, data)

    def pixel(self, x, y, color=None, frame=None):
        """
        Read or write the specified pixel.

        If ``color`` is not specified, returns the current value of the pixel,
        otherwise sets it to the value of ``color``. If ``frame`` is not
        specified, affects the currently active frame.
        """
        if not 0 <= x <= self.width:
            return
        if not 0 <= y <= self.height:
            return
        if color is None:
            return self._register(self._frame, x + y * self.width)
        if not 0 <= color <= 255:
            raise ValueError("Color out of range")
        if frame is None:
            frame = self._frame
        self._register(frame, x + y * self.width, color)