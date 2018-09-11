from machine import Pin, ADC, I2C
from ssd1306 import SSD1306_I2C


class Config:
    """ Configuration file for slider.
    """

    # default settings
    display_active = True
    display_width = 128
    display_height = 64

    max_pin_voltage = 3.11
    battery_max_voltage = 12.4
    battery_min_voltage = 10.5
    battery_probes_amount = 2000

    # define pins for display
    display_scl = Pin(4)
    display_sda = Pin(5)

    # define status led (on-board led)
    status_led = Pin(2, Pin.OUT)

    # define motor control pins
    pin_edge = Pin(0, Pin.IN, Pin.PULL_UP)
    pin_step = Pin(12, Pin.OUT)
    pin_dir = Pin(14, Pin.OUT)

    # define motor driver step motor size pins
    pin_ms1 = Pin(4, Pin.OUT)
    pin_ms2 = Pin(16, Pin.OUT)
    pin_ms3 = Pin(17, Pin.OUT)

    # read battery voltage to show in status
    adc = ADC(Pin(36))
    adc.atten(ADC.ATTN_11DB)

    # setup oled display
    i2c = I2C(scl=display_scl, sda=display_sda)
    display = None if not display_active else SSD1306_I2C(display_width, display_height, i2c)
