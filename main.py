import network
import uhttpd
import slider_api
import http_api_handler
import uasyncio as asyncio

# setup WiFi
ap = network.WLAN(network.AP_IF)
ap.config(essid=b"Slider", authmode=network.AUTH_WPA_WPA2_PSK, password=b"GoProSlider")

from machine import Pin
from slider import Motor, Dolly, Slider

# to make sure that module is working turn on on boar led
status_led = Pin(2, Pin.OUT)
status_led.on()


async def wifi_status(led: Pin):
    while True:
        led.on()
        await asyncio.sleep(3)
        led.off()
        await asyncio.sleep_ms(100)

# define motor control pins
pin_edge = Pin(15, Pin.IN, Pin.PULL_UP)
pin_step = Pin(13, Pin.OUT)
pin_dir = Pin(12, Pin.OUT)

# build slider object
dolly = Dolly()
motor = Motor(pin_step, pin_dir, pin_edge, dolly)
slider = Slider(dolly, motor)

# initialize asyncio loop
loop = asyncio.get_event_loop()
loop.create_task(wifi_status(status_led))

# define api endpoints
slider_api = http_api_handler.Handler([
    (['move'], slider_api.Move(slider))
])

# attach api to server (server trigger run_forever loop)
server = uhttpd.Server([('/api', slider_api)])
server.run()
