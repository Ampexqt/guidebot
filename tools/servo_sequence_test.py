#!/usr/bin/env python3
"""Interactive, unloaded PCA9685 bench test: channels 0-3, one at a time.

Requires a confirmed compatible servo supply and correct V+/GND polarity.
This does not establish compatibility of an unverified 6 V battery pack.
Install Debian python3-smbus. Run as a file so Enter is read from the terminal.
"""

import argparse
import time

ADDRESS = 0x40
CHANNELS = [(0, 'Left hand'), (1, 'Right hand'), (2, 'Left foot'), (3, 'Right foot')]
PULSES_US = (1500, 1400, 1500, 1600, 1500)


class PCA9685:
    def __init__(self, bus, address=ADDRESS, sleep=time.sleep):
        self.bus = bus
        self.address = address
        self.sleep = sleep

    def off(self, channel):
        self.bus.write_byte_data(self.address, 0x09 + 4 * channel, 0x10)

    def off_all(self):
        # Attempt every output even if a preceding I2C write fails.
        errors = []
        for channel in range(16):
            try:
                self.off(channel)
            except OSError as error:
                errors.append(error)
        if errors:
            raise OSError('Could not disable every output; disconnect servo power.') from errors[0]

    def configure(self):
        self.off_all()
        mode = self.bus.read_byte_data(self.address, 0x00)
        if mode & 0x40:
            raise RuntimeError('External clock selected; this test expects the internal oscillator.')
        self.bus.write_byte_data(self.address, 0x00, 0x10)
        self.bus.write_byte_data(self.address, 0xFE, 121)
        self.bus.write_byte_data(self.address, 0x01, 0x04)
        self.bus.write_byte_data(self.address, 0x00, 0x20)
        self.sleep(0.01)
        self.bus.write_byte_data(self.address, 0x00, 0xA0)

    def pulse(self, channel, microseconds):
        if channel not in range(4) or microseconds not in PULSES_US:
            raise ValueError('Only channels 0-3 and the small preset movements are allowed.')
        ticks = round(microseconds * 4096 * 50 / 1_000_000)
        self.bus.write_i2c_block_data(
            self.address, 0x06 + 4 * channel,
            [0, 0, ticks & 255, (ticks >> 8) & 15])


def run_sequence(controller, read=input, write=print, sleep=time.sleep, pause=2.0):
    completed = []
    try:
        controller.configure()
        write('Use unloaded servos with a confirmed compatible supply. Ctrl+C stops.')
        write('Names below are the proposed channel plan; identify the actual connected limbs.')
        for channel, name in CHANNELS:
            while True:
                answer = read(f'\nChannel {channel}: {name}. Enter = test, q = quit: ').strip().lower()
                if answer == 'q':
                    return completed
                if answer == '':
                    break
                write('Press Enter to start this servo, or type q to quit.')
            try:
                for microseconds in PULSES_US:
                    write(f'Channel {channel}: {microseconds} us')
                    controller.pulse(channel, microseconds)
                    sleep(1.0)
            finally:
                controller.off(channel)
            completed.append(channel)
            write(f'Channel {channel} sequence finished; output disabled.')
            if channel != CHANNELS[-1][0]:
                write(f'Pausing {pause:g} seconds before the next prompt.')
                sleep(pause)
        return completed
    finally:
        controller.off_all()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bus', type=int, default=0,
                        help='Confirmed GPIO I2C bus (default: 0); never select HDMI.')
    parser.add_argument('--pause', type=float, default=2,
                        help='Seconds between servos, 0-10 (default: 2).')
    args = parser.parse_args()
    if args.bus < 0 or not 0 <= args.pause <= 10:
        parser.error('Bus must be nonnegative and pause must be between 0 and 10 seconds.')
    try:
        from smbus import SMBus
        # Debian's python3-smbus may expose close() without __enter__/__exit__.
        bus = SMBus(args.bus)
        try:
            completed = run_sequence(PCA9685(bus), pause=args.pause)
        finally:
            bus.close()
        print(f'Completed command sequences for channels: {completed}. Outputs disabled.')
        print('Confirm actual movement yourself; completed commands do not prove a motor passed.')
    except (KeyboardInterrupt, EOFError):
        print('\nStopped; output-disable cleanup was attempted.')
    except (OSError, RuntimeError, ValueError, ImportError) as error:
        print(f'Test stopped: {error}')
        print('Disconnect servo power if communication or output shutdown failed.')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
