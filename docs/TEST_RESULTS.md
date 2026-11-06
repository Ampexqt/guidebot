# Project review and validation results

## October 29, 2026: TFT/touch bench tools and design notes

On the Windows laptop, Python 3.14.6 ran:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m unittest discover -s tools -p test_tft_touch_calibrate.py -v
```

The main suite passed all 64 tests, including 11 GUI tests, with no failures or
skips. The separate calibration suite passed six tests covering reversed axes,
rotation/skew, small ADC noise, unusable samples, and the saved calibration's
numerical consistency. Hardware modules are imported only when the diagnostic
runs, so these software checks require no GPIO hardware or Linux dependencies.

Physical evidence from the user's Orange Pi bench session: the screen displayed
the color sequence, touch readings changed with position and detected release,
and the displayed-target calibration produced the checked-in
`tools/tft_touch_calibration.json`. Independently recalculating that JSON gives
RMS fit error 5.949 pixels, maximum fit error 7.244 pixels, and independent
verification errors 5.635, 10.472, and 13.150 pixels. These passed the tool's
thresholds. This is a record of the user's physical test and the JSON review,
not a claim that Windows automated tests exercised the physical devices.

The main application still uses simulated hardware. The face/voice design is
documented, not implemented; speech, ultrasonic integration, and servo movement
remain pending. The older review below is retained as historical context.

Date: October 23, 2026.

Environment: Windows laptop. The main interpreter is Python 3.14.6 with Tcl/Tk 8.6.15. An isolated Python 3.13.16 runtime was also downloaded into the Git-ignored `.tools/python` directory for actual compatibility testing. The default laptop Python was not changed. This review did not access the Orange Pi.

## Final automated run

Command from the project root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

Actual result:

```text
Ran 64 tests in 4.078s
OK
```

64 passed, 0 failed, 0 skipped on Python 3.14.6. Eleven tests created real Tk windows and exercised actual widgets, rendering, and the event loop. The other 53 tested the database, controller, simulated devices, disabled hardware entry points, terminal frontend, passive interface inventory, source grammar, and CLI.

Actual Python 3.13 command:

```powershell
& '.\.tools\python\cpython-3.13.16-windows-x86_64-none\python.exe' -m unittest discover -s tests -q
```

Actual result:

```text
Ran 64 tests in 3.216s
OK
```

64 passed, 0 failed, 0 skipped on Python 3.13.16, including all 11 GUI tests. This verifies the tested code on Windows x86-64 Python 3.13, not Linux/ARM or the Orange Pi's particular Python build. A grammar test also parses every project Python source using Python 3.13 syntax rules. Runtime tests are stronger evidence than that syntax-only check.

A temporary copy containing only the 35 Git-eligible project files, without `.venv`, `.tools`, logs, or bytecode, was tested with `GUIDEBOT_SKIP_GUI=1`:

```text
Ran 64 tests in 0.505s
OK (skipped=11)
```

That run executed 53 passing tests and deliberately skipped 11 GUI tests. It validates a clean publishable copy on Windows; it is not an Armbian test.

## Findings fixed during review

- The original suite had a timing-dependent canvas item-count assertion: blinking removes highlight shapes, so a valid frame could fail the test. Robot eyes/head now have explicit canvas tags, and tests verify the eye geometry, blink, gaze, expression color, and head movement directly.
- A failed pointing gesture could prevent the UI from rendering an otherwise valid route. The controller now preserves route access and records the motion error.
- Home now clears a whitespace-only search field as well as normal queries.
- Terminal-only startup and passive I2C/SPI diagnostics were added without replacing the working GUI or activating real drivers.

Coverage includes:

- Four required sample destinations and placeholder labeling.
- Case-insensitive, keyword, alias, multiword, and empty-result searches.
- Missing files, malformed JSON, invalid fields, invalid schema, and duplicate IDs.
- Welcome/menu/directions transitions, route-step bounds, Back, Home, search preservation, and new-route reset.
- All five gesture actions, interpolation, interruption, angle bounds, return to neutral, and shutdown.
- Automatic and exact manual sensor readings, invalid readings, visitor detection, hysteresis, and greeting cooldown.
- Sensor error recovery and navigation continuing through simulated device failures.
- Real-driver placeholder constructors rejecting activation.
- GUI buttons, search, no-match handling, clickable LCD preview, manual slider, telemetry updates, and handled action errors.
- Tk event-loop animation, timer cancellation, and idempotent shutdown.
- Minimum 960×700 layout, including checks against containing panels to catch clipped controls; status-tab readings also fit.
- CLI validation success, missing-database exit code, and log-file creation.
- Headless terminal search, routes, navigation, every gesture, distance control, bad-input recovery, and EOF handling.
- JSON snapshots, bounded and continuous monitor behavior, Ctrl+C, and cleanup after a broken output pipe.
- A separate headless subprocess that rejects any Tkinter or real-hardware-driver import, proving those dependencies are unnecessary in that mode.
- Linux metadata fixtures for I2C adapters, SPI controllers/devices, node metadata, missing interfaces, deduplication, permission errors, and diagnostic JSON/exit codes. A guard verifies device nodes are never opened.
- Invalid headless CLI combinations and interval/step validation.

Additional successful checks:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --disable-pip-version-check -r requirements.txt
.\.venv\Scripts\python.exe -m guidebot --validate-data
.\.venv\Scripts\python.exe -m compileall -q guidebot tests run_guidebot.py
```

