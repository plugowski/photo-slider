from slider import *
from slider.Config import Config
import slider_socket
import uasyncio as asyncio

# setup WiFi
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid=b"SliderMCU", authmode=network.AUTH_WPA_WPA2_PSK, password=b"GoProSlider")

# build slider object
driver = MotorDriver(Config.pin_step, Config.pin_dir, Config.pin_ms1, Config.pin_ms2, Config.pin_ms3, Config.pin_edge)
motor = Motor(driver)
status = Status(motor, Dolly(), Config.display)
slider = Slider(motor, status)

server = slider_socket.SliderServer(slider)
server.start()

# initialize asyncio loop
loop = asyncio.get_event_loop()

loop.call_soon(status.splash_screen())
loop.call_soon(server.process_all())

loop.run_forever()

server.stop()
