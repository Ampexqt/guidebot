# HC-SR04 distance bench test

Prepared November 6, 2026. The user confirmed an HC-SR04 with VCC, TRIG, ECHO,
GND and two 10 kOhm resistors fitted. Electrical placement and physical readings
still need verification. This diagnostic does not command servos or alter LCD
signal assignments.

Shut down and unplug the Orange Pi before changing wiring. Leave the servo
battery pack disconnected throughout this sensor-only test.

## Physical header connections

| HC-SR04 connection | Orange Pi One physical pin |
| --- | --- |
| VCC | 2 (5 V) |
| GND | 14 (GND) |
| TRIG | 29 (PA7, gpiochip0 offset 7) |
| Divided Echo junction | 31 (PA8, gpiochip0 offset 8) |

Standard HC-SR04 Echo must not connect directly to the Orange Pi. The two equal
resistors form this divider; merely possessing two resistors is insufficient:

```text
HC-SR04 ECHO --- R1 10k ---+--- Orange Pi physical pin 31
                         |
                       R2 10k
                         |
                        GND
```

At 5 V Echo, the junction is approximately 2.5 V. The sensor ground and divider
ground both connect to the Orange Pi ground. Preserve the separate 3.3 V group
used by LCD LED/PCA9685 VCC. Never insert a 5 V or ground wire into that group.

The long-breadboard hole numbers in [combined wiring](../docs/COMBINED_WIRING.md)
are not literal positions on the user's mini breadboard. Transfer the electrical
nodes to separate connected five-hole groups. The photo's upper and lower blocks
are separate across the center gap; check connections before applying power.

## Transfer and run

In a NEW Windows PowerShell window showing `PS C:\...>`:

```powershell
scp "D:\GuideBot humanoid campus information assistant\tools\ultrasonic_test.py" recursia@192.168.68.125:~/
```

The LAN address may change; use the current one. Then in the Orange Pi SSH
window showing `recursia@orangepione:~$`:

```sh
sudo python3 ~/ultrasonic_test.py --samples 20 --interval 0.5
```

From a repository clone, use `sudo python3 tools/ultrasonic_test.py` instead.
The existing `python3-libgpiod` 2.x installation used by the TFT touch tool is
required. No SMBus or SPI library is needed for this test. If a GPIO is claimed
by another process, stop the conflicting application; do not substitute random
pins. The diagnostic checks the expected gpiochip0 controller label.

Compare a flat target at measured distances such as 10, 30, and 50 cm. Remove
or turn the target away to check that a missing echo reports a timeout instead
of freezing the program. Readings outside 2-400 cm are rejected. No-echo is not
a valid zero-centimeter measurement. Press Ctrl+C to stop.

## Verification limits

The program uses monotonic kernel timestamps for rising/falling edges and an
approximately 40 ms bounded wait. The trigger is returned low after each pulse
and during normal/interrupted cleanup. A 0.5 second default gap separates
attempts; the CLI requires at least 0.06 seconds between attempts.

The distance calculation assumes a sound speed of 343 m/s. Air temperature,
target angle/material, sensor variation, electrical noise, and Linux scheduling
can affect practical results. Judge performance using measured target distances;
valid-looking numbers alone do not establish accuracy or successful integration.

Ten simulated tests cover pulse-to-distance conversion, stale/unrelated edges,
absent/falling-edge timeouts, a bounded noise drain, stuck-high input, trigger
cleanup on interruption, and invalid/out-of-range durations:

```sh
python -m unittest discover -s tools -p test_ultrasonic.py -v
```

These checks do not open GPIO devices or verify physical timing/wiring. The
main GuideBot distance adapter is still simulated.

References:
- [HC-SR04 Echo divider](https://learn.adafruit.com/distance-measurement-ultrasound-hcsr04/connect-the-sensor)
- [libgpiod edge-event waits](https://libgpiod.readthedocs.io/en/master/python_line_request.html)
