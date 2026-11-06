# Interactive four-servo bench test

Run `servo_sequence_test.py` on the Orange Pi using the confirmed GPIO I2C bus
(bus 0 in the latest session) and PCA9685 address 0x40. It does not affect the
LCD signal mapping or activate the main GuideBot hardware adapters.

Before movement, confirm supply voltage compatibility, measured voltage, and
V+/GND polarity. The four 1.5 V R6 cells remain an unverified 6 V nominal source
for the physical Tower Pro SG90 units; this script does not resolve that issue.
Test servos unloaded and unattached to the mechanism. Disabling PWM releases
holding torque, so support any attached mechanism. Do not change servo plugs
while powered. Connect servo power directly to the PCA9685 green terminal, not
the breadboard. See [combined wiring](../docs/COMBINED_WIRING.md).

Proposed channel names, pending identification of the actual motors:

| Channel | Role |
| --- | --- |
| 0 | Left hand |
| 1 | Right hand |
| 2 | Left foot |
| 3 | Right foot |

In Windows Command Prompt/PowerShell, transfer the file (the board's current
address is 192.168.68.125; recheck if it changes):

```powershell
scp "D:\GuideBot humanoid campus information assistant\tools\servo_sequence_test.py" recursia@192.168.68.125:~/
```

Then, in an Orange Pi SSH session:

```sh
sudo apt install -y python3-smbus
sudo python3 ~/servo_sequence_test.py --pause 2
```

If running in a repository clone instead, use
`sudo python3 tools/servo_sequence_test.py --pause 2`.

The test first disables all 16 PCA9685 outputs and sets approximately 50 Hz using
the internal oscillator. It then waits for Enter before each channel. Each
sequence requests 1500, 1400, 1500, 1600, and 1500 microsecond pulses, with one
second at each value. It disables that channel, pauses two seconds, then waits
for Enter again. Change `--pause` to a number from 0 to 10 seconds if desired.
There is no automatic advance past the Enter prompt. Type `q` at a prompt or
press Ctrl+C to stop.

Only one channel receives PWM at a time. The program attempts to disable every
output on normal completion, quitting, EOF, interruption, and I2C errors. If
communication fails, software cannot guarantee output shutdown: disconnect
servo power. A completed command sequence is not a physical pass result. Check
for smooth small movements, excessive noise, binding, heating, and power resets.
No full-range sweep or walking routine is included.

Ten local simulated-I2C tests verify input gating, channel sequencing/pause,
quit behavior, interruption, EOF, external-clock rejection, I2C-error cleanup,
and compatibility with SMBus objects that require explicit close() rather than
supporting the context manager protocol:

```sh
python -m unittest discover -s tools -p test_servo_sequence.py -v
```

These tests do not verify physical motion, servo power, timing on the actual
controller, or mechanical limits. Register reference:
[NXP PCA9685 datasheet](https://www.nxp.com/docs/en/data-sheet/PCA9685.pdf).
