import copy
from math import pi, ceil
import ssd1306
from machine import Pin, PWM
import uasyncio as asyncio
import time as systime


"""
Motor driver can change steps mode to microsteps, for example half step, quarter step etc...
"""


class MotorDriver:

    """ Direction constants
    """
    RIGHT = 1
    LEFT = 0

    """ List of all allowed resolutions
    """
    resolutions = [1, 2, 4, 8, 16]

    """ Settings for specified resolutions
    """
    resolution_settings = {
        1:  [0, 0, 0],
        2:  [1, 0, 0],
        4:  [0, 1, 0],
        8:  [1, 1, 0],
        16: [1, 1, 1]
    }

    def __init__(self, step: Pin, direction: Pin, m1: Pin, m2: Pin, m3: Pin):

        self.pwm = PWM(step)
        self.pwm.duty(512)
        self.pwm.deinit()

        self.direction = direction
        self.m1 = m1
        self.m2 = m2
        self.m3 = m3

        self.set_resolution(1)

    """ Set direction to right/left
    """
    def set_direction(self, direction: int):

        self.direction.value(direction == self.RIGHT)
        return self

    """ Reverse direction based on current settings
    """
    def set_opposite_direction(self):

        self.direction.value(self.LEFT if self.direction.value() else self.RIGHT)
        return self

    """ Set microsteps for stepper motor
    """
    def set_resolution(self, resolution: int=1):

        config = self.resolution_settings[resolution]
        self.m1.value(config[0])
        self.m2.value(config[1])
        self.m3.value(config[2])
        return self

    """ Just send move signal to motor
    """
    def start(self, frequency: int):

        self.pwm.freq(frequency)
        self.pwm.init()

    """ Stop sending move signal to motor
    """
    def stop(self):

        self.pwm.deinit()


"""
Motor knows:
 # diameter of used pulley
 # resolution (steps by rotation)
 # distance by step

Motor can:
 # move by specified distance (how many steps should jump)
 # move on specified direction
 # todo: change step mode 1/2, 1/4, 1/8 i 1/16 for better precision
"""


class Motor:

    """ Determine if motor should be stopped """
    motor_stop = False
    """ Check if limit switch has been reached """
    limit_switch = False

    microsteps = frequency = direction = time_ms = start_time = end_time = None

    def __init__(self, motor_driver: MotorDriver, edge: Pin, resolution: int=200, pulley: float=10.2):

        self.motor_driver = motor_driver
        self.loop = asyncio.get_event_loop()
        self.locker = Lock()

        self.full_rotate_distance = 2 * pi * (pulley / 2)
        self.step_distance = self.full_rotate_distance / resolution
        self.steps_per_mm = 1 / self.step_distance

        # configure pins
        self.pin_edge = edge
        self.pin_edge.irq(trigger=Pin.IRQ_FALLING, handler=self.stop)
        self.microsteps = 1

    """ Move belt by distance on specified direction in time
    """
    async def move(self, direction: int, distance: int = None, time: int = None, speed: int = None) -> int:

        try:
            print('move')
            # max available speed
            self.direction = direction

            # default values for move without time
            self.microsteps = 1
            self.frequency = 800
            self.time_ms = (distance / self.frequency) * 1000

            # jak liczyć speed?

            if time is not None:

                # calculate frequency and resolution for specified distance and time
                self.time_ms = time * 1000
                print('time_ms: ' + str(self.time_ms))
                steps_to_move = distance * self.steps_per_mm

                resolutions = copy.copy(MotorDriver.resolutions)
                resolutions.reverse()

                for resolution in resolutions:
                    print('real freq: ' + str((steps_to_move / time) * resolution))
                    self.frequency = ceil((steps_to_move / time) * resolution)
                    print('check res: ' + str(resolution) + ' frq: ' + str(self.frequency))

                    if self.frequency <= 1000:
                        self.microsteps = resolution
                        self.time_ms = int(distance / (self.step_distance / resolution) / self.frequency * 1000)
                        print('corrected time: ' + str(self.time_ms))
                        break

            self.motor_driver\
                .set_direction(direction)\
                .set_resolution(self.microsteps)\
                .start(self.frequency)

            self.start_time = systime.ticks_us()

            await asyncio.sleep_ms(self.time_ms)

            self.stop()
            self.end_time = systime.ticks_us()
            self.start_time = None

        except LockedProcessException:
            return False

        return True

    """ Rotate motor as long as limit switch will be reached
    """
    async def moveto_edge(self, direction: int, resolution: int=None, freq:int=None):

        try:

            self.start_time = systime.ticks_us()

            self.motor_driver\
                .set_resolution(1 if resolution is None else resolution)\
                .set_direction(direction)\
                .start(700 if freq is None else freq)

        except LockedProcessException:
            return False

        return True

    async def edge(self):

        while True:

            await asyncio.sleep_ms(5)

            # if motor not working > exit

            if self.pin_edge.value() == 0:

                self.motor_driver\
                    .set_opposite_direction()\
                    .set_resolution(4)\
                    .start(1000)
                await asyncio.sleep_ms(43)
                self.motor_driver.stop()
                break

        return True

    """ Stop motor!
    """
    def stop(self, irq=None):

        print('stop_event')
        self.motor_driver.stop()
        self.end_time = systime.ticks_us()
        self.start_time = None
        return True


