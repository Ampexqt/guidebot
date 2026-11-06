# GuideBot face, voice, and touch interface plan

Recorded: October 29, 2026

Physical limb layout corrected: November 4, 2026.

Status updated November 6: the separate `guidebot.robot` entry point implements
the face, blink, playback-driven mouth, destination menu, Repeat and Menu flow.
It includes ultrasonic greetings and optional unloaded motor motions. Combined
execution on the Orange Pi is still pending; see [runtime guide](ROBOT_RUNTIME.md).
Expression variations and mounted limb calibration remain future work.

## Purpose

GuideBot remains a campus information assistant. Visitors choose a destination
and receive spoken campus information and directions. The revision gives the
robot a cute animated face and a clear touch interface while retaining the
existing equipment plan.

## Screen design

Use the 2.4-inch, 240x320 TFT touchscreen for two main views:

- **Face view:** large animated eyes and mouth, facial expressions, and touch
  controls. The mouth moves while the speaker plays speech.
- **Destination menu:** large buttons for campus locations, with names and
  optional icons. The menu lets the visitor choose which information to hear.

The initial destination menu is a list of buttons, not a detailed campus map.
Actual destinations and directions must come from verified campus information.

## Latest decision: no subtitles; provide Repeat

The user explicitly requested removing subtitles and providing a way to hear
the information again. The agreed face view therefore has:

- **Repeat:** speaks the most recently delivered information again and plays
  the talking-mouth animation again.
- **Menu:** returns to the destination buttons.

Repeat remains available after speech finishes. Temporarily disable Repeat
while audio is playing to prevent overlapping speech. Before any message is
available to repeat, keep the button disabled.

Do not include subtitles, scrolling speech captions, or a written direction
summary in this agreed face view. A visitor who did not hear the information
uses Repeat. These are on-screen controls; additional physical buttons are not
required.

Illustrative layout, with final artwork and dimensions still to be designed:

```text
+-----------------------+
|                       |
|     Animated eyes     |
|     Animated mouth    |
|                       |
|       [Repeat]        |
|       [ Menu ]        |
+-----------------------+
```

## Intended visitor flow

1. While waiting, show a cute face with occasional blinking.
2. When visitor detection is implemented, an approaching visitor triggers a
   welcoming expression and spoken greeting.
3. Tapping the waiting face opens the destination menu.
4. Selecting a destination switches to the face view and speaks the relevant
   information while animating the mouth.
5. When speech ends, close the mouth and keep Repeat and Menu available.
6. Repeat replays that information. Menu allows another destination selection.

## Animation approach

The moving mouth is drawn on the TFT; this design does not add a mechanical
mouth servo. For the first version, animate opening and closing while speech is
playing, with blinking and expressions appropriate to waiting, welcoming, and
explaining. More closely following audio loudness is a possible later
improvement, not a requirement for the first version.

The user clarified that the four physical servos are for **two hands and two
feet**, with **no motorized head or neck**. The face and mouth are screen
animations. Proposed PCA9685 channels are 0 left hand, 1 right hand, 2 left foot,
and 3 right foot, pending identification and calibration of the actual joints.
This supersedes the earlier head/arm assumption. Existing simulator joint names
have not yet been revised to match this mechanism.

## Equipment and current progress

| Component | Intended role / current state |
| --- | --- |
| Orange Pi One running Armbian | Runs interface, speech, and robot behavior |
| 2.4-inch SPI TFT touchscreen | Face and destination menu; color and touch tests passed |
| Touch calibration | Saved in `tools/tft_touch_calibration.json`; RMS fit error about 5.95 pixels; three verification errors about 5.64, 10.47, and 13.15 pixels |
| PCA9685 | Servo controller; I2C communication previously detected at address 0x40 |
| Four SG90 servos | User reports component tests passed, still unattached; channel identification and mounted mechanical limits need calibration |
| Ultrasonic sensor | HC-SR04 with two 10 kOhm divider resistors; user reports test passed; integrated visitor detection implemented |
| Speaker / audio interface | USB CD002AUDIO detected and heard; integrated eSpeak/ALSA playback implemented |

Calibration passed the bench test's limits and is loaded by `guidebot.robot`.
The interface uses generous touch targets; verify them physically in the combined test.

## Next verification

Run the combined acceptance checklist in [ROBOT_RUNTIME.md](ROBOT_RUNTIME.md).
Verify face/touch/audio together first, then enable unloaded bench motion.
Calibrate the four limbs after mounting before adding physical gestures.

This plan does not change the robot's campus-assistant purpose or authorize
unverified campus routes. It records the requested interface revision and
the implementation limits above.
