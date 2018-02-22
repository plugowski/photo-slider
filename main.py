from machine import Pin, freq
from oled import *
from slider import *
from uhttpd import Server, api_handler
import network
import slider_api
import uasyncio as asyncio


# define status led (on-board led)
status_led = Pin(2, Pin.OUT)

# define motor control pins
pin_edge = Pin(0, Pin.IN, Pin.PULL_UP)  # D3
pin_step = Pin(12, Pin.OUT)  # D6
pin_dir = Pin(14, Pin.OUT)  # D5

# define motor driver step motor size pins
pin_ms1 = Pin(4, Pin.OUT)  # D2
pin_ms2 = Pin(5, Pin.OUT)  # D1
pin_ms3 = Pin(16, Pin.OUT)  # D0

# overclocking CPU
freq(160000000)

# setup WiFi
ap = network.WLAN(network.AP_IF)
ap.config(essid=b"SliderMCU", authmode=network.AUTH_WPA_WPA2_PSK, password=b"GoProSlider")

i2c = I2C(scl=pin_display_scl, sda=pin_display_sda)
display = ssd1306.SSD1306_I2C(64, 48, i2c)

display.text('elo', 0, 0)
display.show()

async def wifi_status(led: Pin):
    while True:
        led.on()
        await asyncio.sleep(3)
        led.off()
        await asyncio.sleep_ms(50)

# build slider object
driver = MotorDriver(pin_step, pin_dir, pin_ms1, pin_ms2, pin_ms3)
motor = Motor(driver, pin_edge)
slider = Slider(Dolly(), motor)

# initialize asyncio loop
loop = asyncio.get_event_loop()
loop.create_task(wifi_status(status_led))


# define api endpoints
slider_api_endpoints = api_handler.Handler([
    (['status'], slider_api.Status(slider)),
    (['move'], slider_api.Move(slider)),
    (['stop'], slider_api.Stop(slider))
])

# attach api to server (server trigger run_forever loop)
server = Server([('/api', slider_api_endpoints)])

server.run()