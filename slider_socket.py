from slider import Slider
import ujson
from uwebsocket import *
import uasyncio as asyncio


class SliderClient(WebSocketClient):

    def __init__(self, conn, slider: Slider):
        self.slider = slider
        super().__init__(conn)

    def process(self):
        try:

            msg = self.connection.read().decode("utf-8")
            command = ujson.loads(msg)

            self.slider.status.set_socket(self.connection)

            if command['action'] == 'move':
                self.slider.move_dolly(
                    int(command['distance']),
                    self.slider.motor.driver.LEFT if command['direction'] == 'left' else self.slider.motor.driver.RIGHT,
                    int(command['time'])
                )
            elif command['action'] == 'driver':
                self.slider.motor.driver \
                    .set_resolution(int(command['value'])) \
                    .set_direction(command['direction'])
            elif command['action'] == 'resolution':
                self.slider.motor.driver.set_resolution(int(command['value']))
            elif command['action'] == 'stop':
                self.slider.stop()

            # todo: check if other send_status coro already running
            asyncio.get_event_loop().create_task(self.slider.status.send_status())

        except ValueError:
            self.connection.write('Wrong command!')

        except ClientClosedError:
            self.connection.close()


class SliderServer(WebSocketServer):

    def __init__(self, slider: Slider):
        self.slider = slider
        super().__init__(2)

    def _make_client(self, conn):
        return SliderClient(conn, self.slider)
