# GuideBot project notes

## November 6, 2026 — integrated hardware runtime

- User reports speaker, LCD/touch, ultrasonic and servo component tests work.
  Earlier pending component-test notes below are superseded by this report;
  no measured ultrasonic accuracy or integrated test log was provided.
- User confirmed all four servos remain **unattached on the table**. Added the
  separate `python3 -m guidebot.robot` frontend without changing the simulator.
- Implemented face/blink, playback-driven mouth, touch destinations, Repeat,
  Menu interruption, offline USB speech, background HC-SR04 detection with
  hysteresis/cooldown, and optional serialized PCA bench motions. Reused the
  working pin map and saved touch calibration. No head/neck or walking logic.
- Motor commands require `--bench-motion`; the same 1400-1600 us bench pulses
  are used. Mounted motions still require center/direction/limit calibration.
  Separate servo supply voltage compatibility remains a hardware requirement.
- Bundled campus information remains fictional, with a visible/spoken demo
  notice. Verified campus routes are required before visitor use.
- Added [hardware runtime and deployment instructions](ROBOT_RUNTIME.md),
  including laptop push, Pi clone/pull, dependencies and acceptance checklist.
  Code is local; this update has not been committed or pushed by the assistant.
- Initial verification: 76 application tests passed, including the original
  Tk tests and 12 new runtime behavior/device-failure checks; all 26 standalone
  hardware-tool tests passed. This validates software behavior on Windows,
  not physical combined operation. Two additional checks subsequently passed
  for complete runtime cleanup and display-open failure after opening motors.
  Final total: **78 application checks plus 26 standalone checks passed**.
  Four 240x320 layouts (idle, speaking, destinations, motors) were rendered
  with Pillow 13, visually inspected, and their enabled button centers checked.
  CLI help and config validation passed; `git diff --check` was clean.
- Next: deploy through GitHub; run combined acceptance
  checks on the Pi; verify channel identities and power stability; calibrate
  limbs after mounting; replace sample routes; only then consider boot startup.

## November 6, 2026 — mini breadboard, USB audio, and interactive servo test

- Ultrasonic follow-up: the user explicitly confirmed **HC-SR04 with VCC/TRIG/
  ECHO/GND and two 10 kOhm divider resistors fitted**. Added the standalone
  [ultrasonic test](../tools/ultrasonic_test.py) and
  [instructions](../tools/ULTRASONIC_TEST.md), using physical pins 29 (TRIG) and
  31 (divided Echo), controller offsets 7/8. It uses kernel edge timestamps,
  bounded waits, 20 default samples, and no motor commands. **Ten simulated
  checks passed** for timing conversion, missing/stale/noisy edges, stuck-high
  input, interruption cleanup, and range validation. Actual wiring and ruler /
  missing-echo bench results are still pending. No physical sensor pass or new
  application integration is claimed.

- User reported the LCD color test still works after moving the shared logic
  connections to a mini breadboard. The mini board requires remapped positions;
  the long board's A30/A35 ultrasonic placements do not apply literally. For the
  shared 3.3 V node, use three holes in one connected five-hole group only.
  Preserve the TFT/touch GPIO mapping. Obtain/check actual wiring before
  transferring additional divider/supply groups.
- The latest PCA9685 probe on GPIO I2C bus 0 returned **40 at address 0x40**.
  Communication passed; no physical motor movement pass has yet been reported.
- Current Orange Pi LAN address is **192.168.68.125**, replacing the earlier
  .110 address for this session; addresses can change.
- USB speaker description specifies one USB cable for audio and power with a
  built-in sound card. Armbian detected **CD002-AUDIO**, ALSA card identifier
  **CD002AUDIO**, device 0 (card index 1 during this session). User heard the
  successful Front Left/Front Right `speaker-test` playback. Explicit output
  selection used `plughw:CARD=CD002AUDIO,DEV=0`.
- `arecord -l` listed no capture hardware, so no usable microphone input is
  exposed by the current speaker. A microphone is optional for a future
  voice-input feature; the agreed touch-menu and spoken-output flow needs the
  speaker. USB microphone purchasing candidates were discussed, but no microphone
  purchase, detection, or test is confirmed.
- eSpeak NG greeting generation/playback commands were provided, including
  amplitude `-a 200` and the separate system-mixer check. Successful playback
  evidence is specifically the speaker channel test; custom greeting quality,
  mixer configuration, and face/mouth synchronization are not yet verified.
