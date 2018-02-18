import network
import uhttpd
import slider_api
import http_api_handler
from modules import uasyncio as asyncio
import machine
from machine import Pin
from slider import MotorDriver, Motor, Dolly, Slider

# setup WiFi
ap = network.WLAN(network.AP_IF)
ap.config(essid=b"SliderMCU", authmode=network.AUTH_WPA_WPA2_PSK, password=b"GoProSlider")

# to make sure that module is working turn on on boar led
status_led = Pin(2, Pin.OUT)
status_led.on()

# overclocking CPU
machine.freq(160000000)


async def wifi_status(led: Pin):
    while True:
        led.on()
        await asyncio.sleep(3)
        led.off()
        await asyncio.sleep_ms(50)


# define motor control pins
pin_edge = Pin(0, Pin.IN, Pin.PULL_UP)  # D3
pin_step = Pin(12, Pin.OUT)  # D6
pin_dir = Pin(14, Pin.OUT)  # D5

# define motor driver step motor size pins
pin_ms1 = Pin(4, Pin.OUT)  # D2
pin_ms2 = Pin(5, Pin.OUT)  # D1
pin_ms3 = Pin(16, Pin.OUT)  # D0

# build slider object
driver = MotorDriver(pin_step, pin_dir, pin_ms1, pin_ms2, pin_ms3)
motor = Motor(driver, pin_edge)
slider = Slider(Dolly(), motor)


# initialize asyncio loop
loop = asyncio.get_event_loop()
loop.create_task(wifi_status(status_led))

# define api endpoints
slider_api = http_api_handler.Handler([
    (['status'], slider_api.Status(slider)),
    (['move'], slider_api.Move(slider)),
    (['stop'], slider_api.Stop(slider))
])

# attach api to server (server trigger run_forever loop)
server = uhttpd.Server([('/api', slider_api)])
server.run()
