# GuideBot architecture and later integration

November 6 implementation: `guidebot.robot` now provides a separate physical frontend. `RobotSession` handles face/menu/Repeat and arrival policy; `robot_devices` manages asynchronous USB speech, a worker-owned HC-SR04 GPIO request, and timed bench motions. Display/touch and PCA primitives reuse the successful standalone tools. This leaves the legacy simulator controller and its head/arm labels unchanged. See [runtime guide](ROBOT_RUNTIME.md); the Phase 1 description below is historical. Combined hardware execution remains unverified.

November 4 physical-layout clarification: the user has **two hands and two
feet, with no motorized head or neck**. The simulator joint names and behavior
described below remain the existing software implementation, not the corrected
physical mapping. See [project notes](PROJECT_NOTES.md) and the
[combined wiring guide](COMBINED_WIRING.md) before implementing real limb drivers.
The TFT/touch bench tests have also progressed beyond the original Phase 1
status below; their results are recorded in [test results](TEST_RESULTS.md).

Phase 1 has a Windows graphical simulator and a terminal/JSON frontend suitable for headless deployment. Both use simulated devices. The Orange Pi, PCA9685 HW-570, four servos, HC-SR04, SPI TFT, and touchscreen have not been accessed or tested.

## Current data flow

```text
Tkinter UI and LCD preview OR headless terminal/JSON frontend
                       |
                RobotController
                 /     |      \
        CampusDatabase |       DistanceSensor interface
             |         |                  |
       local JSON  ServoDriver       SimulatedUltrasonic
                       |
                 SimulatedServos
                       |
          Tkinter face and status widgets
```

`database.py` validates all local route data before the GUI starts. `controller.py` owns page state, route step selection, visitor detection, error state, and gesture requests. It does not import Tkinter or a GPIO library.

`__main__.py` selects the frontend before importing Tkinter. `--headless` imports only the terminal module and simulated device implementations. Both frontends construct the same `RobotController`; the terminal does not emulate a graphical framebuffer. The terminal loop advances simulation on input, while JSON monitor mode updates at the selected low-frequency interval. Output is streamed without an accumulated history.

`diagnostics.py` is a separate passive inventory command. It reads Linux directory entries, sysfs labels, and device-node metadata, without opening bus nodes or importing drivers. Its fixture tests simulate Linux filesystems on Windows; actual Linux interface availability is not verified by those tests.

`app.py` composes the controller with `SimulatedServos` and `SimulatedUltrasonic`. A Tk `after` callback updates the simulation at approximately 30 frames per second. Elapsed time is capped at 0.1 seconds per GUI frame so dragging a window or pausing in a debugger does not cause a large jump. Device models also accept explicit elapsed times for deterministic tests. The preview and telemetry refresh less often than the face to reduce drawing work.

The four logical servos are `head_pan`, `head_tilt`, `left_arm`, and `right_arm`. The simulator starts at 90° and uses bounded 0–180° logical angles. **These values are illustrative simulator poses, not calibration values for physical mechanisms.** Keyframes interpolate without `sleep`, threads, or blocking motion loops. A new gesture replaces the old one from its current pose. Closing the app cancels its timer and closes each simulated device.

The deterministic automatic sensor uses time-varying synthetic readings. Manual mode uses the exact chosen value. Presence enters below 45 cm, exits at 50 cm, and triggers a welcome wave only on a new arrival at Home when the motion system is idle and the greeting cooldown has expired. Sensor failures clear the displayed distance and log the error. A recovered sensor clears its error on the next valid reading.

A pointing-gesture failure records a motion error while leaving a selected route and its step navigation available. Real-driver placeholder classes remain isolated in `hardware/future.py`, and neither runtime frontend imports them. No command-line option activates real hardware.

## Boundaries prepared for future drivers

The contracts in `guidebot/hardware/interfaces.py` are Python protocols. A concrete driver can satisfy a protocol without inheriting from it.

| Boundary | Contract | Later responsibility |
| --- | --- | --- |
| Servo | `angles`, `active_gesture`, `gesture(name)`, `update(dt)`, `close()` | Convert logical poses into calibrated per-channel hardware output; keep gesture scheduling nonblocking. |
| Distance | `update(dt)`, `read_cm()`, `close()` | Supply a recent bounded distance or raise an informative timeout/error. Blocking echo timing must stay outside the GUI callback. |
| Display | `present_rgb(pixels, width, height)`, `close()` | Accept an RGB888 frame and transfer it to the identified LCD controller with the correct orientation and pixel format. |

The display protocol is an interface only. The Phase 1 Canvas draws directly with Tkinter and does not generate RGB frames. A future framebuffer renderer must translate the same view state into 240×320 pixels. This rendering work, LCD communication, and touch input are not implemented yet.

The current `ui/preview.py` demonstrates screen content, page transitions, and touch-sized button regions at 240×320 logical pixels. Its callbacks call the same controller methods as the desktop UI. A future touch adapter should map calibrated screen coordinates to equivalent actions. Do not choose a touchscreen driver until the actual touch-controller model has been identified.

`hardware/future.py` contains explicitly disabled constructors for the real PCA9685, ultrasonic, and SPI display drivers. They are markers for future implementation, not operational drivers. There is no hardware-enabling command-line flag.

## Suggested next stages after the simulator is confirmed

1. Replace fictional campus routes with approved information and validate the JSON. Verify each route from the kiosk with campus staff.
2. Identify the LCD controller, touchscreen controller, board interfaces, and library compatibility on the actual Orange Pi One/Armbian image. Record those findings before choosing libraries or pin assignments.
3. Add an Orange Pi-specific composition entry point. Keep `python -m guidebot` as the Windows simulation entry point. Inject real devices only through that new entry point after they have independent checks.
4. Implement and bench-test the display renderer and touch mapping. Confirm the physical orientation, full 240×320 area, readable text, and calibrated button positions.
5. Implement ultrasonic measurement with a bounded timeout and a cached result. Use a worker or another suitable acquisition mechanism so a missing echo cannot freeze navigation. Add tests for timeout, stale readings, and recovery.
6. Implement the PCA9685 servo adapter with a shared nonblocking motion scheduler. Add explicit channel mapping, per-joint limits, center positions, direction inversion, and calibration configuration. Confirm the power arrangement and electrical compatibility for the selected components before connecting them. Begin with separately controlled joint checks and measured mechanical limits; simulator angles are not physical travel limits.
7. Define output behavior on driver failure, process exit, and power loss. Physical shutdown behavior must be chosen and tested for the actual mechanism rather than inferred from the simulator's `close()` method.
8. Run driver-specific tests on the Orange Pi, then integrate the complete robot and verify display, sensor response, gesture timing, and failure recovery together. Keep the Windows simulator as the regression-test environment.

No hardware pin numbers, pulse calibration, SPI controller identity, or board-library compatibility is assumed in this phase.
