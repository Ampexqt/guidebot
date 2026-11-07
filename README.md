# GuideBot — campus assistant and Orange Pi robot

A Python campus information assistant with a Windows Tkinter simulator, a terminal simulation, and a separate integrated Orange Pi hardware program. The existing simulator modes keep using simulated hardware.

**Physical robot:** see [setup and GitHub deployment](docs/ROBOT_RUNTIME.md) for `python3 -m guidebot.robot`. It combines the tested TFT/touch screen, USB speech, HC-SR04 visitor detection, and optional unloaded PCA9685 servo motions. The four motors are two hands and two feet, with no head or neck. Individual component tests have passed according to the user; combined operation on the Pi remains to be verified.

Development happens on the Windows laptop with Python 3.14. Project updates can use **laptop → GitHub → Orange Pi**, with the board independently cloning or pulling through Ethernet. Direct SSH/SCP is also used for physical bench testing. The application itself runs offline after transfer.

The included Library, Registrar, Computer Laboratory, and Guidance Office routes are **fictional placeholders**. They must not be used to navigate a real campus.

## 1. Start on Windows

Python 3.13 and 3.14 are supported targets. The desktop simulator also needs Tcl/Tk and otherwise uses only the Python standard library. The physical frontend needs the Debian packages listed in [the runtime guide](docs/ROBOT_RUNTIME.md). The compatibility review ran on **Python 3.14.6 and Python 3.13.16 on Windows**; this is not a test of Armbian, ARM, or physical devices. See [test results](docs/TEST_RESULTS.md).

Open your IDE terminal as PowerShell and run:

```powershell
Set-Location 'D:\GuideBot humanoid campus information assistant'
py -m tkinter
```

A small Tk demonstration window should appear. Close it before continuing.

Create a local Python environment:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --disable-pip-version-check -r requirements.txt
```

The requirements file contains no third-party packages, so there is nothing to download. The pip command is included as the dependency setup step; it can be omitted. No environment activation or PowerShell execution-policy change is needed.

Validate the campus database, run the tests, and launch GuideBot:

```powershell
.\.venv\Scripts\python.exe -m guidebot --validate-data
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m guidebot
```

For a quick launch with your existing Python instead of a virtual environment:

```powershell
Set-Location 'D:\GuideBot humanoid campus information assistant'
py -m guidebot
```

If `py` is unavailable but `python --version` works, replace `py` with `python` in these commands. In your IDE, choose `.venv\Scripts\python.exe` as the interpreter and run `run_guidebot.py`. Run the launcher from the project root; do not run individual files inside `guidebot` directly.

If you have several installed Python versions, use `py -3.14 -m venv .venv` to select your laptop's version explicitly. The isolated `.tools/python` interpreter used for the compatibility review is optional, ignored by Git, and not required to run the project.

## 2. What appears on screen

The dark blue desktop window contains:

1. A **SIMULATION / NO HARDWARE** badge and a prominent placeholder-data notice.
2. A robot with moving eyes, periodic blinking, changing expressions, a moving head, and animated arms.
3. The welcome message **Hello! I'm GuideBot!** and a **Find a destination** button.
4. A searchable campus menu. Search names or keywords such as `books`, `records`, `ICT`, or `counseling`. Select a result and click **Show directions**, double-click it, or press Enter. Enter in the search box opens the first match.
5. A directions screen that displays one route step at a time. **Previous step** and **Next step** stop at the route boundaries. The starting point is always the fictional kiosk; this simulator does not track the visitor's location.
6. **Back** and **Home** buttons. Back from a route restores your search. Home clears the route and search. Escape and Alt+Left go back; Ctrl+Home returns home.
7. **Wave**, **Nod**, **Look around**, **Point**, and **Reset pose** controls. Reset pose smoothly interrupts the current simulated gesture and returns all four logical angles to 90°.
8. A changing simulated ultrasonic distance. Turn off **Automatic distance** to use the 2–200 cm slider. The sensor simulator itself supports 2–400 cm through its Python interface. Below 45 cm, a visitor entering the greeting zone on the welcome screen triggers a wave. The visitor leaves the zone at 50 cm; greetings have an eight-second cooldown.
9. A right-hand **LCD preview** tab with a clickable **240×320 logical pixel** view. Its destination, step, Back, and Home buttons control the same application. Search is entered through the desktop search box. Windows DPI scaling may enlarge the preview physically on screen.
10. A **Device status** tab showing robot state, sensor distance, head pan, head tilt, left arm, and right arm angles. A short state/distance summary remains visible below the tabs.

The face becomes happy for waves and nods, focused while giving directions, curious near a visitor, and concerned if a simulated device reports an error. Motions run through the Tk event loop and do not pause navigation.

The window supports a minimum size of 960×700 logical pixels. The face area becomes shorter in smaller windows to keep navigation controls accessible. On heavily scaled displays, maximize the window if needed.

## 3. Project structure

```text
GuideBot humanoid campus information assistant/
├── run_guidebot.py             IDE-friendly launcher
├── requirements.txt           Standard library only
├── requirements-headless.txt  Terminal mode; no Tk dependency
├── README.md                  Windows setup and usage
├── guidebot/
│   ├── __main__.py            Command-line entry point
│   ├── app.py                 Tkinter window and event loop
│   ├── controller.py          Navigation, robot state, and behavior
│   ├── headless.py            Terminal commands and JSON monitor
│   ├── diagnostics.py         Passive Linux interface inventory
│   ├── database.py            JSON validation and search
│   ├── logging_setup.py       Rotating file and console logs
│   ├── data/campus.json       Fictional sample campus routes
│   ├── hardware/
│   │   ├── interfaces.py      Servo, distance, and display contracts
│   │   ├── simulated.py       Working simulated devices
│   │   └── future.py          Disabled real-driver placeholders
│   └── ui/
│       ├── face.py            Shared animated robot drawing
│       └── preview.py         Clickable 240×320 LCD preview
├── tests/                     Unit and real Tk widget tests
└── docs/
    ├── ARCHITECTURE.md        Future Orange Pi integration plan
    ├── DEPLOYMENT.md          Orange Pi setup and headless commands
    ├── GITHUB.md              Manual publishing and transfer workflow
    └── TEST_RESULTS.md        Actual validation results and limits