- Added [interactive servo sequence tool](../tools/servo_sequence_test.py) and
  [instructions](../tools/SERVO_SEQUENCE_TEST.md). It waits for Enter before each
  of channels 0-3, applies small center movements, disables each output, pauses
  two seconds, and waits for Enter again. Proposed names remain left hand,
  right hand, left foot, right foot; there are no head/neck motors.
- **Eight new simulated-I2C checks passed** for input gating, sequential output,
  delay behavior, quitting, Ctrl+C/EOF, external-clock rejection, and cleanup
  after I2C errors. This is software verification, not a physical servo pass.
  No full application-suite rerun is claimed for this addition.
- Follow-up from the actual board: Debian `python3-smbus` raised
  `TypeError: 'SMBus' object does not support the context manager protocol`
  before the original script could start the sequence. Fixed the entry point
  to explicitly open and close the bus with try/finally. Added two regression
  checks using a bus without context manager methods, including closure after
  an I2C error. The servo suite now has **10 passing software checks**. The
  corrected file must be recopied to the Orange Pi before retrying; no physical
  servo pass is inferred from this software repair.
- The servo supply compatibility and terminal polarity issue recorded November 4
  remains unresolved. The interactive script does not validate a battery pack
  or establish mechanical limits. Next: transfer the script, confirm compatible
  power/wiring, then report movement for each unloaded servo. Continue sensor
  identification/divider testing and audio/UI integration afterward.
- These updates are local and have not been committed or pushed in this turn.

## November 4, 2026 — combined wiring and corrected limb layout

Date uses Asia/Manila time. This entry supersedes the earlier assumption that
the physical robot has head-pan/head-tilt servos.

### Decisions and confirmed context

- **The physical robot has two hands and two feet, with no motorized head or
  neck.** Its four servos are for those four limbs. The face and moving mouth
  remain animations on the TFT.
- Proposed PCA9685 channel plan: **0 left hand, 1 right hand, 2 left foot,
  3 right foot**. This is a documentation proposal, not a confirmed existing
  assembly or a calibrated motion mapping. Identify each actual servo before
  connecting it to a limb.
- Keep the previously tested LCD/touch signal pins. Orange Pi pin 1 is already
  used for the LCD LED, pin 17 for LCD VCC, and pin 6 for LCD GND. The earlier
  instruction assigning pin 1 directly to PCA9685 VCC overlooked this conflict.
- The user has a breadboard and male/male and female/female jumper wires.
  Use a breadboard group to share 3.3 V instead of requiring a purchased splitter:
  **pin 1 → A1, LCD LED → B1, PCA9685 VCC → C1**. These holes must be on the same
  numbered row and same side of the center gap. LCD VCC remains on pin 17.
- PCA9685 logic: **GND → pin 9, SDA → pin 3, SCL → pin 5**. VCC stays at 3.3 V;
  servo V+ is a separate supply. Battery positive must not join the 3.3 V group.
- A single-pin 2.54 mm Dupont Y splitter, one female to two male ends, is an
  optional alternative compatible with the existing female/female jumpers.

### Supply and sensor issues still unresolved

- Photos show a four-AA holder and **R6 carbon batteries marked 1.5 V each**,
  making 6 V nominal together. The original suggestion was four 1.2 V NiMH AA
  cells, making 4.8 V nominal. The physical servos are labeled Tower Pro SG90;
  the later 4.8-6.0 V specification image pictured Smraza S51. That image alone
  does not establish the actual SG90 supply range.
- NiMH is one possible supply option, not the only option. Confirm the actual
  servo's supported range and measured pack voltage, or select an appropriate
  regulated supply. Fresh-cell voltage can differ from the nominal sum. Keep
  the battery holder empty during logic wiring checks. R6 carbon cells shown
  are not rechargeable.
- A later photo showed red/black leads inserted into the green power terminal,
  but its polarity markings were not readable. Positive-to-V+ and negative-to-GND
  still need physical confirmation. No servo movement has been reported.
- Proposed ultrasonic layout is conditional on an actual standard HC-SR04:
  VCC from pin 2 (5 V), GND from pin 14, TRIG pin 29 (PA7), divided Echo pin 31
  (PA8). Two 10 kOhm resistors provide the documented Echo divider. The sensor
  model, resistor availability, and this sensor wiring/test remain unconfirmed.
- Power-bank output capacity and the speaker/audio interface remain unconfirmed.
  Audio is required for spoken information and Repeat. The intended portable
  arrangement is power bank for the Orange Pi and a separate suitable servo
  supply, with a shared ground reference and separate positive supply rails.

