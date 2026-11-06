# GuideBot combined wiring guide

Prepared November 4, 2026 (Asia/Manila).

This guide preserves the tested Orange Pi One TFT/touch signal mapping and adds
PCA9685 logic connections through a shared 3.3 V breadboard group. The ultrasonic
assignment is proposed, not physically tested, and applies ONLY to a standard
four-pin HC-SR04 labeled VCC, TRIG, ECHO, GND. Confirm the actual sensor before
following that section. Speech/audio wiring is outside this guide and still
requires identification of the speaker/audio interface.

All Orange Pi numbers below are PHYSICAL positions on its 40-pin header, not
GPIO software offsets. Locate its pin-1 marking first; do not infer orientation
from a rotated photo or a Raspberry Pi picture.

## 1. Prepare without power

Shut down the Orange Pi if running, unplug its power bank, and remove batteries
from the servo battery holder. Move wires only with both supplies disconnected.
Keep motors off the robot mechanism for initial tests.

Required for this layout: jumper connections with female sockets at the module
headers and male ends at the breadboard, plus TWO 10 kOhm resistors (1/4 W is
sufficient) for the HC-SR04 divider. If using separate female/female and male/male
jumpers, join one of each to form the required female-to-male connection.

The user's four R6 carbon cells are 1.5 V each (6 V nominal together). This guide
does not establish that the physical Tower Pro SG90 units support that pack;
the supplied 4.8-6.0 V screenshot pictured a different Smraza S51 unit. Keep the
holder empty until actual servo supply compatibility, measured voltage, and
terminal polarity are confirmed. Four 1.2 V NiMH AA cells (4.8 V nominal) were
the originally planned battery option. Do not recharge nonrechargeable R6 cells.

## 2. Understand the breadboard groups

Use the printed letters and numbers. On a standard terminal-strip breadboard,
A1 through E1 connect together; F1 through J1 form a different group across the
center gap. Different numbered rows are separate. This design uses only A-E.
Never treat the entire long column of holes as one connected rail.

The named holes below are exclusive assignments for this plan. Leave all other
holes in these groups unused unless deliberately extending the same electrical
connection. Ground, 3.3 V, 5 V, and Echo must remain in their separate groups.

## 3. Shared 3.3 V for LCD LED and PCA9685 logic

Detach ONLY the LCD LED wire's Orange Pi end from physical pin 1. Keep its LCD
end connected. Make these connections instead:

| From | To |
| --- | --- |
| Orange Pi pin 1 (3.3 V) | A1 |
| LCD LED | B1 |
| PCA9685 VCC | C1 |

A1/B1/C1 are one shared 3.3 V node. Do not connect GND, 5 V, the battery leads,
or PCA9685 V+ to this group. LCD VCC stays on Orange Pi pin 17. This change
shares the existing supply; it does not require a new GPIO setting or alter
the saved calibration's display orientation.

## 4. LCD display and touch (preserve existing signal wiring)

| TFT label | Destination |
| --- | --- |
| VCC | Orange Pi pin 17 (3.3 V) |
| GND | Orange Pi pin 6 (GND) |
| LED | Breadboard B1 (shared 3.3 V) |
| CS | Orange Pi pin 24 (PC3 / SPI0 CS0) |
| RESET | Orange Pi pin 18 (PC7) |
| DC | Orange Pi pin 22 (PA2) |
| SDI / MOSI | Orange Pi pin 19 (PC0 / SPI0 MOSI) |
| SCK | Orange Pi pin 23 (PC2 / SPI0 clock) |
| T_CLK | Orange Pi pin 11 (PA1) |
| T_CS | Orange Pi pin 15 (PA3) |
| T_DIN | Orange Pi pin 13 (PA0) |
| T_DO | Orange Pi pin 16 (PC4) |
| T_IRQ | Orange Pi pin 7 (PA6) |

Leave the display SDO/MISO pin and all SD-card pins disconnected. Touch uses
software SPI on its separate five wires, matching the calibration tool.

## 5. PCA9685 logic connections

| PCA9685 label | Destination |
| --- | --- |
| VCC | Breadboard C1 (3.3 V) |
| GND | Orange Pi pin 9 (GND) |
| SDA | Orange Pi pin 3 (PA12 / I2C0 SDA) |
| SCL | Orange Pi pin 5 (PA11 / I2C0 SCL) |
| OE | Leave disconnected for this bench setup |

Orange Pi ground pins 6, 9, and 14 are electrically common. The PCA9685 ground
also connects its logic and servo-supply ground. VCC is logic power; V+ is the
separate motor-power distribution rail. Do not bridge VCC to V+ or power VCC
from a 5 V/6 V servo pack: onboard I2C pull-ups must stay at 3.3 V for this board.

## 6. Four servo connectors and motor power

The user clarified on November 4 that the robot has two hands and two feet,
with no motorized head or neck. These are proposed channel assignments; actual
limb identity, joint orientation, safe pulse limits, and load have not yet been
calibrated. These names supersede the earlier head-pan/head-tilt assumption.

| Servo role | PCA9685 channel |
| --- | --- |
| Left hand | 0 |
| Right hand | 1 |
| Left foot | 2 |
| Right foot | 3 |

The simulator still uses its original head/arm logical joint names. Do not
apply its gesture poses directly to this physical limb layout. A later software
mapping change and per-joint mechanical calibration are required. Two foot
servos alone do not establish a tested walking or load-bearing mechanism.

For EACH servo, the three-hole connector spans all three pins of ONE channel:

