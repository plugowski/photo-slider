from math import pi, floor
from machine import Pin
import uasyncio as asyncio

# todo: managae semaphore for motor - only one process can use a motor at once
# todo: manage async push buttons
# todo: manage beter stop action
# todo: define default motor speed in calibration and manual mode

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
        return self.loop.create_task(self.motor.moveto_edge(self.motor.LEFT))

    """ Calibrate slider - initialize move dolly to the end (one edge) and go back to start
    """
    async def calibrate(self):
        # reset length
        self.length = 0

        # move dolly to the end...
        await self.motor.moveto_edge(self.motor.RIGHT)

        # ...reset position to calculate total length of slider...
        self.dolly.set_position(0)

        # ...then go to start and calculate length...
        await self.motor.moveto_edge(self.motor.LEFT)

        # ...set length and position (always 0 - start)
        self.length = abs(self.dolly.get_position())
        self.dolly.set_position(0)

    """ Move dolly to start position
    """
    def goto_start(self):
        self.loop.create_task(self.motor.moveto_edge(self.motor.LEFT))

    """ Move dolly to end position
    """
    def goto_end(self):
        self.loop.create_task(self.motor.moveto_edge(self.motor.RIGHT))

    """ Force stop motor
    """
    def stop(self):
        self.loop.call_soon(self.motor.stop)

    """ Move dolly by direction in time 
    """
    def move_dolly(self, distance: int, direction: int, time: int=None):
        self.loop.create_task(self.motor.move(direction, distance, time))

    """ Move dolly by direction in time 
    """
    def move_dolly_edge(self, direction: int):
        self.loop.create_task(self.motor.moveto_edge(direction))

    """ Manual move dolly it shouldn't be async, just in real time move
    """
    def move_dolly_manual(self, direction: int):
        self.motor.move(direction, 1)


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
Motor knows:
 # diameter of used pulley
 # resolution (steps by rotation)
 # distance by step

Motor can:
 # move by specified distance (how many steps should jump)
 # move on specified direction
 # todo: change step mode 1/2, 1/4, 1/8 i 1/16 for better precission
"""


class Motor:

    """
    Direction constants
    """
    RIGHT = 1
    LEFT = -1

    MAX_SPEED = 160   # mm/s
    MIN_SPEED = 0.16  # mm/s

    """ Determine if motor should be stopped """
    motor_stop = False
    """ Check if limit switch has been reached """
    limit_switch = False

    def __init__(self, step: Pin, direction: Pin, edge: Pin, dolly: Dolly, resolution: int=200, pulley: float=10.2):
        self.loop = asyncio.get_event_loop()
        self.locker = Lock()
        self.dolly = dolly

        self.rotate = 2 * pi * (pulley / 2)
        self.step_distance = self.rotate / resolution

        # configure pins
        self.pin_edge = edge
        self.pin_step = step
        self.pin_dir = direction

        # reset pins
        self.pin_dir.off()
        self.pin_step.off()

    """ Make one step in specified direction
    """
    def step(self, direction: int, ignore_switch: bool=False):

        # check if edge was reached or motor hasn't been stopped
        if (not ignore_switch and self.__limit_switch()) or not self.__can_work():
            return False

        # set direction
        self.pin_dir.value(direction == 1)

        # send signal on/off to motor
        self.pin_step.on()
        self.pin_step.off()
        return True

    """ Rotate as many steps until reach 1mm distance on pulley
    """
    def move_mm(self, direction: int):

        steps_moved = 0
        steps_to_do = self.__calculate_steps(1)
        move_status = True

        while steps_moved < steps_to_do:
            move_status = self.step(direction)
            if not move_status:
                break
            steps_moved += 1

        # update dolly position (+/- X steps)
        self.loop.call_soon(self.dolly.change_position, steps_moved, direction)
        return move_status

    """ Move belt by distance on specified direction in time
    """
    async def move(self, direction: int, distance: int, time: int = None) -> int:

        try:
            # lock motor
            self.locker.lock('move')
            # todo: check if interval isn't smaller than minimum interval (max speed)
            interval = self.__get_interval(distance, time)

            # move dolly by 1 mm until whole distance will be reached
            moved = 0
            while moved < distance:
                if not self.move_mm(direction):
                    break
                moved += 1
                await asyncio.sleep_ms(interval)

            # even if motor has been stopped now is time to reset status
            self.start()
            self.locker.unlock('move')

        except LockedProcessException:
            return False

        return True

    """ Rotate motor as long as limit switch will be achieved
    """
    async def moveto_edge(self, direction: int):

        try:

            self.locker.lock('move_edge')

            counter = 0
            while self.move_mm(direction):
                counter += 1
                await asyncio.sleep_ms(0)

            # when motor move to edge it reach limit switch, to release it dolly should go back couple steps
            self.release_limit_switch(-1 * direction)

            # even if motor has been stopped now is time to reset status
            self.start()
            self.locker.unlock('move_edge')

        except LockedProcessException:
            return False

        return True

    """ If limit switch will be reached, it is necessary to move it oposite until release
    """
    def release_limit_switch(self, direction: int):

        steps_moved = 0
        while self.pin_edge.value() == 1:
            self.step(direction, True)
            steps_moved += 1

        # update dolly position (+/- X steps)
        self.loop.call_soon(self.dolly.change_position, steps_moved, direction)

    """ Stop motor!
    """
    def stop(self):
        self.motor_stop = True

    """ Start motor
    """
    def start(self):
        self.motor_stop = False

    """ Check if motor is locked / is working
    """
    def is_locked(self):
        return self.locker.is_locked()

    """ Convert distance in mm into steps
    """
    def __calculate_steps(self, distance: int) -> int:
        return int(floor(distance / self.step_distance))

    """ Check limit switch status
    """
    def __limit_switch(self) -> bool:
        return self.pin_edge.value() == 1

    """ Check if motor still can work
    """
    def __can_work(self):
        return not self.motor_stop

    """ Calculate interval for each step by stepper motor return interval in milliseconds
    """
    @staticmethod
    def __get_interval(distance: int = None, time: int = None) -> int:

        if time is None or distance is None or distance == 0:
            return 0

        return int((time / distance) * 1000)


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
