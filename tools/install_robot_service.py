"""Install boot startup on the Orange Pi: sudo python3 -m tools.install_robot_service."""

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent.parent
SERVICE = Path('/etc/systemd/system/guidebot.service')


def unit_quote(value, *, command=False):
    """Quote a literal systemd value, including specifiers and ExecStart dollars."""
    value = str(value)
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError('Service values cannot contain control characters.')
    value = value.replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%')
    if command:
        value = value.replace('$', '$$')
    return '"' + value + '"'


def working_directory_value(root):
    # Unlike ExecStart arguments, WorkingDirectory is not shell-unquoted.
    value = str(root)
    if (not value.startswith('/') or value != value.strip()
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise ValueError('Working directory must be an absolute Linux path without surrounding whitespace or control characters.')
    return value.replace('%', '%%')


def build_unit(root, amplitude=100, audio_device='plughw:CARD=CD002AUDIO,DEV=0'):
    if type(amplitude) is not int or not 0 <= amplitude <= 200:
        raise ValueError('Speech amplitude must be an integer from 0 to 200.')
    return f'''[Unit]
Description=GuideBot campus information assistant
After=systemd-udev-trigger.service sound.target alsa-restore.service
StartLimitIntervalSec=0

[Service]
Type=exec
User=root
WorkingDirectory={working_directory_value(root)}
ExecStart=/usr/bin/python3 -u -m guidebot.robot --speech-amplitude {amplitude} --audio-device {unit_quote(audio_device, command=True)}
Restart=on-failure
RestartSec=10
KillMode=mixed
TimeoutStopSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
'''


def install(root, destination, unit):
    # Validate before touching an existing service. This does not open hardware.
    subprocess.run(['/usr/bin/python3', '-m', 'guidebot.robot', '--check'],
                   cwd=root, check=True)
    # Replace atomically so an interrupted write cannot leave a partial unit.
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n',
                                     dir=destination.parent, suffix='.service', delete=False) as output:
        temporary = Path(output.name)
        try:
            output.write(unit)
            output.flush()
            os.fchmod(output.fileno(), 0o644)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        # Check with the real systemd parser before replacing/enabling the unit.
        subprocess.run(['systemd-analyze', 'verify', '--man=no', str(temporary)], check=True)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    subprocess.run(['systemctl', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', 'enable', destination.name], check=True)
    # restart also starts a newly installed service, and applies changed options.
    subprocess.run(['systemctl', 'restart', destination.name], check=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--speech-amplitude', type=int, choices=range(201),
                        default=100, metavar='0-200')
    parser.add_argument('--audio-device', default='plughw:CARD=CD002AUDIO,DEV=0')
    args = parser.parse_args(argv)
    if sys.platform != 'linux' or not Path('/run/systemd/system').is_dir():
        parser.exit(1, 'Run this installer on the Orange Pi running systemd.\n')
    if os.geteuid() != 0:
        parser.exit(1, 'Run with sudo: sudo python3 -m tools.install_robot_service\n')
    try:
        install(ROOT, SERVICE, build_unit(ROOT, args.speech_amplitude, args.audio_device))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f'Service setup failed: {error}', file=sys.stderr)
        print('Inspect: sudo journalctl -u guidebot -b -n 60 --no-pager', file=sys.stderr)
        return 1
    print('GuideBot service enabled for boot and start requested. Servo motion is disabled.')
    print('Confirm the face and speech, then check: sudo systemctl status guidebot --no-pager')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
