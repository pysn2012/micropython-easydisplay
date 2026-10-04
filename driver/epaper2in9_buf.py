# 适用于 2.9 寸黑白墨水屏（GDEH029A1，SSD1608 控制器）的 Framebuffer 驱动
# Github: https://github.com/pysn2012/micropython-easydisplay
# Licence: MIT
# Date: 2026/10
#
# 参考资料:
# https://github.com/mcauser/micropython-waveshare-epaper
# https://github.com/ZinggJM/GxEPD2 (GxEPD2_290)
#
# 原理说明:
#   - 面板原生分辨率为 128*296 竖向，通过 rotate 参数选择画布方向：
#     rotate=0: 128*296 竖向（原始方向）
#     rotate=1: 296*128 横向（顺时针 90°，默认推荐）
#     rotate=2: 128*296 竖向（180°）
#     rotate=3: 296*128 横向（顺时针 270°）
#   - show() 时把画布内容转置到面板缓冲后送屏（全刷方式，与 1.54 寸
#     墨水屏驱动一致）：黑闪一下，约 1.6 秒，同时彻底清除残影
#   - 颜色：1=白色，0=黑色

from micropython import const
from time import sleep_ms, ticks_ms, ticks_diff
import framebuf
import math
from struct import pack
from machine import Pin

# Display resolution（面板原生分辨率）
EPD_WIDTH  = const(128)
EPD_HEIGHT = const(296)

# Display commands
DRIVER_OUTPUT_CONTROL                = const(0x01)
BOOSTER_SOFT_START_CONTROL           = const(0x0C)
DEEP_SLEEP_MODE                      = const(0x10)
DATA_ENTRY_MODE_SETTING              = const(0x11)
MASTER_ACTIVATION                    = const(0x20)
DISPLAY_UPDATE_CONTROL_2             = const(0x22)
WRITE_RAM                            = const(0x24)
WRITE_VCOM_REGISTER                  = const(0x2C)
WRITE_LUT_REGISTER                   = const(0x32)
SET_DUMMY_LINE_PERIOD                = const(0x3A)
SET_GATE_TIME                        = const(0x3B)
SET_RAM_X_ADDRESS_START_END_POSITION = const(0x44)
SET_RAM_Y_ADDRESS_START_END_POSITION = const(0x45)
SET_RAM_X_ADDRESS_COUNTER            = const(0x4E)
SET_RAM_Y_ADDRESS_COUNTER            = const(0x4F)
TERMINATE_FRAME_READ_WRITE           = const(0xFF)  # aka NOOP

BUSY = const(1)  # 1=busy, 0=idle


