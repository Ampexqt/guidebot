"""Real Tk widget tests; skipped explicitly if Tcl/Tk or a display is unavailable."""

from types import SimpleNamespace
import os
import unittest

try:
    if os.environ.get("GUIDEBOT_SKIP_GUI") == "1":
        tk = None
    else:
        import tkinter as tk
except ImportError:
    tk = None

from guidebot.controller import Page
from guidebot.database import CampusDatabase, DEFAULT_DATABASE


@unittest.skipIf(tk is None, "GUI disabled by GUIDEBOT_SKIP_GUI=1, or Tkinter is not installed")
class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            root = tk.Tk()
            root.destroy()
        except tk.TclError as exc:
            raise unittest.SkipTest(f"Tk display unavailable: {exc}")

    def setUp(self):
        from guidebot.app import GuideBotApp
        self.root = tk.Tk()
        self.errors = []
        self.root.report_callback_exception = lambda *args: self.errors.append(args)
        self.app = GuideBotApp(self.root, CampusDatabase(DEFAULT_DATABASE))
        self.root.update()
        self.addCleanup(self.app.close)

    def test_welcome_animation_and_preview_dimensions(self):
        self.assertTrue(self.app.welcome_page.winfo_ismapped())
        self.assertEqual(self.app.preview.winfo_width(), 240)
        self.assertEqual(self.app.preview.winfo_height(), 320)
        self.assertEqual(len(self.app.face.find_withtag("robot-eye")), 2)
        self.assertEqual(len(self.app.face.find_withtag("robot-head")), 1)
        self.assertEqual(self.errors, [])

    def test_widgets_complete_search_and_directions_flow(self):
        self.app.start_button.invoke()
        self.app.search_var.set("records")
        self.root.update()
        self.assertEqual(self.app.destination_list.size(), 1)
        self.app.open_button.invoke()
        self.assertEqual(self.app.controller.destination.id, "registrar")
        self.assertIn("fictional", self.app.step_text.get("1.0", "end"))
        self.app.next_button.invoke()
        self.app.next_button.invoke()
        self.assertEqual(self.app.controller.step_index, 2)
        self.assertIn("disabled", self.app.next_button.state())
        self.app.previous_button.invoke()
        self.assertEqual(self.app.controller.step_index, 1)
        self.app.back_button.invoke()
        self.assertEqual(self.app.controller.page, Page.MENU)
        self.assertEqual(self.app.search_var.get(), "records")
        self.app.dispatch(self.app.controller.home)
        self.assertEqual(self.app.search_var.get(), "")
        self.assertEqual(self.app.controller.page, Page.WELCOME)
        self.assertEqual(self.errors, [])

    def test_no_matches_disables_open_and_enter_is_safe(self):
        self.app.start_button.invoke()
        self.app.search_var.set("unknown campus building")
        self.assertEqual(self.app.destination_list.size(), 0)
        self.assertIn("disabled", self.app.open_button.state())
        self.app._open_first_result()
        self.assertEqual(self.app.controller.page, Page.MENU)

    def test_home_clears_whitespace_only_search(self):
        self.app.start_button.invoke()
        self.app.search_var.set("   ")
        self.app.home_button.invoke()
        self.assertEqual(self.app.search_var.get(), "")

    def test_face_blinks_moves_eyes_and_changes_expression(self):
        from guidebot.ui.face import draw_robot, TEAL
        from guidebot.hardware.simulated import NEUTRAL
        canvas = self.app.face
        def render(elapsed, expression="friendly", angles=NEUTRAL):
            canvas.delete("all")
            draw_robot(canvas, 0, 0, 400, 260, expression, elapsed, angles)
            return canvas.coords("eye-left")
        open_eye = render(1)
        closed_eye = render(.11)
        self.assertLess(closed_eye[3]-closed_eye[1], (open_eye[3]-open_eye[1])*.2)
        moved_eye = render(2)
        self.assertNotEqual(open_eye[0], moved_eye[0])
        render(1, "concerned")
        self.assertEqual(canvas.itemcget("eye-left", "fill"), "#ffd17a")
        render(1, "happy")
        self.assertEqual(canvas.itemcget("eye-left", "fill"), TEAL)

    def test_gui_gestures_update_angles_and_robot_head(self):
        from guidebot.ui.face import draw_robot
        from guidebot.hardware.simulated import NEUTRAL
        self.app.dispatch(lambda: self.app.controller.gesture("look"))
        self.app.controller.tick(.2)
        self.assertNotEqual(self.app.controller.servos.angles["head_pan"], 90)
        canvas = self.app.face
        canvas.delete("all")
        draw_robot(canvas, 0, 0, 400, 260, "friendly", 1, NEUTRAL)
        neutral_head = canvas.coords("robot-head")
        canvas.delete("all")
        draw_robot(canvas, 0, 0, 400, 260, "friendly", 1, self.app.controller.servos.angles)
        self.assertNotEqual(canvas.coords("robot-head"), neutral_head)
        self.app.dispatch(lambda: self.app.controller.gesture("neutral"))
        self.app.controller.tick(1)
        self.assertTrue(all(angle == 90 for angle in self.app.controller.servos.angles.values()))

    def test_preview_clicks_navigation_and_step_controls(self):
        self.app.preview._click(SimpleNamespace(x=120, y=270))
        self.assertEqual(self.app.controller.page, Page.MENU)
        self.app.preview._click(SimpleNamespace(x=120, y=115))
        self.assertEqual(self.app.controller.page, Page.DIRECTIONS)
        self.app.preview._click(SimpleNamespace(x=175, y=260))
        self.assertEqual(self.app.controller.step_index, 1)
        self.app.preview._click(SimpleNamespace(x=175, y=300))
        self.assertEqual(self.app.controller.page, Page.WELCOME)

    def test_manual_sensor_and_telemetry(self):
        self.app.auto_var.set(False)
        self.app.dispatch(self.app._set_sensor_mode)
        self.app.distance_slider.set(30)
        self.root.update()
        self.app.controller.tick(0.2)
        self.assertEqual(self.app.controller.distance_cm, 30)
        self.assertEqual(self.app.controller.servos.active_gesture, "wave")

    def test_failed_action_is_reported_and_gui_stays_usable(self):
        def fail():
            raise ValueError("test action failure")
        with self.assertLogs("guidebot.app", level="ERROR"):
            self.app.dispatch(fail)
        self.assertIn("test action failure", self.app.error_text.get())
        self.app.start_button.invoke()
        self.assertEqual(self.app.controller.page, Page.MENU)
        self.assertEqual(self.app.error_text.get(), "")

    def test_animation_event_loop_runs_and_shutdown_cancels_timer(self):
        start = self.app.controller.elapsed
        self.root.after(250, self.root.quit)
        self.root.mainloop()
        self.assertGreater(self.app.controller.elapsed, start)
        self.assertTrue(self.app.state_var.get())
        self.assertEqual(self.errors, [])
        self.app.close()
        self.assertTrue(self.app.controller.closed)
        self.assertIsNone(self.app._timer)

    def test_controls_fit_minimum_window_size(self):
        self.root.geometry("960x700")
        self.root.update()
        self.app.start_button.invoke()
        self.root.update()
        # Both the menu and sandbox remain accessible at the minimum size.
        self.assert_widget_inside_window(self.app.open_button)
        self.assert_widget_inside_window(self.app.distance_slider)
        self.assert_widget_inside_window(self.app.preview)
        self.assertLessEqual(self.app.open_button.winfo_rooty()+self.app.open_button.winfo_height(),
                             self.app.distance_slider.winfo_rooty()-20)
        self.app.open_button.invoke()
        self.root.update()
        self.assert_widget_inside_window(self.app.next_button)
        self.app.right_notebook.select(self.app.status_tab)
        self.root.update()
        for child in self.app.status_tab.winfo_children()[0].winfo_children():
            self.assert_widget_inside_window(child)

    def assert_widget_inside_window(self, widget):
        ancestor = widget.master
        while ancestor is not None:
            with self.subTest(widget=str(widget), ancestor=str(ancestor)):
                self.assertGreaterEqual(widget.winfo_rooty(), ancestor.winfo_rooty())
                self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(),
                                     ancestor.winfo_rooty()+ancestor.winfo_height())
                self.assertGreaterEqual(widget.winfo_rootx(), ancestor.winfo_rootx())
                self.assertLessEqual(widget.winfo_rootx()+widget.winfo_width(),
                                     ancestor.winfo_rootx()+ancestor.winfo_width())
            ancestor = ancestor.master
