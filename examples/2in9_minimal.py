# 2.9 寸墨水屏最小使用示例（Minimal example for the 2.9 inch e-paper）
#
# 硬件:Waveshare 2.9 寸黑白墨水屏（GDEH029A1）+ Raspberry Pi Pico（引脚按实际接线修改）
# 需上传到开发板:driver/、lib/、font/text_lite_16px_2312.v3.bmf（放到文件系统根目录）
#
# 运行效果:白底显示中英文,全刷一次（黑闪一下,约 1.6 秒）
import time
from machine import SPI, Pin
import epaper2in9_buf
from easydisplay import EasyDisplay

spi = SPI(1, baudrate=2000000, polarity=0, phase=0, sck=Pin(2), mosi=Pin(3))
dp = epaper2in9_buf.EPD(spi, res=10, dc=8, busy=6, cs=7, rotate=1)  # rotate=1: 296*128 横向
ed = EasyDisplay(dp, "MONO", font="/text_lite_16px_2312.v3.bmf", color=0, bg_color=1)

dp.fill(1)  # 白底（MONO:1=白 0=黑;不要使用 EasyDisplay 的 clear=True,那会清成黑底）
ed.text("你好，世界！", 8, 8)
ed.text("Hello World!", 8, 32)
ed.text("2.9 inch e-paper", 8, 56)
dp.show()   # 全刷送屏;之后可继续绘制再 show(),或调用 dp.poweroff() 进入深度休眠