"""
Locker to avoid race condition in access to motor
"""


class Lock:

    is_lock = False
    locked_by = None

    def lock(self, process: str=None):
        if self.is_lock and self.locked_by != process:
            raise LockedProcessException()

        self.is_lock = True
        self.locked_by = process

    def unlock(self, process: str=None):
        if self.locked_by == process:
            self.is_lock = False

    def is_locked(self):
        return self.is_lock


class LockedProcessException(Exception):
    pass


"""
Dolly knows:
 # its own position
"""


class Dolly:

    """ Actual dolly position """
    current_position = 0

    """ Change
    """
    def change_position(self, value, direction):
        self.current_position += direction * value

    """ Set current position for dolly
    """
    def set_position(self, position: int):
        self.current_position = position

    """ Get current dolly position
    """
    def get_position(self) -> int:
        return self.current_position


"""
Slider knows:
 # total length
 # dolly position

Slider can:
 # reset dolly position
 # move dolly in two directions in specified time
"""


class Slider:

    """ Total length of slider in steps """
    length = 0

    def __init__(self, motor: Motor, display: ssd1306.SSD1306_I2C = None):
        self.loop = asyncio.get_event_loop()
        self.motor = motor
        self.display = display

        self.loop.create_task(self.display_status())

    """ Reset slider, so move dolly on start position
    """
    async def reset(self):
        self.loop.create_task(self.motor.moveto_edge(MotorDriver.LEFT))

    """ Display status information on the screen
    """
    async def display_status(self):

        if self.display is None:
            return True

        width = 128
        bat_w = 15
        status = 6

        self.display.fill(0)
        self.display.text('Initialized!', 0, 0)
        self.display.rect(width - bat_w - 2, 0, bat_w, 7, 1)
        self.display.rect(width - 2, 2, 2, 3, 1)
        self.display.fill_rect(width - bat_w, 2, status, 3, 1)
        self.display.show()

        while True:
            if self.motor.start_time is not None:

                total_time = (0 if self.motor.time_ms is None else self.motor.time_ms) / 1000
                time_elapsed = systime.ticks_diff(systime.ticks_us(), self.motor.start_time)
                print(time_elapsed)
                # todo: max dla ticks_us to 536870911, licznik przekreca sie po okolo 13,5min...
                time_left = round(total_time - (time_elapsed / 1000000), 2)
                print(time_left)
                distance_elapsed = self.motor.frequency * (time_elapsed / 1000000) * (self.motor.step_distance / self.motor.microsteps)

                self.display.fill_rect(0, 9, 128, 64, 0)
                self.display.line(0, 9, 128, 9, 1)
                self.display.text('<<<<<<<' if MotorDriver.LEFT == self.motor.direction else '>>>>>>>', 36, 12)
                self.display.text('TOTAL: ' + str(self.nice_time(int(total_time))), 0, 23)
                self.display.text('LEFT:  ' + str(self.nice_time(int(time_left))), 0, 32)

                self.display.text('DIST:  ' + str(int(distance_elapsed)) + ' mm', 0, 41)

                self.display.line(0, 54, 128, 54, 1)
                self.display.text('R/Hz: ' + str(self.motor.microsteps) + '/' + str(self.motor.frequency), 0, 56)
                self.display.show()
            await asyncio.sleep_ms(1000)

    @staticmethod
    def nice_time(seconds: int) -> str:
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return "%02d:%02d:%02d" % (h, m, s)

    """ Move dolly to start position
    """
    def goto_start(self):
        self.loop.call_soon(self.motor.moveto_edge(MotorDriver.LEFT))

    """ Move dolly to end position
    """
    def goto_end(self):
        self.loop.call_soon(self.motor.moveto_edge(MotorDriver.RIGHT))

    """ Force stop motor
    """
    def stop(self):
        self.loop.call_soon(self.motor.stop)

    """ Change motor speed
    """
    def speed(self, value: int):
        self.motor.motor_driver.set_resolution(value)

    """ Move dolly by direction in time
    """
    def move_dolly(self, distance: int, direction: int, time: int=None):
        self.loop.call_soon(self.motor.move(direction, distance, time))
