from uwebsocket import WebSocketServer, WebSocketClient, ClientClosedError
import ujson
from slider import Slider


class SliderClient(WebSocketClient):

    def __init__(self, conn, slider: Slider):
        super().__init__(conn)
        self.slider = slider

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

                if command['action'] == 'move':
                    self.slider.move_dolly(
                        int(command['distance']),
                        self.slider.motor.motor_driver.LEFT if command['direction'] == 'left' else self.slider.motor.motor_driver.RIGHT,
                        int(command['time'])
                    )
                elif command['action'] == 'driver':
                    self.slider.motor.motor_driver\
                        .set_resolution(int(command['value']))\
                        .set_direction(command['direction'])

                elif command['action'] == 'speed':
                    self.slider.speed(int(command['speed']))
                elif command['action'] == 'resolution':
                    self.slider.motor.motor_driver.set_resolution(int(command['value']))
                elif command['action'] == 'stop':
                    self.slider.motor.stop()

                # todo: zwracac status slidera przez socket
                self.slider.display.fill_rect(0, 56, 128, 8, 0)
                self.slider.display.text(command['action'], 0, 56)
                self.slider.display.show()

            except ValueError:
                print('wrong command!')
                self.connection.write('Wrong command!')

        except ClientClosedError:
            self.connection.close()


class SliderServer(WebSocketServer):
    def __init__(self, slider: Slider):
        self.slider = slider
        super().__init__("www/index.html", 2)

    def _make_client(self, conn):
        return SliderClient(conn, self.slider)