Database validation reported `Validated 4 destinations. Placeholder data: True.` The requirements step installed no third-party packages. Source compilation completed without errors.

Both interpreters compiled the source without errors. Python 3.13 also ran `--headless --once` successfully. Python 3.14 ran a three-snapshot monitor successfully. Installing `requirements-headless.txt` completed without installing third-party packages.

On Windows, `python -m guidebot.diagnostics --json` correctly reported `supported: false` and no Linux interfaces. This is an unsupported-platform check, not a physical bus test.

## GitHub preparation checks

A local repository was initialized on `main`. `git add --dry-run` selected 35 project files and excluded generated directories. `git check-ignore` confirmed `.venv`, `.tools`, `.env`, log paths, and a representative credentials filename are ignored. A pattern scan of all 35 candidate files found zero private-key, credential-URL, or common token/secret-assignment findings. Pattern scans are a check, not a guarantee against every possible secret.

There are no staged/tracked files, commits, or remotes. No GitHub repository was created and nothing was pushed. A clean checkout simulation confirmed that ignored local folders are not runtime dependencies.

## Scope and limits

The desktop application was relaunched from `.venv` for visual inspection. The existing minimum-window layout regression tests passed.

Final visual inspection confirmed the welcome screen and four menu entries. Typing `counseling` found Guidance Office; pressing Enter opened its placeholder route. Clicking Next in the LCD preview advanced both displays to step 2. The Device status tab showed four servo angles and changing synthetic distance. Clicking Wave showed a happy expression and the right-arm angle changing from 90 degrees. The application is left running for local use.

Automated GUI tests verify widget behavior and layout bounds, rather than pixel-perfect visual comparisons. This is not an exhaustive accessibility, long-duration performance, multi-monitor, or Windows DPI-configuration test. Arbitrarily long replacement route text and large custom databases have not been visually verified on the 240×320 preview.

Armbian execution, Linux permissions on the actual board, ARM-specific behavior, memory consumption within 512 MB, sustained CPU load, and real I2C/SPI availability remain untested. The documented clone/pull commands have not been executed against GitHub because publication awaits the user's decision. Tests using Linux-shaped fixture directories do not establish hardware availability.

No Orange Pi connection, PCA9685 output, servo motion, HC-SR04 measurement, SPI LCD rendering, or physical touchscreen behavior has been tested. Future real drivers are disabled and are not implemented. The preview is a Tkinter simulation, and all campus directions are fictional placeholders.

# November 6 integrated hardware frontend update

The original review above remains a historical simulator baseline. The new
`guidebot.robot` entry point was validated on Windows: the original 64
application checks and 14 new runtime checks passed (78 total), plus 26
standalone calibration/servo/ultrasonic checks. New coverage includes arrival
hysteresis/dropouts, menu/Repeat/speech behavior, serial motor timing, stale
sensor readings, child-process failures and cleanup after partial startup.
Four TFT layouts were rendered with bundled Pillow 13, visually inspected and
checked at each enabled button center. CLI help, calibration/data validation
and diff whitespace checks passed. These checks do not prove simultaneous
hardware operation: the user reports individual component tests passed, and
the combined Orange Pi acceptance check in [ROBOT_RUNTIME.md](ROBOT_RUNTIME.md)
is still required. No mounted motion calibration or real campus routes exist yet.