class EPD(framebuf.FrameBuffer):
    # 30 bytes (look up tables)，original waveshare example
    LUT_FULL_UPDATE = bytearray(b'\x02\x02\x01\x11\x12\x12\x22\x22\x66\x69\x69\x59\x58\x99\x99\x88\x00\x00\x00\x00\xF8\xB4\x13\x51\x35\x51\x51\x19\x01\x00')

    def __init__(self, spi, res: int, dc: int, busy: int, cs: int = None, rotate: int = 1):
        """
        初始化 2.9 寸墨水屏

        Args:
            spi: SPI 实例（建议 baudrate=2000000, polarity=0, phase=0）
            res: RESET 引脚号
            dc: Data / Command 引脚号
            busy: BUSY 引脚号
            cs: 片选引脚号（可不接）
            rotate: 画布方向 0-3，1/3 为 296*128 横向，默认 1
        """
        if rotate not in (0, 1, 2, 3):
            raise ValueError("rotate must be 0-3")
        self.spi = spi
        self.rotate = rotate
        self.res = Pin(res, Pin.OUT, value=0)
        self.dc = Pin(dc, Pin.OUT, value=0)
        self.busy = Pin(busy, Pin.IN)
        self.cs = Pin(cs, Pin.OUT, value=1) if cs is not None else None

        # 画布尺寸随旋转方向变化，1/3 为横向
        if rotate in (1, 3):
            self.width, self.height = EPD_HEIGHT, EPD_WIDTH
        else:
            self.width, self.height = EPD_WIDTH, EPD_HEIGHT
        self.buffer = bytearray((self.width + 7) // 8 * self.height)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_HLSB)
        # 面板缓冲（竖向 128*296），show() 时由画布转置而来
        if rotate != 0:
            self._panel = bytearray(EPD_WIDTH // 8 * EPD_HEIGHT)
            self._panel_fb = framebuf.FrameBuffer(self._panel, EPD_WIDTH, EPD_HEIGHT, framebuf.MONO_HLSB)

        self.init()

    def init(self):
        """初始化面板（上电或深度休眠唤醒后调用）"""
        self.hard_reset()
        self._write(DRIVER_OUTPUT_CONTROL, pack("<HB", EPD_HEIGHT - 1, 0x00))
        self._write(BOOSTER_SOFT_START_CONTROL, b'\xD7\xD6\x9D')
        self._write(WRITE_VCOM_REGISTER, b'\xA8')  # VCOM 7C
        self._write(SET_DUMMY_LINE_PERIOD, b'\x1A')  # 4 dummy lines per gate
        self._write(SET_GATE_TIME, b'\x08')  # 2us per line
        self._write(DATA_ENTRY_MODE_SETTING, b'\x03')  # X increment Y increment
        self.set_lut(self.LUT_FULL_UPDATE)

    def _write(self, command=None, data=None):
        """SPI write to the device: commands and data."""
        if self.cs is not None:
            self.cs(0)
        if command is not None:
            self.dc(0)
            self.spi.write(bytes([command]))
        if data is not None:
            self.dc(1)
            self.spi.write(data)
        if self.cs is not None:
            self.cs(1)

    def write_cmd(self, cmd):
        """写命令"""
        self._write(command=cmd)

    def write_data(self, data):
        """写数据"""
        self._write(data=data)

    def wait_until_idle(self, timeout_ms=10000):
        """等待面板空闲（带超时保护）"""
        start = ticks_ms()
        while self.busy.value() == BUSY:
            if ticks_diff(ticks_ms(), start) > timeout_ms:
                break
            sleep_ms(10)

    def hard_reset(self):
        """硬件复位"""
        self.res(0)
        sleep_ms(100)
        self.res(1)
        sleep_ms(100)

    def set_lut(self, lut):
        """写波形查找表"""
        self._write(WRITE_LUT_REGISTER, lut)

    # put an image in the frame memory
    def set_frame_memory(self, image, x, y, w, h):
        # x point must be the multiple of 8 or the last 3 bits will be ignored
        x = x & 0xF8
        w = w & 0xF8

        if x + w >= EPD_WIDTH:
            x_end = EPD_WIDTH - 1
        else:
            x_end = x + w - 1

        if y + h >= EPD_HEIGHT:
            y_end = EPD_HEIGHT - 1
        else:
            y_end = y + h - 1

        self.set_memory_area(x, y, x_end, y_end)
        self.set_memory_pointer(x, y)
        self._write(WRITE_RAM, image)

    # replace the frame memory with the specified color
    def clear_frame_memory(self, color):
        self.set_memory_area(0, 0, EPD_WIDTH - 1, EPD_HEIGHT - 1)
        self.set_memory_pointer(0, 0)
        self._write(WRITE_RAM)
        # send the color data
        for i in range(0, EPD_WIDTH // 8 * EPD_HEIGHT):
            self.write_data(bytes([color]))

    # draw the current frame memory and switch to the next memory area
    def display_frame(self):
        self._write(DISPLAY_UPDATE_CONTROL_2, b'\xC4')
        self._write(MASTER_ACTIVATION)
        self._write(TERMINATE_FRAME_READ_WRITE)
        self.wait_until_idle()

    # specify the memory area for data R/W
    def set_memory_area(self, x_start, y_start, x_end, y_end):
        self._write(SET_RAM_X_ADDRESS_START_END_POSITION)
        # x point must be the multiple of 8 or the last 3 bits will be ignored
        self.write_data(bytes([(x_start >> 3) & 0xFF]))
        self.write_data(bytes([(x_end >> 3) & 0xFF]))
        self._write(SET_RAM_Y_ADDRESS_START_END_POSITION, pack("<HH", y_start, y_end))

    # specify the start point for data R/W
    def set_memory_pointer(self, x, y):
        self._write(SET_RAM_X_ADDRESS_COUNTER)
        # x point must be the multiple of 8 or the last 3 bits will be ignored
        self.write_data(bytes([(x >> 3) & 0xFF]))
        self._write(SET_RAM_Y_ADDRESS_COUNTER, pack("<H", y))
        self.wait_until_idle()

    def show(self):
        """把画布内容全刷到屏幕：黑闪一下，约 1.6 秒，同时清除残影"""
        if self.rotate == 0:
            self.set_frame_memory(self.buffer, 0, 0, EPD_WIDTH, EPD_HEIGHT)
        else:
            self._to_panel()
            self.set_frame_memory(self._panel, 0, 0, EPD_WIDTH, EPD_HEIGHT)
        self.display_frame()

    def _to_panel(self):
        """把画布按 rotate 方向转置到面板缓冲"""
        pf = self._panel_fb
        pf.fill(0)
        src = self.buffer
        stride = (self.width + 7) >> 3
        if self.rotate == 1:
            for y in range(self.height):
                row = y * stride
                px = EPD_WIDTH - 1 - y
                for x in range(self.width):
                    if (src[row + (x >> 3)] >> (7 - (x & 7))) & 1:
                        pf.pixel(px, x, 1)
        elif self.rotate == 2:
            for y in range(self.height):
                row = y * stride
                py = EPD_HEIGHT - 1 - y
                for x in range(self.width):
                    if (src[row + (x >> 3)] >> (7 - (x & 7))) & 1:
                        pf.pixel(EPD_WIDTH - 1 - x, py, 1)
        else:  # rotate == 3
            for y in range(self.height):
                row = y * stride
                for x in range(self.width):
                    if (src[row + (x >> 3)] >> (7 - (x & 7))) & 1:
                        pf.pixel(y, EPD_HEIGHT - 1 - x, 1)

    def clear(self):
        """清空画布（注意：墨水屏白底请使用 fill(1)）"""
        self.fill(0)

    def circle(self, x, y, radius, c, section=100):
        """
        画圆

        Args:
            c: 颜色
            x: 中心 x
            y: 中心 y
            radius: 半径
            section: 分段
        """
        arr = []
        for m in range(section + 1):
            _x = round(radius * math.cos((2 * math.pi / section) * m - math.pi) + x)
            _y = round(radius * math.sin((2 * math.pi / section) * m - math.pi) + y)
            arr.append([_x, _y])
        for i in range(len(arr) - 1):
            self.line(*arr[i], *arr[i + 1], c)

    def fill_circle(self, x, y, radius, c):
        """
        画填充圆

        Args:
            c: 颜色
            x: 中心 x
            y: 中心 y
            radius: 半径
        """
        rsq = radius * radius
        for _x in range(radius):
            _y = int(math.sqrt(rsq - _x * _x))
            y0 = y - _y
            end_y = y0 + _y * 2
            y0 = max(0, min(y0, self.height))
            length = abs(end_y - y0) + 1
            self.vline(x + _x, y0, length, c)
            self.vline(x - _x, y0, length, c)

    def poweroff(self):
        """进入深度休眠（长时间待机时使用）"""
        self._write(DEEP_SLEEP_MODE, b'\x01')
        self.wait_until_idle()

    def poweron(self):
        """从深度休眠唤醒（唤醒后需调用 init() 重新初始化）"""
        self.hard_reset()
        self.wait_until_idle()
