import network
import uhttpd
import slider_api
import http_api_handler
import uasyncio as asyncio

# setup WiFi
ap = network.WLAN(network.AP_IF)
ap.config(essid=b"SliderMCU", authmode=network.AUTH_WPA_WPA2_PSK, password=b"GoProSlider")

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
        await asyncio.sleep_ms(50)


async def manual_move(lft_pin: Pin, rgt_pin: Pin, motor: Motor):

    while True:
        await asyncio.sleep_ms(2)
        while not lft_pin.value() or not rgt_pin.value():
            motor.move_mm(motor.LEFT if not lft_pin.value() else motor.RIGHT)
            await asyncio.sleep_ms(10)


# define motor control pins
pin_edge = Pin(15, Pin.IN, Pin.PULL_UP)

pin_rgt_button = Pin(5, Pin.IN, Pin.PULL_UP)
pin_lft_button = Pin(4, Pin.IN, Pin.PULL_UP)

pin_step = Pin(13, Pin.OUT)
pin_dir = Pin(12, Pin.OUT)

# build slider object
dolly = Dolly()
motor = Motor(pin_step, pin_dir, pin_edge, dolly)
slider = Slider(dolly, motor)


# initialize asyncio loop
loop = asyncio.get_event_loop()
loop.create_task(wifi_status(status_led))
loop.create_task(manual_move(pin_lft_button, pin_rgt_button, motor))

# define api endpoints
slider_api = http_api_handler.Handler([
    (['status'], slider_api.Status(slider)),
    (['move'], slider_api.Move(slider)),
    (['stop'], slider_api.Stop(slider))
])

# attach api to server (server trigger run_forever loop)
server = uhttpd.Server([('/api', slider_api)])
server.run()
