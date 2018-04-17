from slider.Dolly import *
from slider.Motor import *
from slider.MotorDriver import *
from slider.Status import *
import uasyncio as asyncio


class Slider:
    """ Main class of Slider. Class can delegate tasks for motor or direct for driver.
    """

    working_task = None  # define current working task to kill it after fire stop method.

    def __init__(self, motor: Motor, status: Status):
        self.motor = motor
        self.status = status

    async def reset(self):
        """ Reset slider, so move dolly on start position
        """

        self.__do_action(self.motor.moveto_edge(MotorDriver.LEFT))

    def goto_start(self):
        """ Move dolly to start position
        """

        self.__do_action(self.motor.moveto_edge(MotorDriver.LEFT))

    def goto_end(self):
        """ Move dolly to end position
        """

        self.__do_action(self.motor.moveto_edge(MotorDriver.RIGHT))

    def stop(self):
        """ Force stop motor
        """

        if self.working_task:
            # cancel current working task
            asyncio.cancel(self.working_task)
            self.working_task = None

        self.motor.stop()

    def move_dolly(self, distance: int, direction: int, time: int = None):
        """ Move dolly by direction in time
        """

        self.__do_action(self.motor.move(direction, distance, time))

    def __do_action(self, generator):

        try:
            self.working_task = generator
            asyncio.get_event_loop().call_soon(self.working_task)
        except LockedProcessException as e:
            self.stop()
            # todo: send error message to client
            # self.status.write('motor locked')
            print('motor locked')
            print(e)
        except RuntimeError as e:
            print(e)