```

## 4. Edit or replace campus data

Edit `guidebot/data/campus.json` in your IDE. Each destination has a unique `id`, display `name`, `category`, `aliases` list, `description`, and a nonempty `steps` list. Use JSON double quotes, with no comments or trailing commas.

Keep `is_placeholder` set to `true` while the information is fictional. Update the campus name, starting point, notice, and route text together when campus staff provide verified information. The notice is always displayed. Restart GuideBot after editing; it does not watch the file for changes.

Validate before launching:

```powershell
.\.venv\Scripts\python.exe -m guidebot --validate-data
```

To load a different local database:

```powershell
.\.venv\Scripts\python.exe -m guidebot --database 'D:\My Campus Data\campus.json'
```

The default database path is resolved relative to the package, not the terminal's working directory. A missing or invalid database produces a clear terminal error and exit code 2. Missing Tkinter or an unusable graphical display produces exit code 3 with a headless-mode suggestion. Other startup failures produce exit code 1 and a traceback in the log.

## 5. Logs and troubleshooting

On Windows, the default log is:

```text
%LOCALAPPDATA%\GuideBot\logs\guidebot.log
```

Logs rotate at approximately 500 KB, keeping three backups. Console logging remains active if a file cannot be created. To use a log within the project:

```powershell
.\.venv\Scripts\python.exe -m guidebot --log-file '.\logs\guidebot.log'
```

Read the last 60 lines of the default Windows log:

```powershell
Get-Content -LiteralPath "$env:LOCALAPPDATA\GuideBot\logs\guidebot.log" -Tail 60
```

| Symptom | What to do |
| --- | --- |
| `py` is not recognized | Try `python --version`, then use `python` instead of `py`. |
| `No module named guidebot` | Run `Set-Location` to the project folder, or run `run_guidebot.py` with your IDE. |
| `No module named tkinter` / `_tkinter` | Repair or modify your Python installation to include Tcl/Tk support. Tkinter is not installed with `pip install tkinter`. Verify with `py -m tkinter`, then recreate the virtual environment if needed. |
| `.venv\Scripts\python.exe` does not exist | Run `py -m venv .venv` from the project folder. |
| Invalid JSON error | Check double quotes and commas, then run `--validate-data`. The error includes the filename and, for JSON syntax failures, line/column details. |
| The slider does not move | Uncheck **Automatic distance**. |
| A search finds nothing | Clear the search box or try a destination name. |
| Servo angles are not visible | Select the **Device status** tab beside **LCD preview**. |
| An action or simulated device fails | Read the message in the window and the log. Navigation remains available for handled device errors. Reset pose can clear a recovered motion error. |
| Some tests are skipped | Read the skip reason. GUI tests explicitly skip if Tkinter or a usable graphical display is unavailable. Skipped tests have not passed. |

For help fixing a problem, send the complete terminal error or a screenshot of the GuideBot window, plus the command you ran. The log tail is also useful. No Orange Pi access is needed to debug this phase.

## 6. Run without a desktop: Orange Pi or Windows terminal

The board has only 512 MB RAM, so start with the terminal frontend. It imports no Tkinter, creates no window or framebuffer, starts no web server, and uses one process with no application worker threads. JSON monitoring streams snapshots without retaining a growing history. Actual Orange Pi RAM use and performance have **not** been measured.

After cloning the project, run these commands **on the Orange Pi's own terminal**:

```bash
cd ~/guidebot
python3.13 --version
python3.13 -m guidebot --validate-data
python3.13 -m guidebot --headless
```

If its executable is named `python3`, first verify `python3 --version` reports 3.13, then substitute `python3`. There are no third-party packages to install and no requirement for Tkinter in this mode.

Try these terminal commands:

```text
list
search books
go library
next
previous
back
home
gesture wave
tick 2
distance 30
status
distance auto
quit
```

`go` accepts a destination **ID**, shown by `list`. Simulation updates when terminal commands are entered; it does not animate continuously while waiting for input. `tick` advances simulation time explicitly. The terminal shows the current route instruction and JSON telemetry, rather than a graphical face or LCD preview.

For unattended operation without interactive input:

```bash
python3.13 -m guidebot --headless --once
python3.13 -m guidebot --headless --steps 10 --interval 1
python3.13 -m guidebot --headless --monitor --interval 1
```

`--once` emits one JSON snapshot and exits. `--steps 10` emits ten snapshots, one second apart. `--monitor` continues until Ctrl+C. The interval may be 0.1–60 seconds. Log messages go to stderr; JSON snapshots go to stdout. These modes still use simulated servos and distance readings.

Use the same flags on Windows with `.\.venv\Scripts\python.exe` in place of `python3.13`.

See [Orange Pi deployment](docs/DEPLOYMENT.md) for first clone, updates, optional virtual environments, and headless testing.

## 7. Passive Orange Pi interface diagnostic

```bash
cd ~/guidebot
python3.13 -m guidebot.diagnostics --json
```

This script lists visible I²C adapters, SPI controllers, SPI devices, and userspace device-node metadata. It reads directory entries and sysfs labels; it does **not** open device nodes, scan bus addresses, change configuration, or send commands to motors. It needs no third-party modules or `sudo`. On Windows it reports that Linux interface detection is unsupported.

Missing nodes do not prove the board lacks an interface, and visible nodes do not prove a PCA9685 or LCD is connected or working. The diagnostic follows the Linux kernel's documented [I²C interface](https://docs.kernel.org/i2c/dev-interface.html) and [SPI interface](https://docs.kernel.org/spi/spidev.html) naming conventions.

## 8. GitHub publishing and code transfer

The project repository is [Ampexqt/guidebot](https://github.com/Ampexqt/guidebot). Follow [the step-by-step GitHub guide](docs/GITHUB.md) for the code-transfer workflow. After reviewing local changes, commit and push the project sources; the Orange Pi can independently pull updates.

`.gitignore` excludes virtual environments, the downloaded test interpreter, bytecode, logs, local editor files, `.env` files, common private-key formats, and common credentials filenames. Both devices create their own environment if needed; do not transfer `.venv` between Windows and Linux.

## 9. Physical TFT and touch bench test

The standalone [TFT/touch calibration tool](tools/TFT_TOUCH_TEST.md) was exercised on the robot's Orange Pi One and 240x320 SPI screen. It displays calibration targets, reads the separate touch connections, verifies the mapping, and saves calibration JSON. It uses Linux SPI/GPIO and has additional Debian dependencies; it is separate from the simulator.

Run its software checks on Windows or Linux without connected hardware:

```sh
python -m unittest discover -s tools -p test_tft_touch_calibrate.py -v
```

The saved [bench calibration](tools/tft_touch_calibration.json) belongs to the tested screen and orientation. Recalibrate after changing the display orientation, touch wiring, or unit. The physical `guidebot.robot` frontend loads this mapping; the desktop simulator does not access the TFT.

## 10. Integrated physical robot

To start GuideBot automatically when the Orange Pi powers on, use the
[boot service setup](docs/ROBOT_RUNTIME.md#start-automatically-when-powered-on).
It runs the face, touch menu, speech and visitor sensor without logging in;
servo motion stays disabled.

The [physical runtime](docs/ROBOT_RUNTIME.md) implements an animated face and talking mouth, destination menu, **Repeat** and **Menu** buttons without subtitles, USB speech, and ultrasonic visitor greetings. Add `--bench-motion` only for the current unattached servos to enable small serialized movements and individual motor buttons.

The legacy future-driver placeholders still deliberately raise errors; the new physical entry point uses separate real adapters. The desktop and headless simulation stay unchanged. Follow the runtime guide for GitHub clone/pull deployment and the combined hardware acceptance check. Mounted limb calibration and verified real campus routes remain outstanding.