| Servo lead | PCA9685 channel label |
| --- | --- |
| Brown | GND / - |
| Red | V+ / + |
| Yellow or orange | PWM / signal |

Use the printed labels, not photo orientation or plastic colors alone. A servo
does not plug directly onto the Orange Pi header. Connect only channel 0 for
the first movement test; test the others individually before connecting all
four for a combined test.

AFTER supply compatibility and measured voltage have been confirmed:

| Servo supply lead | PCA9685 green screw terminal |
| --- | --- |
| Positive (normally red) | V+ / + |
| Negative (normally black) | GND / - |

Check terminal markings and clamp insulation-free conductor securely inside
the terminal, with no loose strands or exposed ends touching. Route motor power
directly to this terminal, not through the breadboard or the Pi's GPIO power
wiring. Keep the Orange Pi on its own power bank. Their grounds are shared via
the PCA9685 GND connection; keep their positive supplies separate.

The holder, switch, cells, and leads must support motor current under load.
Wiring four channels does not prove that one battery pack can reliably run all
four simultaneously. Test current/power stability and mechanical limits first.

## 7. HC-SR04 power and trigger

If the sensor differs from a standard 5 V HC-SR04, stop at this section and
identify its requirements. For a standard HC-SR04, make these breadboard links:

| From | To |
| --- | --- |
| Orange Pi pin 14 (GND) | A10 |
| HC-SR04 GND | B10 |
| Orange Pi pin 2 (5 V) | A20 |
| HC-SR04 VCC | B20 |
| Orange Pi pin 29 (PA7) | HC-SR04 TRIG |

Rows 1, 10, and 20 are separate: 3.3 V, GND, and 5 V respectively. The 5 V
connection powers only the small sensor in this layout, not the servos.

## 8. HC-SR04 Echo divider (required for this 5 V sensor)

Use TWO 10 kOhm resistors, R1 and R2. They have no polarity.

| Connection | Breadboard placement |
| --- | --- |
| HC-SR04 ECHO wire | A30 |
| R1 first leg | B30 |
| R1 second leg | A35 |
| R2 first leg | B35 |
| R2 second leg | C10 (ground group) |
| Orange Pi pin 31 (PA8) | C35 |

```text
HC-SR04 ECHO ---- R1 10k ----+---- Orange Pi pin 31
                           |
                         R2 10k
                           |
                          GND
```

At a 5 V Echo input, the equal resistors give approximately 2.5 V at the GPIO
input. Do not connect the sensor's 5 V Echo directly to pin 31. Each resistor
must span different connected groups, exactly as listed. If the resistors are
not available, leave the ultrasonic section disconnected.

## 9. Orange Pi physical pin allocation

| Pin | Assignment |
| --- | --- |
| 1 | Shared 3.3 V to breadboard A1 |
| 2 | Sensor 5 V to breadboard A20 |
| 3 | PCA9685 SDA |
| 5 | PCA9685 SCL |
| 6 | LCD GND |
| 7 | Touch IRQ |
| 9 | PCA9685 GND |
| 11 | Touch CLK |
| 13 | Touch DIN |
| 14 | Sensor/divider ground to A10 |
| 15 | Touch CS |
| 16 | Touch DO |
| 17 | LCD VCC (3.3 V) |
| 18 | LCD RESET |
| 19 | LCD MOSI |
| 22 | LCD DC |
| 23 | LCD SCK |
| 24 | LCD CS |
| 29 | Proposed HC-SR04 TRIG (PA7) |
| 31 | Proposed divided HC-SR04 Echo (PA8) |

No signal pin is assigned twice. The standalone
[HC-SR04 test](../tools/ULTRASONIC_TEST.md) now uses these ultrasonic pins, but a
physical distance/timeout test is still pending. The main GuideBot app does not
yet read this sensor. Pin availability must be checked if additional overlays
or peripherals are enabled later.

## 10. Power-on and test order

1. Photograph the completed unpowered wiring and check it against these tables.
2. Leave the servo battery holder empty. Power the Orange Pi from its power bank.
3. Confirm the TFT still works and check the available I2C buses with
   `sudo /usr/sbin/i2cdetect -l`. Identify the GPIO bus before checking address
   0x40; do not scan the HDMI bus.
4. Bench-test the identified ultrasonic sensor with the divider fitted, measuring
   known distances and confirming a missing echo cannot hang the program.
5. With power disconnected, prepare ONE servo and a confirmed compatible supply.
   Run a small center movement test; do not start with a full 0-180 degree sweep.
6. Test remaining servos individually, then assess combined current and load.

Existing TFT commands in the repo are described in
[TFT touch test instructions](../tools/TFT_TOUCH_TEST.md). This wiring guide does
not mean that the main GuideBot app already controls these physical devices.

## Sources

- [Orange Pi One manufacturer manual (mirrored PDF)](https://manuals.plus/m/b11dc744f83d119fc99bae37f2c99d678da0f80b5d7e5a40319b4427a2150a04_optim.pdf)
- [PCA9685 pinouts](https://learn.adafruit.com/16-channel-pwm-servo-driver/pinouts)
- [PCA9685 servo power and connectors](https://learn.adafruit.com/16-channel-pwm-servo-driver/hooking-it-up)
- [HC-SR04 and equal-resistor divider](https://learn.adafruit.com/distance-measurement-ultrasound-hcsr04/connect-the-sensor)
- [Breadboard connection groups](https://learn.adafruit.com/breadboards-for-beginners/breadboards)
- [Matching TFT interface documentation](https://www.lcdwiki.com/res/MSP2402/2.4inch_SPI_Module_MSP2402_User_Manual_EN.pdf)
