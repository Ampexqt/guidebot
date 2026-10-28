# GuideBot face, voice, and touch interface plan

Recorded: October 29, 2026

Status: design agreed in conversation; implementation is pending. This document
records the intended behavior, rather than claiming that the current app already
supports physical speech or the revised screen interface.

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

The four planned servos remain intended for head and arm gestures.

## Equipment and current progress

| Component | Intended role / current state |
| --- | --- |
| Orange Pi One running Armbian | Runs interface, speech, and robot behavior |
| 2.4-inch SPI TFT touchscreen | Face and destination menu; color and touch tests passed |
| Touch calibration | Saved in `tools/tft_touch_calibration.json`; RMS fit error about 5.95 pixels; three verification errors about 5.64, 10.47, and 13.15 pixels |
| PCA9685 | Servo controller; I2C communication previously detected at address 0x40 |
| Four SG90 servos | Planned gestures; movement testing pending suitable servo power |
| Ultrasonic sensor | Planned visitor detection; component testing pending |
| Speaker / audio interface | Required for spoken information; actual available audio equipment still needs identification |

Calibration passed the bench test's limits, but the saved mapping is not yet
integrated into GuideBot. Use generous touch targets and verify the final
interface physically before relying on small controls.

## Before implementation

Identify the actual speaker, its connection, and any amplifier or audio
interface required. Then implement the face and menu views, load the saved
touch calibration, add speech playback and Repeat, and connect mouth animation
to playback start and completion. Test these together before adding gestures
or automatic visitor greetings.

This plan does not change the robot's campus-assistant purpose or authorize
unverified campus routes. It records the requested interface revision for
future work.
