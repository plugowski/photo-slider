from math import pi
from machine import Pin, PWM
import uasyncio as asyncio

# todo: managae semaphore for motor - only one process can use a motor at once
# todo: manage async push buttons
# todo: manage beter stop action
# todo: define default motor speed in calibration and manual mode


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
        self.pwm.duty(512)

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

    def __init__(self, motor_driver: MotorDriver, edge: Pin, resolution: int=200, pulley: float=10.2):

        self.motor_driver = motor_driver
        self.loop = asyncio.get_event_loop()
        self.locker = Lock()

        self.full_rotate_distance = 2 * pi * (pulley / 2)
        self.step_distance = self.full_rotate_distance / resolution
        self.steps_per_mm = 1 / self.step_distance

        # configure pins
        self.pin_edge = edge

    """ Move belt by distance on specified direction in time
    """
    async def move(self, direction: int, distance: int, time: int = None) -> int:

        try:

            # max available speed
            resolution = 1
            frequency = 800
            time_ms = (distance / frequency) * 1000

            if time is not None:

                # calculate frequency and resolution for specified distance and time
                steps_to_move = distance * self.steps_per_mm
                prev_frequency = prev_resolution = None

                for resolution in MotorDriver.resolutions:
                    frequency = (steps_to_move / time) * resolution

                    if (resolution == 1 and frequency < 400) or frequency < 1000:
                        prev_frequency = frequency
                        prev_resolution = resolution
                        continue
                    else:
                        frequency = prev_frequency
                        resolution = prev_resolution

                    break

                time_ms = time * 1000

            # todo: check if motor is locked self.locker.is_locked()
            # todo: lock motor
            # self.locker.lock('move')

            # listen edge limiter events
            asyncio.get_event_loop().create_task(self.edge())

            self.motor_driver\
                .set_direction(direction)\
                .set_resolution(resolution)\
                .start(frequency)

            await asyncio.sleep_ms(time_ms)

            self.motor_driver.stop()
            # self.locker.unlock('move')

        except LockedProcessException:
            return False

        return True

    """ Rotate motor as long as limit switch will be reached
    """
    async def moveto_edge(self, direction: int):

        try:

            asyncio.get_event_loop().create_task(self.edge())

            self.motor_driver\
                .set_resolution(1)\
                .set_direction(direction)\
                .start(700)

        except LockedProcessException:
            return False

        return True

    async def edge(self):

        while True:
            if self.pin_edge.value() == 0:

                self.motor_driver\
                    .set_opposite_direction()\
                    .set_resolution(4)\
                    .start(500)
                await asyncio.sleep_ms(100)
                self.motor_driver.stop()
                break

        return True

    """ If limit switch will be reached, it is necessary to move it oposite until release
    """
    # def release_limit_switch(self):
        # todo: przesuwac slider tak dlugo jak switch jest wcisniety

    """ Stop motor!
    """
    def stop(self):
        self.motor_driver.stop()


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

    def __init__(self, dolly: Dolly, motor: Motor):
        self.loop = asyncio.get_event_loop()
        self.dolly = dolly
        self.motor = motor

    """ Reset slider, so move dolly on start position
    """
    async def reset(self):
        return self.loop.create_task(self.motor.moveto_edge(MotorDriver.LEFT))

    """ Move dolly to start position
    """
    def goto_start(self):
        self.loop.create_task(self.motor.moveto_edge(MotorDriver.LEFT))

    """ Move dolly to end position
    """
    def goto_end(self):
        self.loop.create_task(self.motor.moveto_edge(MotorDriver.RIGHT))

    """ Force stop motor
    """
    def stop(self):
        self.loop.call_soon(self.motor.stop)

    """ Move dolly by direction in time
    """
    def move_dolly(self, distance: int, direction: int, time: int=None):
        self.loop.create_task(self.motor.move(direction, distance, time))