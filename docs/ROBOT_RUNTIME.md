# Integrated Orange Pi hardware program

This adds a physical frontend alongside the existing Windows simulator. Run it from the repository root; it reuses the tested drivers under `tools/`, so clone the entire repository. It does not need a Linux desktop, internet speech service, or microphone.

## Current behavior

- Idle animated face; a visitor closer than 45 cm triggers a spoken welcome. A valid reading of 50 cm or farther re-arms arrival detection, with a 15-second greeting cooldown. Missing readings do not trigger greetings. An orange dot and console message indicate a sensor problem; touch navigation remains usable.
- Tap the face to open large destination buttons. Selecting one speaks its route, returns to the face, and animates the mouth during playback. Menu stops playback. Repeat replays the previous message and is disabled during speech. No spoken-text subtitles appear on the face.
- The menu's Motors button opens four individual motor controls. By default they are disabled. `--bench-motion` enables only the previously tested small pulses: 1500, 1400, 1500, 1600, 1500 microseconds, one second per step, then output off. Only one motor moves at a time. Arrival also requests channel 0; destination selection requests channel 1. Requests during an existing movement are ignored.
- Channel plan: 0 left hand, 1 right hand, 2 left foot, 3 right foot. These are proposed identities until the motors are mounted. No head or neck motor is assumed. This program does not implement walking or balance.
- Ctrl+C, SIGTERM, and application errors attempt speech shutdown, worker shutdown, GPIO release, and PCA output disable when bench motion is enabled. Software cannot guarantee output shutdown after power loss or an I2C failure; disconnect servo power if needed.

The user reports that the individual display, touch, speaker, ultrasonic sensor and servos passed their tests. **Combined execution still needs verification on the Orange Pi.** Servos are currently unattached. Do not use `--bench-motion` after attaching limbs until their centers, directions, movement limits and mechanical clearance are calibrated. Motor power must remain separate from the 3.3 V logic supply; see [combined wiring](COMBINED_WIRING.md).

The bundled campus routes are fictional. The screen says DEMO and spoken routes include a demo warning. Replace `guidebot/data/campus.json` with verified names and directions from the robot's actual starting position, then set `is_placeholder` to false. Do not present the current routes as real visitor guidance.

## First deployment

First push this update from the laptop after reviewing it. No push is performed by the runtime.

On **Windows PowerShell**, from your project folder:

```powershell
cd "D:\GuideBot humanoid campus information assistant"
git status --short
git add guidebot/robot.py guidebot/robot_devices.py tests/test_robot.py tools docs README.md
git diff --cached --stat
git commit -m "Add integrated Orange Pi robot runtime and hardware guides"
git push origin main
```

The staging command includes the earlier standalone hardware tests and wiring notes. Review the staged files before committing. If Git reports nothing to commit, inspect `git log -1` and `git status` before deciding whether a push is needed.

On the **Orange Pi terminal** (or laptop SSH session showing `recursia@orangepione`):

```bash
sudo apt update
sudo apt install -y git python3-spidev python3-libgpiod python3-pil python3-smbus alsa-utils espeak-ng fonts-dejavu-core
cd ~
git clone https://github.com/Ampexqt/guidebot.git guidebot
cd ~/guidebot
python3 -m guidebot.robot --check
sudo python3 -m guidebot.robot
```

If `~/guidebot` already exists, use the update commands below instead of cloning again. Use the system Python with Debian's installed hardware libraries; a normal isolated venv will not see them. The tested libgpiod version is 2.2.1. The default ALSA device is `plughw:CARD=CD002AUDIO,DEV=0`; use `--audio-device` if `aplay -l` shows a different card name. Do not run other display, touch, ultrasonic or servo scripts at the same time.

The first run leaves PCA outputs untouched. Start it after stopping the standalone tests, which disable their outputs. Press Ctrl+C, then, with **unattached servos and a confirmed compatible power supply**, run:

```bash
sudo python3 -m guidebot.robot --bench-motion
```

No extra Orange Pi wiring changes are required for the documented working pin map. This entry point uses SPI0.0, GPIO chip0 with the H3 label, I2C0/address0x40, the checked-in touch calibration, and the existing separate touch GPIO lines. Keep the HC-SR04 Echo voltage divider fitted.

## Later updates

Push laptop changes first. Stop the robot with Ctrl+C before pulling on the Pi:

```bash
cd ~/guidebot
git status --short
git pull --ff-only
python3 -m guidebot.robot --check
sudo python3 -m guidebot.robot --bench-motion
```

Preserve local edits before pulling; do not use a forced reset. Keep machine-specific calibration or campus data outside the checkout if they should survive updates, for example `~/guidebot-config/`, and select them using `--calibration /home/recursia/guidebot-config/touch.json` and `--database /home/recursia/guidebot-config/campus.json`. Do not commit passwords or copy the Windows `.venv` to Linux. Automatic boot startup is deferred until combined operation passes.

## Combined acceptance check

1. Start without bench motion: confirm the idle face and a tap opens the destination menu.
2. Select every destination: verify audible speech, mouth animation, Menu interruption, and Repeat after playback. Confirm the demo warning is heard.
3. Move a flat target near then far from the ultrasonic sensor. Check welcome, hysteresis and cooldown. Keep a target still nearby: it should not repeat continuously.
4. Stop, restart with `--bench-motion`, and use Motors to test each of the four unattached motors. Confirm channel identity, no simultaneous commands and output release after each sequence. Test a welcome and route selection with motors enabled.
5. Stop with Ctrl+C and confirm audio stops and motor outputs release. Record actual results, power stability and any device errors before mounting or enabling startup on boot.

Windows checks can validate navigation, process failures, timing and cleanup logic without proving electrical operation. Run `python -m unittest discover -s tests -v`, plus the standalone suites described in their guides. `python -m guidebot.robot --preview face.png` renders the idle face without hardware if Pillow is installed.

Implementation references: [eSpeak NG command options](https://manpages.debian.org/trixie/espeak-ng/espeak-ng.1.en.html), [ALSA playback](https://manpages.debian.org/trixie/alsa-utils/aplay.1.en.html), [libgpiod line requests](https://libgpiod.readthedocs.io/en/master/python_line_request.html). Range GPIO requests belong exclusively to the sensor worker; they are not shared with the UI thread.
