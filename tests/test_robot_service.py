"""Boot service configuration and installation failures without Linux hardware."""

from pathlib import Path, PurePosixPath
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.install_robot_service import build_unit, install


class RobotServiceTests(unittest.TestCase):
    def test_boot_uses_system_python_and_no_bench_motion(self):
        unit = build_unit(PurePosixPath('/home/recursia/guidebot'), 200)
        self.assertIn('\nWorkingDirectory=/home/recursia/guidebot\n', unit)
        self.assertIn('ExecStart=/usr/bin/python3 -u -m guidebot.robot --speech-amplitude 200', unit)
        self.assertNotIn('--bench-motion', unit)
        self.assertIn('WantedBy=multi-user.target', unit)
        self.assertIn('Restart=on-failure', unit)
        self.assertIn('KillMode=mixed', unit)

    def test_literal_paths_and_audio_cannot_inject_unit_directives(self):
        unit = build_unit('/home/robot 100%/guidebot', audio_device='plug:$CARD"test')
        self.assertIn('\nWorkingDirectory=/home/robot 100%%/guidebot\n', unit)
        self.assertIn('--audio-device "plug:$$CARD\\"test"', unit)
        with self.assertRaises(ValueError):
            build_unit('/home/robot\nExecStart=/bin/false')
        with self.assertRaises(ValueError):
            build_unit('/home/robot', amplitude=201)
        with self.assertRaises(ValueError):
            build_unit('relative/path')

    def test_invalid_config_preserves_installed_service(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / 'guidebot.service'
            destination.write_text('existing service', encoding='utf-8')
            with patch('tools.install_robot_service.subprocess.run',
                       side_effect=subprocess.CalledProcessError(1, 'config check')) as run:
                with self.assertRaises(subprocess.CalledProcessError):
                    install(Path(folder), destination, 'replacement')
            self.assertEqual(destination.read_text(encoding='utf-8'), 'existing service')
            self.assertEqual(run.call_count, 1)

    def test_install_enables_and_restarts_and_reports_start_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            destination = root / 'guidebot.service'
            unit = build_unit('/home/recursia/guidebot')
            with patch('tools.install_robot_service.os.fchmod', create=True), \
                    patch('tools.install_robot_service.subprocess.run') as run:
                run.side_effect = [None, None, None, None,
                                   subprocess.CalledProcessError(1, 'restart')]
                with self.assertRaises(subprocess.CalledProcessError):
                    install(root, destination, unit)
            self.assertEqual(destination.read_text(encoding='utf-8'), unit)
            commands = [call.args[0] for call in run.call_args_list]
            self.assertEqual(commands[1][:3], ['systemd-analyze', 'verify', '--man=no'])
            self.assertEqual(Path(commands[1][3]).suffix, '.service')
            self.assertEqual([commands[0]] + commands[2:], [
                ['/usr/bin/python3', '-m', 'guidebot.robot', '--check'],
                ['systemctl', 'daemon-reload'],
                ['systemctl', 'enable', 'guidebot.service'],
                ['systemctl', 'restart', 'guidebot.service'],
            ])
            self.assertEqual(list(root.iterdir()), [destination])

    def test_systemd_rejection_preserves_service_and_does_not_enable(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            destination = root / 'guidebot.service'
            destination.write_text('existing service', encoding='utf-8')
            with patch('tools.install_robot_service.os.fchmod', create=True), \
                    patch('tools.install_robot_service.subprocess.run') as run:
                run.side_effect = [None, subprocess.CalledProcessError(1, 'verify')]
                with self.assertRaises(subprocess.CalledProcessError):
                    install(root, destination, 'invalid unit')
            self.assertEqual(destination.read_text(encoding='utf-8'), 'existing service')
            self.assertEqual(run.call_count, 2)
            self.assertEqual(list(root.iterdir()), [destination])
