"""Explicitly disabled integration placeholders, never imported by the simulator."""


class HardwareDisabledError(RuntimeError):
    pass


class PCA9685ServoDriver:
    def __init__(self, *args, **kwargs):
        raise HardwareDisabledError("Real motor control is disabled. Implement and calibrate on Orange Pi first.")


class HCSR04DistanceSensor:
    def __init__(self, *args, **kwargs):
        raise HardwareDisabledError("Real ultrasonic input is disabled. Orange Pi driver is not implemented.")


class SPITFTDisplay:
    def __init__(self, *args, **kwargs):
        raise HardwareDisabledError("Real SPI LCD output is disabled. Display driver is not implemented.")
