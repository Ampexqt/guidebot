# Orange Pi One deployment — terminal simulation only

For the new **physical robot** entry point, dependencies, GitHub clone/pull commands and combined acceptance checks, use [ROBOT_RUNTIME.md](ROBOT_RUNTIME.md). This older page describes only `python -m guidebot --headless`, which remains a simulation. Its historical hardware status and test counts below predate the integrated program.

The intended transfer is Windows laptop → GitHub over HTTPS → Orange Pi over its own Ethernet connection. Commands below run locally on the named device; none requires laptop-to-board SSH. GitHub publication and real Orange Pi execution have not been performed by this review.

## 1. Publish from Windows when ready

Follow [GITHUB.md](GITHUB.md). The Orange Pi can clone only after a repository has been published. Replace `YOUR_USERNAME` in the following URL with the actual repository owner. If you choose another repository name, update that too.

## 2. First clone on the Orange Pi

Use the board's existing local terminal/console. These are instructions for you to execute on Armbian; the assistant has not run them on the board.

```bash
python3.13 --version
git --version
```

If `git` is not installed, install it with Armbian's package manager:

```bash
sudo apt update
sudo apt install git
```

Clone using the board's Ethernet internet access:

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/guidebot.git guidebot
cd ~/guidebot
python3.13 -m guidebot --validate-data
python3.13 -m guidebot --headless
```

If the Python executable is named `python3`, confirm it reports Python 3.13, then replace `python3.13` with `python3` in all commands. Do not replace the operating system's Python executable or change system symlinks for this project.

For private repositories, authenticate separately on the board using a supported GitHub HTTPS method. Keep credentials out of source files, clone URLs, shell scripts, and committed configuration. See [GitHub authentication guidance](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github).

## 3. Choose a headless mode

Interactive terminal:

```bash
python3.13 -m guidebot --headless
```

One JSON snapshot; useful for startup validation:

```bash
python3.13 -m guidebot --headless --once
```

Ten snapshots, one second apart, then exit:

```bash
python3.13 -m guidebot --headless --steps 10 --interval 1
```

Continuous telemetry at one snapshot per second; stop with Ctrl+C:

```bash
python3.13 -m guidebot --headless --monitor --interval 1
```

The headless frontend shares the database and controller with the Windows GUI. It can search destinations, show route steps, request simulated gestures, and report simulated distance and servo angles. It does not import Tkinter or any real hardware driver. It has no physical LCD output and no graphical face; those remain desktop preview features until a real display backend is implemented.

It starts no web service or application worker threads. Monitor output is streamed rather than accumulated. These implementation choices reduce overhead, but actual RAM use, CPU usage, temperature, and reliability on the 512 MB board have not been measured.

## 4. Optional virtual environment

Because there are no third-party dependencies, running directly with the existing Python 3.13 is sufficient. If that Python installation supports `venv`, you can isolate the project:

```bash
cd ~/guidebot
python3.13 -m venv .venv
.venv/bin/python --version
.venv/bin/python -m pip install --disable-pip-version-check -r requirements-headless.txt
.venv/bin/python -m guidebot --headless
```

The requirements file installs no packages. If creating the environment fails because the Python installation lacks `ensurepip` or `venv`, use the direct `python3.13` commands above. A venv package must match how Python was installed; package availability depends on your Armbian repositories. No pip installation into system Python is needed for GuideBot.

Do not copy the laptop's `.venv` onto Linux. The board creates its own environment, and `.venv` is ignored by Git.

## 5. Validate on the board without a desktop

```bash
cd ~/guidebot
python3.13 -m guidebot --validate-data
GUIDEBOT_SKIP_GUI=1 python3.13 -m unittest discover -s tests -v
python3.13 -m guidebot --headless --steps 3 --interval 1
python3.13 -m guidebot.diagnostics --json
```

With the current suite, headless testing should report 64 tests total, with 11 GUI tests skipped and 53 tests executed. These are expected counts; compare them with your actual output. A skip is not a pass. The Linux diagnostic tests use filesystem fixtures and do not prove the board's hardware is working.

The passive diagnostic examines Linux metadata for I²C adapters, SPI controllers and devices, and `/dev/i2c-*` and `/dev/spidev*` nodes. It uses `stat` and permission checks, but never opens these nodes. It does not run address probes, load modules, select bus numbers, edit overlays, or access GPIO.

Exit code 0 from the diagnostic means the inventory completed, including on unsupported platforms where a clear note is printed. It does not mean an interface or peripheral was found. A Linux metadata read/permission failure produces exit code 1. Missing interfaces produce explanatory notes. Do not infer GPIO pin assignments or attached chip identities from this report.

Linux interface references: [I²C userspace interface](https://docs.kernel.org/i2c/dev-interface.html), [SPI userspace interface](https://docs.kernel.org/spi/spidev.html).

## 6. Pull later updates

Stop the running simulator with Ctrl+C. After the laptop has pushed an approved update:

```bash
cd ~/guidebot
git status --short
git pull --ff-only
python3.13 -m guidebot --validate-data
GUIDEBOT_SKIP_GUI=1 python3.13 -m unittest discover -s tests -v
python3.13 -m guidebot --headless
```

If `git status` shows local edits, preserve and review those changes before pulling. `--ff-only` refuses divergent history rather than creating an unexpected merge. The board never needs direct access to the laptop.

## 7. Logs and hardware boundaries

The Linux default log is `~/.local/share/GuideBot/logs/guidebot.log`. Read it with:

```bash
tail -n 60 ~/.local/share/GuideBot/logs/guidebot.log
```

Set a project-local log path if desired:

```bash
python3.13 -m guidebot --headless --log-file ./logs/guidebot.log
```

PCA9685, HC-SR04, SPI LCD, touchscreen input, servo calibration, and GPIO mappings remain unimplemented and disabled. The hardware diagnostic does not change that. See [ARCHITECTURE.md](ARCHITECTURE.md) for the later integration stages.
