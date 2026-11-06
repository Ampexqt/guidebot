# Orange Pi One TFT/touch calibration

Standalone bench diagnostic for the wiring tested in this chat. It does not
change the GuideBot app or drive a motor. It assumes a 240x320 ILI9341-compatible
display and an XPT2046/ADS7846-compatible resistive touch interface.

For simultaneous LCD, PCA9685, and proposed HC-SR04 connections, follow the
[combined wiring guide](../docs/COMBINED_WIRING.md). It replaces the direct LCD
LED-to-pin-1 connection below with a shared 3.3 V breadboard node; all tested
LCD/touch signal pins stay the same.

Turn off and unplug the board before changing wires. Header numbers below are
physical positions, not GPIO offsets. Find the board's pin-1 marking first.

| TFT label | Orange Pi One physical pin |
| --- | --- |
| VCC | 17 (3.3 V) |
| GND | 6 |
| CS | 24 (SPI0 CS0) |
| RESET | 18 (PC7) |
| DC | 22 (PA2) |
| SDI/MOSI | 19 (PC0) |
| SCK | 23 (PC2) |
| LED | 1 (3.3 V) |
| T_CLK | 11 (PA1) |
| T_CS | 15 (PA3) |
| T_DIN | 13 (PA0) |
| T_DO | 16 (PC4) |
| T_IRQ | 7 (PA6) |

Leave display SDO and the SD-card pins disconnected. Touch uses its own software
SPI connections. SPI0 must already appear as `/dev/spidev0.0`.

On Debian/Armbian, install `python3-spidev python3-libgpiod gpiod python3-pil`.
This script requires libgpiod 2.x, tested API target 2.2.1.

For the tested Armbian H3 setup, `/boot/armbianEnv.txt` includes these lines
(merge with existing overlays; do not duplicate settings or replace rootdev):

```text
overlay_prefix=sun8i-h3
overlays=i2c0 spi-spidev
param_spidev_spi_bus=0
```

Reboot after changing boot settings and confirm `ls /dev/spidev*` lists
`/dev/spidev0.0`. Install the diagnostic's dependencies separately from the
standard-library-only simulator:

```sh
sudo apt update
sudo apt install python3-spidev python3-libgpiod gpiod python3-pil
```

Run on the Orange Pi:

```sh
sudo python3 ~/tft_touch_calibrate.py
```

If running from a clone of this repository instead, use
`sudo python3 tools/tft_touch_calibrate.py` from its root. The resulting JSON is
saved beside the script. The checked-in JSON records this robot's passing bench
calibration. It is specific to the tested screen, orientation, and wiring;
calibrate another unit before using it.

Follow five crosshair targets on the TFT itself, regardless of its previous
physical orientation. Hold each gently for about one second, then release. The
program fits an affine mapping, checks fit error, and asks for three additional
verification taps. Verification must pass before it writes
`tft_touch_calibration.json` beside the script. An existing calibration is
preserved if fitting or verification fails. Fit thresholds (12 pixel RMS,
20 pixel maximum) and verification tolerance (20 pixels) are bench checks,
not a guarantee for small UI buttons.

After passing, a yellow dot follows touches. Press Ctrl+C to stop. Report any
error message, text orientation problem, or visible dot offset. The saved mapping
assumes this display orientation, the same touch wiring, and the raw-divisor
normalization stored in the JSON. It is not loaded into GuideBot automatically.

Local validation: run `python -m unittest discover -s tools -p test_tft_touch_calibrate.py`.
These checks cover mapping math, rotated/reversed axes, ADC noise, and singular
samples. They do not verify GPIO timing, wiring, or the physical display.

References:
- https://www.lcdwiki.com/res/MSP2402/2.4inch_SPI_Module_MSP2402_User_Manual_EN.pdf
- https://linux-sunxi.org/Xunlong_Orange_Pi_One_%26_Lite
- https://libgpiod.readthedocs.io/en/master/python_api.html
- https://github.com/adafruit/Adafruit_CircuitPython_RGB_Display/blob/main/adafruit_rgb_display/ili9341.py
