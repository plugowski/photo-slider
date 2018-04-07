from uwebsocket import WebSocketServer, WebSocketClient, ClientClosedError
import ujson
import ssd1306
import uasyncio as asyncio
from machine import I2C, Pin
from slider import Motor, MotorDriver

i2c = I2C(scl=Pin(23), sda=Pin(22))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)
oled.contrast(1)


class SliderClient(WebSocketClient):

    def __init__(self, conn, driver: MotorDriver):
        super().__init__(conn)
        self.motor = driver

    def process(self):
        try:
            msg = self.connection.read()
            if not msg:
                return

            msg = msg.decode("utf-8")
            print(msg)

            try:
                self.connection.write("cmd: " + msg)
                command = ujson.loads(msg)
                print(command)
                loop = asyncio.get_event_loop()

                if command['action'] == 'left':
                    self.motor.set_direction(0)
                    self.motor.start(500)
                    # loop.call_soon(self.motor.start(500))
                elif command['action'] == 'right':
                    self.motor.set_direction(1)
                    self.motor.start(500)
                    # loop.call_soon(self.motor.start(500))
                elif command['action'] == 'resolution':
                    print('val: ' + command['value'])
                    self.motor.set_resolution(int(command['value']))
                elif command['action'] == 'stop':
                    self.motor.stop()

                self.connection.write("cmd: " + msg)
                oled.fill(0)
                oled.text(command['action'], 0, 0)
                oled.show()

            except ValueError:
                self.connection.write('Wrong command!')

        except ClientClosedError:
            self.connection.close()


class SliderServer(WebSocketServer):
    def __init__(self, motor: MotorDriver):
        self.motor = motor
        super().__init__("www/index.html", 2)

    def _make_client(self, conn):
        return SliderClient(conn, self.motor)