### Changes and verification today

- Created [combined wiring guide](COMBINED_WIRING.md), including explicit
  breadboard holes, LCD/touch connections, PCA9685 logic, proposed limb channels,
  conditional HC-SR04 wiring/divider, and staged testing instructions.
- Updated [TFT test instructions](../tools/TFT_TOUCH_TEST.md) to point to the
  combined layout and explain the shared LED supply.
- Corrected the channel table and physical limb descriptions in the combined
  wiring guide and [face/voice plan](FACE_AND_VOICE_DESIGN.md). Added a note in
  [architecture](ARCHITECTURE.md) distinguishing the existing simulator's joint
  names from the user's actual four-limb mechanism.
- Documentation allocation check: **20 unique Orange Pi physical pin
  assignments**, with no duplicate header-pin assignment in the combined plan.
  Shared breadboard power is intentional. This checks the plan, not actual
  electrical continuity or assembled wiring.
- No new physical servo/ultrasonic pass result or automated application-suite
  run is claimed today. The previous **64 app + 6 calibration tests** and passing
  TFT/touch calibration remain the October 29 checkpoint.
- These November 4 documentation updates are saved locally; no new commit or
  GitHub push was performed for this notes request.

### Next steps

1. Confirm limb identity and mounting: two hands/two feet, proposed channel
   assignment, servo direction/center, and mechanical travel limits. Do not
   assume head/neck gesture poses are suitable for the feet or hands. Foot
   construction, load-bearing requirements, and walking behavior are not yet
   specified or validated.
2. Check the unpowered breadboard/Orange Pi/PCA9685 connections and battery
   terminal polarity with clear photos and, where available, a multimeter.
3. Power only the Orange Pi with the servo batteries removed; confirm the LCD
   still works, identify the GPIO I2C bus, and check PCA9685 communication at 0x40.
4. Resolve the servo supply. Then run a small unloaded movement test on one
   identified servo; test each remaining servo individually before combined
   motion or installation in the mechanism.
5. Identify the ultrasonic sensor and fit the correct Echo voltage protection
   before connecting its input to the Orange Pi; test distance and timeout.
6. Identify audio hardware and confirm power capacity. Later, revise software
   joint names/mappings for the actual limbs and implement the TFT face/menu,
   saved touch calibration, speech, and Repeat/Menu behavior. The application
   still uses simulated devices; no limb-driver change was made today.

## October 29, 2026 — hardware checks and face/voice design

Date uses Asia/Manila time. This entry summarizes the working session spanning
October 28–29, including earlier hardware checks carried forward in the chat.

### Decisions

- GuideBot remains a campus information assistant; retain the existing equipment
  plan rather than changing the robot's purpose.
- Use the 2.4-inch 240x320 SPI TFT for a cute animated face and a separate touch
  menu of campus destinations. A detailed campus map is not part of the initial
  menu design.
- Draw blinking eyes, expressions, and a talking mouth on the TFT. No mechanical
  mouth servo is planned. Initially, the mouth opens and closes while speech
  plays; following audio loudness more closely can come later.
- **No subtitles or speech captions.** Provide large on-screen **Repeat** and
  **Menu** buttons. Repeat replays the most recent information with mouth
  animation. Keep Repeat available after playback; disable it while speaking
  and before there is a message to repeat. Menu returns to destination choices.
- Intended flow: waiting face → visitor greeting when detection is implemented
  → tap to open destinations → select destination → spoken information with
  talking face → Repeat or Menu.
- At this point the four SG90 servos were assumed to provide head and arm
  gestures; the user's November 4 correction above supersedes that assumption
  with two hands/two feet and no motorized head or neck. Spoken information
  still requires identification of the actual speaker/audio setup.

Full specification: [face and voice design](FACE_AND_VOICE_DESIGN.md).

### Changes saved in the repository

- `tools/tft_touch_calibrate.py`: standalone Orange Pi display/touch calibration
  utility. Displays five crosshair targets, fits an affine mapping, checks three
  additional targets, then shows a touch-following yellow dot. Saves JSON only
  after successful verification.
- `tools/tft_touch_calibration.json`: the tested robot's actual calibration.
  Specific to this screen, display orientation, and touch wiring.
- `tools/test_tft_touch_calibrate.py`: six software checks, including validation
  of the saved calibration results.
