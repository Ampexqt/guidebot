# GuideBot project notes

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
- The four SG90 servos remain intended for head and arm gestures. Spoken
  information still requires identification of the actual speaker/audio setup.

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
