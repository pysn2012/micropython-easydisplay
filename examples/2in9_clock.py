# 2.9 寸墨水屏时钟示例（Clock example for the 2.9 inch e-paper）
#
# 硬件:Waveshare 2.9 寸黑白墨水屏（GDEH029A1）+ AHT10 温湿度传感器（可选）+ Raspberry Pi Pico
# 需上传到开发板:driver/、lib/、font/text_lite_16px_2312.v3.bmf（放到文件系统根目录）
# 可选:ahtx0.py（AHT10 温湿度传感器驱动,没有传感器时温湿度显示为 --）
#
# 显示内容:日期 + 中文星期 / 48px 大号时间 / 中文温湿度
# 刷新方式:全刷（每次 show() 黑闪一下,约 1.6 秒,同时清除残影）
import time
from machine import SPI, Pin, SoftI2C
from driver import epaper2in9_buf
from lib.easydisplay import EasyDisplay

# ---------- WiFi / NTP(填入自己的账号密码) ----------
WIFI_SSID = "你的WiFi名称"
WIFI_PASSWORD = "你的WiFi密码"


def do_connect():
    import network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        while not wlan.isconnected():
            pass
    print('network config:', wlan.ifconfig())


def sync_ntp():
    print("开始同步网络时间")
    import ntptime
    try:
        ntptime.NTP_DELTA = 3155644800  # UTC+8 偏移（秒）,不设置则为 UTC
        ntptime.host = 'time1.aliyun.com'
        ntptime.settime()
    except Exception as e:
        print("同步ntp时间错误", repr(e))


# ---------- 温湿度传感器（可选,没有可注释掉） ----------
try:
    from ahtx0 import AHT10
    i2c = SoftI2C(scl=Pin(5), sda=Pin(4))
    sensor = AHT10(i2c)
except Exception:
    sensor = None

# ---------- 显示初始化 ----------
weekday_dict = {
    0: "星期一",
    1: "星期二",
    2: "星期三",
    3: "星期四",
    4: "星期五",
    5: "星期六",
    6: "星期日"
}

spi = SPI(1, baudrate=2000000, polarity=0, phase=0, sck=Pin(2), mosi=Pin(3))
dp = epaper2in9_buf.EPD(spi, res=10, dc=8, busy=6, cs=7, rotate=1)  # 296*128 横向
ed = EasyDisplay(dp, "MONO", font="/text_lite_16px_2312.v3.bmf", color=0, bg_color=1)

do_connect()
sync_ntp()

# ---------- 主循环:每分钟刷新一次 ----------
black, white = 0, 1
while True:
    dp.fill(white)
    t = time.localtime()
    showdate = "%.2d-%.2d-%.2d" % (t[0], t[1], t[2])
    showtime = "%.2d:%.2d" % (t[3], t[4])
    # 第一行:日期 + 中文星期(16px)
    ed.text(showdate, 10, 8)
    ed.text(weekday_dict[t[6]], 238, 8)
    dp.hline(0, 30, 296, black)
    # 中间:时间大字(48px;5 个字符 × 24px = 120px,x=(296-120)//2=88 居中)
    ed.text(showtime, 88, 38, size=48)
    dp.hline(0, 92, 296, black)
    # 第三行:中文温湿度(16px;如需校准可在此对读数加减偏移)
    if sensor:
        ed.text("温度:%0.1f℃" % sensor.temperature, 20, 102)
        ed.text("湿度:%0.1f%%" % sensor.relative_humidity, 170, 102)
    else:
        ed.text("温度:--", 20, 102)
        ed.text("湿度:--", 170, 102)
    dp.show()  # 全刷:黑闪一下,约 1.6 秒
    time.sleep(59)