- `tools/TFT_TOUCH_TEST.md`: physical wiring, SPI preparation, dependencies,
  usage, and test limitations.
- `docs/FACE_AND_VOICE_DESIGN.md`: the agreed design above.
- `README.md` and `docs/TEST_RESULTS.md`: updated entry points and verification
  records.

These tools do not yet integrate the physical TFT or saved touch mapping into
the main GuideBot app. Desktop/headless app hardware remains simulated. The
animated face/voice revision is a documented plan, not an implemented feature.

### Hardware and verification results

| Item | Result / evidence |
| --- | --- |
| Orange Pi and access | Armbian boots; SSH and SCP worked from the Windows laptop |
| PCA9685 | Earlier communication check responded at I2C address `0x40`; servo outputs/motion are not yet tested |
| SPI | `/dev/spidev0.0` appeared after restoring the H3 overlay prefix and enabling SPI |
| TFT display | User reported successful red, green, blue, black, and white transitions |
| Touch | User supplied changing raw coordinates and successful release detection |
| Displayed-target calibration | User completed the utility and copied its JSON to the laptop; JSON independently reviewed |
| Calibration fit | RMS **5.949 px**; maximum fit error **7.244 px** |
| Independent verification taps | **5.635 px**, **10.472 px**, **13.150 px** error; all below the utility's 20 px limit |
| Main automated suite | **64 passed**, including 11 GUI tests; no failures or skips on Windows Python 3.14.6 |
| Calibration software suite | **6 passed**; combined automated count **70 passed** |

The physical results above come from the user's bench session and calibration
file, while the automated suite ran on Windows. Use generous touch targets and
verify the final menu physically; passing the bench tolerance does not guarantee
small-button accuracy. Earlier unmarked-corner readings were approximate; use
the saved displayed-target calibration instead.

Working SPI settings in `/boot/armbianEnv.txt`:

```text
overlay_prefix=sun8i-h3
overlays=i2c0 spi-spidev
param_spidev_spi_bus=0
```

Keep each setting only once and preserve the board's other boot settings. The
working wiring table is in [TFT touch test instructions](../tools/TFT_TOUCH_TEST.md).

### GitHub checkpoint

Repository: [Ampexqt/guidebot](https://github.com/Ampexqt/guidebot), branch `main`.

Commit [7dba583](https://github.com/Ampexqt/guidebot/commit/7dba58352ae3be2e85611c9f3825f0dd31ebd9c0),
“Add TFT touch calibration tools and face voice design plan,” was pushed
successfully. The remote commit was checked against local HEAD, and the working
tree was clean immediately after that push. This notes entry was written after
that checkpoint.

### Next steps and unresolved items

1. Identify the available speaker: USB, powered 3.5 mm speaker, or bare speaker.
   Determine the needed audio interface/amplifier and its power requirements
   before implementing playback.
2. Continue individual hardware testing with the ultrasonic sensor. Obtain a
   clear model/pin-label photo and identify available resistors or a level
   shifter before specifying wiring. A 5 V Echo signal must not connect directly
   to a 3.3 V GPIO input.
3. Resolve servo power. The user currently has an Orange Pi power bank and
   jumper wires, with no confirmed servo V+ supply connection. Do not treat
   PCA9685 logic power or its illuminated LED as servo motor power. Check supply
   ratings and power distribution, then test one SG90 before the remaining
   three.
4. Implement the TFT face and destination menu, loading the saved calibration
   with its recorded display orientation. Keep the existing simulator usable.
5. Add speech playback, Repeat/Menu behavior, and mouth animation tied to
   playback start/completion. Verify repeated taps cannot overlap speech.
6. Integrate visitor detection and gestures after their component tests pass.
   Replace fictional campus routes with verified information before real use.

### Practical instructions to preserve

- The user benefits from short, numbered instructions and exact copyable
  commands, with one hardware step at a time.
- Run Linux commands such as `sudo python3 ...` after SSH login at the
  `recursia@orangepione:~$` prompt. Run SCP commands containing a Windows drive
  path in Windows Command Prompt/PowerShell. A prompt or an expected output line
  is not a command to type. Windows Sudo does not need enabling.
- Shut down and disconnect power before changing wiring. Do not repeatedly ask
  for `sudo poweroff` once shutdown is already confirmed.
- The board used `192.168.68.110` during testing; check its current address if
  connectivity changes. Command Prompt was used when PowerShell's PSReadLine
  input handler encountered a console-rendering exception.
