from slider.Config import *
from slider.Dolly import *
from slider.Motor import *
from ssd1306 import SSD1306_I2C
import ujson
import utime

from uwebsocket import WebSocketConnection


class Status:
    """ Display and send actual slider status (battery, motor position, time left etc.)
    """

    slider_length = None
    dolly_position = None
    socket = None

    def __init__(self, motor: Motor, dolly: Dolly, display: SSD1306_I2C = None):
        self.motor = motor
        self.dolly = dolly
        self.display = display

    def set_socket(self, connection: WebSocketConnection):
        """ Setup socket connection handler
        """
        self.socket = connection

    def send(self, msg: str):
        ...

    def error(self, msg):
        ...

    async def draw_battery(self, level, show_value=True):
        """
        """
        bat_w = 15
        status_bar = 11

        # clean battery area
        self.display.fill_rect(self.display.width - bat_w - 2, 2, bat_w + 2, 7, 0)

        # battery shape
        self.display.rect(self.display.width - bat_w - 2, 0, bat_w, 7, 1)
        self.display.rect(self.display.width - 2, 2, 2, 3, 1)
        # battery status
        bar = level / 100 * status_bar
        self.display.fill_rect(self.display.width - bat_w, 2, int(bar), 3, 1)

        if show_value:
            extra_space = 0 if 10 < level < 100 else 8
            extra_space = extra_space if level > 10 else extra_space * -1
            self.display.fill_rect(self.display.width - bat_w - 27, 0, 24, 7, 0)
            self.display.text(str(level), self.display.width - bat_w - 2 - 17 - extra_space, 0)

        await asyncio.sleep(30)

    async def display_status(self):
        """ Display status information on the screen
        """

        if self.display is None:
            return

        self.display.fill(0)
        self.display.text('Ready!', 0, 0)
        self.draw_battery(self.battery_level()[1])
        self.display.show()

        while True:

            # todo: baterie odpytywac co kilka(nascie) sekund)
            self.draw_battery(self.battery_level()[1])

            if self.motor.start_time or self.motor.end_time:

                total_time = (0 if self.motor.time_ms is None else self.motor.time_ms) / 1000
                time_for_delta = self.motor.end_time if self.motor.end_time else utime.ticks_ms()
                time_elapsed = utime.ticks_diff(time_for_delta, self.motor.start_time)
                time_left = round(total_time - (time_elapsed / 1000), 2)
                distance_elapsed = self.motor.frequency * (time_elapsed / 1000) * (
                        self.motor.step_distance / self.motor.microsteps)

                self.display.fill_rect(0, 9, 128, 64, 0)
                self.display.line(0, 9, 128, 9, 1)
                self.display.text('<<<<<<<' if MotorDriver.LEFT == self.motor.direction else '>>>>>>>', 36, 12)
                self.display.text('TOTAL: ' + str(self.nice_time(int(total_time))), 0, 23)
                self.display.text('LEFT:  ' + str(self.nice_time(int(time_left))), 0, 32)

                self.display.text('DIST:  ' + str(int(distance_elapsed)) + ' mm', 0, 41)

                self.display.line(0, 54, 128, 54, 1)
                self.display.text('R/Hz: ' + str(self.motor.microsteps) + '/' + str(self.motor.frequency), 0, 56)
                self.display.show()

                # if finished reset timers
                if self.motor.end_time:
                    self.motor.start_time = self.motor.end_time = None

            await asyncio.sleep_ms(10)

    @staticmethod
    def battery_level() -> tuple:

        adc = Config.adc

        probe = i = 0
        while i < Config.battery_probes_amount:
            probe = probe + adc.read()
            i = i + 1

        adc_value = int(probe / Config.battery_probes_amount)
        percent = adc_value / 4095

        battery_voltage = percent * Config.battery_max_voltage
        battery_range = Config.battery_max_voltage - Config.battery_min_voltage
        battery_percent = int((battery_voltage - Config.battery_min_voltage) / battery_range * 100)
        battery_percent = 0 if battery_percent < 0 else battery_percent

        return battery_voltage, battery_percent, adc_value, percent

    @staticmethod
    def nice_time(seconds: int) -> str:
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return "%02d:%02d:%02d" % (h, m, s)

    async def send_status(self):

        if self.socket is None:
            return

        # motor.__dict__

        while True:
            status = {
                'errors': None,
                'motor': {
                    'locked': True,
                    'speed': 12,
                    'frequency': 1000,
                    'microsteps': 4,
                    'start_time': 121345,
                    'current_time': 123423,
                    'direction': 'left',
                },
                'slider': {
                    'duration': {
                        'set': 3600,
                        'nice': '01:00:00',
                        'left': 2560
                    },
                    'distance': {
                        'set': 1000,
                        'left': 532
                    }
                },
                'battery': {
                    'voltage': 12.4,
                    'percent': 100
                }
            }
            self.socket.write(ujson.dumps(status))

            await asyncio.sleep_ms(500)
