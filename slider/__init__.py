from math import pi, ceil
from machine import Pin
import uasyncio as asyncio

# todo: managae semaphore for motor - only one process can use a motor at once
# todo: manage async push buttons
# todo: manage beter stop action
# todo: when edge has been reached, move aboit 1mm in oposite direction (to release button)

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
        self.dolly = dolly
        self.motor = motor
        self.loop = asyncio.get_event_loop()

    """ Reset slider, so move dolly on start position
    """
    async def reset(self):
        return self.loop.create_task(self.motor.moveto_edge(self.motor.LEFT))

    """ Calibrate slider, so get information about current dolly position and slider length
    """
    async def calibrate(self):
        # reset length
        self.length = 0

        # move dolly to the end...
        await self.motor.moveto_edge(self.motor.LEFT)

        self.dolly.set_position(0)

        # ...then go to start and calculate total slider length...
        await self.motor.moveto_edge(self.motor.RIGHT)

        # set length and position
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
        self.loop.create_task(self.motor.move(distance, direction, time))

    """ Manual move dolly it shouldn't be async, just in real time move
    """
    def move_dolly_manual(self, direction: int):
        self.motor.move(1, direction)


"""
Dolly knows:
 # its own position
"""


class Dolly:

    """ Actual dolly position """
    current_position = 0

    """ Change 
    """
    def change_position(self, value):
        self.current_position += value

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

    RIGHT = 1
    LEFT = -1

    """ Determine if motor should be stopped """
    motor_stop = False

    def __init__(self, step: Pin, direction: Pin, edge: Pin, dolly: Dolly, resolution: int=200, pulley: float=10.2):
        self.loop = asyncio.get_event_loop()
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
    def step(self, direction: int):

        # check if edge was reached
        if self.__limit_switch() or not self.__can_work():
            # once motor stopped, switch it again to False
            self.motor_stop = False
            return False

        # update dolly position (+/- 1 step)
        self.loop.call_soon(self.dolly.change_position, direction)

        # set direction
        self.pin_dir.value(direction == 1)

        # send signal on/off to motor
        self.pin_step.on()
        self.pin_step.off()

        return True

    """ Move belt by distance on specified direction in time
    """
    async def move(self, distance: float, direction: int, time: int=None) -> int:

        moved = 0
        steps = self.__calculate_steps(distance)
        interval = self.__get_interval(steps, time)

        while moved < steps:
            if not self.step(direction):
                break

            moved += 1
            await asyncio.sleep_ms(interval)

        return moved

    """ Rotate motor as long as limit switch will be achieved
    """
    async def moveto_edge(self, direction: int):

        moved = 0
        while self.step(direction):
            await asyncio.sleep(0)

        return moved

    """ Stop motor!
    """
    def stop(self):
        self.motor_stop = True

    """ Convert distance in mm into steps
    """
    def __calculate_steps(self, distance: float) -> int:
        return int(ceil(distance / self.step_distance))

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
    def __get_interval(steps: int, time: int=None) -> int:

        if time is None or time == 0:
            return 0

        return int((1 / (steps / time)) * 1000)
