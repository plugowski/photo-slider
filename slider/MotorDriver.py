from machine import Pin, PWM


class MotorDriver:
    """ Motor driver can change steps mode to microsteps and define frequency for PWM.
    """

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
        1: [0, 0, 0],
        2: [1, 0, 0],
        4: [0, 1, 0],
        8: [1, 1, 0],
        16: [1, 1, 1]
    }

    def __init__(self, step: Pin, direction: Pin, m1: Pin, m2: Pin, m3: Pin, endstop: Pin):
        self.pwm = PWM(step)
        self.pwm.duty(512)
        self.pwm.deinit()

        self.endstop = endstop
        self.direction = direction
        self.m1 = m1
        self.m2 = m2
        self.m3 = m3

        self.set_resolution(1)

    def set_direction(self, direction: int):
        """ Set direction to right/left
        """

        self.direction.value(direction == self.RIGHT)
        return self

    def set_opposite_direction(self):
        """ Reverse direction based on current settings
        """

        self.direction.value(self.LEFT if self.direction.value() else self.RIGHT)
        return self

    def set_resolution(self, resolution: int = 1):
        """ Set microsteps for stepper motor
        """

        config = self.resolution_settings[resolution]
        self.m1.value(config[0])
        self.m2.value(config[1])
        self.m3.value(config[2])
        return self

    def start(self, frequency: int):
        """ Just send move signal to motor
        """

        self.pwm.freq(frequency)
        self.pwm.init()

    def stop(self):
        """ Stop sending move signal to motor
        """

        self.pwm.deinit()
