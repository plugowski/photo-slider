import copy
from math import pi, ceil
from machine import Pin
from slider.Lock import *
from slider.MotorDriver import MotorDriver
import uasyncio as asyncio
import utime


class Motor:
    """ Motor knows about resolution of itself as well as how to calculate frequency and time needed to move a dolly.
    """

    """
    Motor knows:
     # diameter of used pulley
     # resolution (steps by rotation)
     # distance by step
    """

    def __init__(self, driver: MotorDriver, resolution: int = 200, pulley: float = 10.2):

        self.driver = driver

        self.microsteps = self.frequency = self.direction = None
        self.time_ms = self.start_time = self.end_time = None
        self.last_interrupt = None

        # calculate defaults
        self.full_rotate_distance = 2 * pi * (pulley / 2)
        self.step_distance = self.full_rotate_distance / resolution
        self.steps_per_mm = 1 / self.step_distance

        # configure pins
        self.driver.endstop.irq(trigger=Pin.IRQ_FALLING, handler=self.endstop)

    def calculate(self, distance: int, time: int) -> tuple:
        """ Calculate frequency and resolution for specified distance and time.
        """

        frequency = microsteps = None
        time_ms = time * 1000
        steps_to_move = distance * self.steps_per_mm

        resolutions = copy.copy(MotorDriver.resolutions)
        resolutions.reverse()

        for resolution in resolutions:
            frequency = ceil((steps_to_move / time) * resolution)
            if 1 < frequency <= 1000:
                microsteps = resolution
                time_ms = int(ceil(distance / (self.step_distance / resolution) / frequency * 1000))
                break

        if microsteps is None:
            raise RuntimeError('Speed out of range!')

        return frequency, microsteps, time_ms

    def move(self, direction: int, distance: int = None, time: int = None) -> int:
        """ Move belt by distance on specified direction in time.
        """

        # only one motor process can be used
        Lock().lock('motor')

        # max available speed
        self.direction = direction

        # default values for move without time
        self.microsteps = 1
        self.frequency = 800
        self.time_ms = (distance / self.frequency) * 1000

        if time is not None:
            self.frequency, self.microsteps, self.time_ms = self.calculate(distance, time)

        self.driver \
            .set_direction(direction) \
            .set_resolution(self.microsteps) \
            .start(self.frequency)

        self.start_time = utime.ticks_ms()
        yield from asyncio.sleep_ms(self.time_ms)

        # after specified time just stop the motor
        self.stop()

    def moveto_edge(self, direction: int, resolution: int = None, freq: int = None):
        """ Rotate motor as long as limit switch will be reached
        """

        Lock().lock('motor')

        self.driver \
            .set_resolution(1 if resolution is None else resolution) \
            .set_direction(direction) \
            .start(1000 if freq is None else freq)

        yield 0

    def endstop(self, irq: Pin = None):
        """ Stop motor by hit in endstop switch. Dolly should go back couple steps to release switch.
        """

        # interrupt send couple signals one after another, to avoid couple reverse moving, wait for a while
        if 0 < utime.ticks_diff(utime.ticks_ms(), self.last_interrupt) < 750 or irq.value() == 1:
            return

        # stop motor, but only the driver (don't unlock a Motor)
        self.driver.stop()

        # change direction and move couple steps to release endstop
        self.driver \
            .set_opposite_direction() \
            .set_resolution(4) \
            .start(1000)

        # wait till endstop will be released
        utime.sleep_ms(43)

        # stop motor and release lock
        self.stop()

        # update last interrupt
        self.last_interrupt = utime.ticks_ms()

    def stop(self):
        """ Stop and unlock motor!
        """

        self.driver.stop()
        Lock().unlock('motor')
        if self.start_time:
            self.end_time = utime.ticks_ms()
