from machine import Pin, ADC


class Config:

    display_active = True
    display_width = 128
    display_height = 64

    display_scl = Pin(23)
    display_sda = Pin(22)

    # battery voltage: 2.5 - 4.2 (7.5 - 12.6)
    # adc = ADC(Pin(36))
    # adc.atten(ADC.ATTN_11DB)

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
