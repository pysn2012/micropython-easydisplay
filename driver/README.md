## 屏幕驱动（Chinese）

### 说明
- 文件名含有 `buf` 的驱动是使用 `Framebuffer` 的帧缓冲区驱动，具有较高的效率和丰富的功能，
在开发板内存充足的情况下请尽量选择该驱动


- 文件名含有 `spi` 的驱动是使用 `SPI` 对屏幕进行直接驱动，配合 `micropython-easydisplay` 使用时效率略低，
但是对内存不足以使用 `Framebuffer` 的开发板非常友好


- 部分驱动可能存在一些错误，如果您遇到了错误并修复了 `BUG`，别忘记提交 `Pull Request` 来向项目提交您的更改建议。


## Screen Drivers

### Description
- Drivers with filenames containing `buf` are `Framebuffer` drivers, which have higher efficiency and richer features. Please choose these drivers when there is sufficient memory available on the development board.


- Drivers with filenames containing `spi` are SPI drivers used for direct driving of the screen. When used with `micropython-easydisplay`, they have slightly lower efficiency but are very friendly for development boards with insufficient memory to use `Framebuffer`.


- Some drivers may have some errors. If you encounter an error and fix a bug, don't forget to submit a pull request to contribute your suggested changes to the project.

## 2.9 寸墨水屏驱动（Chinese）

### 说明
- `epaper2in9_buf.py` 适用于 Waveshare `2.9` 寸串行黑白墨水屏（`GDEH029A1`，`SSD1608` 控制器，分辨率 `128*296`）
- 全刷方式（与 `1.54` 寸墨水屏驱动一致）：每次 `show()` 黑闪一下（约 `1.6` 秒），同时彻底清除残影
- `rotate` 参数支持 `0-3` 四个方向：`0`=128\*296 竖向，`1`=296\*128 横向（默认），`2`=竖向 180°，`3`=横向 270°
- `poweroff()` 为深度休眠（长时间待机时使用），唤醒需 `poweron()` 后再调用 `init()`
- 完整示例见 `examples/2in9_minimal.py`（最小示例）与 `examples/2in9_clock.py`（时钟示例）

### 使用示例
```python
from machine import SPI, Pin
from driver import epaper2in9_buf
from lib.easydisplay import EasyDisplay

spi = SPI(1, baudrate=2000000, polarity=0, phase=0, sck=Pin(2), mosi=Pin(3))
dp = epaper2in9_buf.EPD(spi, res=10, dc=8, busy=6, cs=7, rotate=1)  # 296*128 横向
ed = EasyDisplay(dp, "MONO", font="/text_lite_16px_2312.v3.bmf", color=0, bg_color=1)

dp.fill(1)  # 墨水屏设置白底（MONO：1=白，0=黑）
ed.text("你好，世界！Hello World!", 8, 8)
dp.show()
```

### 注意
- 墨水屏白底黑字请使用 `color=0, bg_color=1`，并先 `dp.fill(1)`；不要使用 `EasyDisplay` 的
  `clear=True`（其清屏为 `fill(0)`，会把墨水屏清成全黑）
- `font` 字体文件需上传到开发板，可使用仓库 `font/` 目录下的 `bmf` 字体，也可通过
  `MicroPython-uFont-Tools` 自行生成
- 需要固件内置 `framebuf` 模块（标准固件均有，`1.19+` 测试通过）；`ellipse`/`poly` 需要更高版本固件
- 暂仅提供 `.py` 源码版本

### Notes (English)
- `epaper2in9_buf.py` targets the Waveshare `2.9` inch SPI black/white e-paper
  (`GDEH029A1`, `SSD1608` controller, `128*296`)
- Full refresh mode (consistent with the `1.54` inch e-paper driver): each `show()`
  blinks once (about `1.6s`) and clears ghosting
- Use `rotate` to select the canvas orientation (`0-3`, default `1` = `296*128` landscape)
- For black text on a white background, use `color=0, bg_color=1` and `dp.fill(1)` first;
  do not use `clear=True` of `EasyDisplay`
