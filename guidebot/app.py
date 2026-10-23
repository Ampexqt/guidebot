"""Tkinter desktop simulator. Every device is simulated in this entry point."""

import logging
import time
import tkinter as tk
from tkinter import ttk

from .controller import Page, RobotController
from .database import CampusDatabase
from .hardware.interfaces import SERVO_NAMES
from .hardware.simulated import SimulatedServos, SimulatedUltrasonic
from .ui.face import BG, INK, MUTED, TEAL, draw_robot
from .ui.preview import LCDPreview

logger = logging.getLogger(__name__)
BACKGROUND = "#0b1626"
PANEL = "#14263b"


class GuideBotApp:
    def __init__(self, root: tk.Tk, database: CampusDatabase):
        self.root = root
        self.sensor = SimulatedUltrasonic()
        self.controller = RobotController(database, SimulatedServos(), self.sensor)
        self._timer = None
        self._closed = False
        self._last_time = time.monotonic()
        self._last_telemetry = -1.0
        self._last_preview = -1.0
        self._last_signature = None
        self.root.title("GuideBot | Campus Assistant Simulator")
        width = min(1180, max(960, root.winfo_screenwidth()-80))
        height = min(900, max(700, root.winfo_screenheight()-100))
        root.geometry(f"{width}x{height}")
        root.minsize(960, 700)
        root.configure(bg=BACKGROUND)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self._configure_styles()
        self._build()
        self.root.bind("<Configure>", self._resize)
        self.root.bind("<Alt-Left>", lambda event: self.dispatch(self.controller.back))
        self.root.bind("<Control-Home>", lambda event: self.dispatch(self.controller.home))
        self.root.bind("<Escape>", lambda event: self.dispatch(self.controller.back))
        self._render_page()
        self._animate()
        logger.info("GuideBot started in simulation mode; real hardware is disabled")

    def _configure_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background=BACKGROUND)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BACKGROUND, foreground=INK, font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background=PANEL, foreground=INK)
        style.configure("Muted.TLabel", foreground=MUTED)
        style.configure("Small.TLabel", foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"))
        style.configure("Heading.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("TButton", background="#25405a", foreground=INK,
                        borderwidth=0, padding=(12, 8), font=("Segoe UI", 10))
        style.map("TButton", background=[("active", "#355776"), ("disabled", "#172a40")],
                  foreground=[("disabled", "#6a819a")])
        style.configure("Primary.TButton", background=TEAL, foreground="#08251e", font=("Segoe UI", 10, "bold"))
        style.map("Primary.TButton", background=[("active", "#9cffe8"), ("disabled", "#254b47")])
        style.configure("TEntry", fieldbackground="#1c334b", foreground=INK,
                        insertcolor=INK, padding=9, borderwidth=0)
        style.configure("TCheckbutton", background=BACKGROUND, foreground=INK, font=("Segoe UI", 9))
        style.map("TCheckbutton", background=[("active", BACKGROUND)])
        style.configure("Horizontal.TScale", background=BACKGROUND, troughcolor="#25405a")
        style.configure("TNotebook", background=BACKGROUND, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=MUTED, padding=(12, 7))
        style.map("TNotebook.Tab", background=[("selected", "#25405a")],
                  foreground=[("selected", TEAL)])

    def _button(self, parent, text, action, **kwargs):
        return ttk.Button(parent, text=text, command=lambda: self.dispatch(action), **kwargs)

    def _build(self):
        shell = ttk.Frame(self.root, padding=(22, 16))
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(3, weight=1)
        header = ttk.Frame(shell)
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text="GuideBot", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="  /  Campus assistant", style="Muted.TLabel").pack(side="left", pady=(8, 0))
        tk.Label(header, text="SIMULATION  /  NO HARDWARE", bg="#173f3b", fg=TEAL,
                 font=("Segoe UI", 9, "bold"), padx=12, pady=7).pack(side="right")
        nav = ttk.Frame(shell)
        nav.grid(row=1, column=0, sticky="ew", pady=(10, 10))
        self.back_button = self._button(nav, "<  Back", self.controller.back)
        self.back_button.pack(side="left")
        self.home_button = self._button(nav, "Home", self.controller.home)
        self.home_button.pack(side="left", padx=6)
        self.breadcrumb = ttk.Label(nav, style="Muted.TLabel")
        self.breadcrumb.pack(side="left", padx=12)
        self.notice = tk.Label(shell, text=self.controller.database.notice,
                               bg="#3a3021", fg="#ffdc96", font=("Segoe UI", 9),
                               anchor="w", padx=12, pady=8, wraplength=1050)
        self.notice.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        content = ttk.Frame(shell)
        content.grid(row=3, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)
        left = ttk.Frame(content)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)
        robot_panel = ttk.Frame(left, style="Panel.TFrame", padding=8)
        robot_panel.grid(row=0, column=0, sticky="ew")
        self.face = tk.Canvas(robot_panel, height=180, background=BG, highlightthickness=0)
        self.face.pack(fill="x")
        self.expression_label = ttk.Label(robot_panel, style="Panel.TLabel", anchor="center")
        self.expression_label.pack(fill="x", pady=2)
        self.page_host = ttk.Frame(left, padding=(0, 14, 0, 0))
        self.page_host.grid(row=1, column=0, sticky="nsew")
        self.page_host.columnconfigure(0, weight=1)
        self._build_welcome()
        self._build_menu()
        self._build_directions()
        self._build_controls(left)
        right = ttk.Frame(content, width=266)
        right.grid(row=0, column=1, sticky="ns")
        self.right_notebook = ttk.Notebook(right)
        self.right_notebook.pack(fill="x")
        self.preview_tab = ttk.Frame(self.right_notebook, padding=5)
        self.status_tab = ttk.Frame(self.right_notebook, padding=5)
        self.right_notebook.add(self.preview_tab, text="LCD preview")
        self.right_notebook.add(self.status_tab, text="Device status")
        preview_border = tk.Frame(self.preview_tab, bg="#35516b", padx=3, pady=3)
        preview_border.pack(pady=(7, 5))
        self.preview = LCDPreview(preview_border, self.controller, self.dispatch)
        self.preview.pack()
        ttk.Label(self.preview_tab, text="240 × 320 logical pixels · clickable", style="Small.TLabel").pack(anchor="w")
        self._build_telemetry(self.status_tab)
        summary = ttk.Frame(right, style="Panel.TFrame", padding=10)
        summary.pack(fill="x", pady=(12, 0))
        ttk.Label(summary, textvariable=self.state_var, style="Panel.TLabel", wraplength=230).pack(anchor="w")
        ttk.Label(summary, textvariable=self.distance_status, style="Panel.TLabel").pack(anchor="w", pady=(4, 0))
        ttk.Label(summary, text="Servo angles: open Device status above.", style="Panel.TLabel",
                  font=("Segoe UI", 8), foreground=MUTED, wraplength=230).pack(anchor="w", pady=(5, 0))
        self.error_text = tk.StringVar()
        ttk.Label(shell, textvariable=self.error_text, foreground="#ffb590", wraplength=1000).grid(
            row=4, column=0, sticky="w", pady=(7, 0))
        ttk.Label(shell, text="Windows prototype  •  All servo angles and distance readings are simulated",
                  style="Small.TLabel").grid(row=5, column=0, sticky="w", pady=(4, 0))

    def _build_welcome(self):
        self.welcome_page = ttk.Frame(self.page_host)
        ttk.Label(self.welcome_page, text="Hello! I'm GuideBot!", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(self.welcome_page, text="Your friendly campus information assistant.",
                  style="Muted.TLabel").pack(anchor="w", pady=(8, 4))
        ttk.Label(self.welcome_page, text="Find a place, follow each step, and try the robot controls below.",
                  style="Muted.TLabel", wraplength=540).pack(anchor="w", pady=(0, 18))
        self.start_button = self._button(self.welcome_page, "Find a destination  >", self.controller.show_menu,
                                        style="Primary.TButton")
        self.start_button.pack(anchor="w")

    def _build_menu(self):
        self.menu_page = ttk.Frame(self.page_host)
        self.menu_page.columnconfigure(0, weight=1)
        ttk.Label(self.menu_page, text="Where would you like to go?", style="Heading.TLabel").grid(row=0, column=0, sticky="w")
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.menu_page, textvariable=self.search_var, font=("Segoe UI", 11))
        self.search_entry.grid(row=1, column=0, sticky="ew", pady=(9, 4))
        self.search_entry.bind("<Return>", self._open_first_result)
        self.results_count = ttk.Label(self.menu_page, style="Small.TLabel")
        self.results_count.grid(row=2, column=0, sticky="w", pady=(3, 4))
        results_frame = ttk.Frame(self.menu_page)
        results_frame.grid(row=3, column=0, sticky="ew")
        results_frame.columnconfigure(0, weight=1)
        self.destination_list = tk.Listbox(results_frame, height=4, bg=PANEL, fg=INK,
                                          selectbackground="#27665f", selectforeground="white",
                                          font=("Segoe UI", 11), activestyle="none", borderwidth=0,
                                          highlightthickness=1, highlightbackground="#35516b",
                                          exportselection=False)
        self.destination_list.grid(row=0, column=0, sticky="ew")
        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.destination_list.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.destination_list.configure(yscrollcommand=scrollbar.set)
        self.destination_list.bind("<Double-Button-1>", self._open_selected)
        self.destination_list.bind("<Return>", self._open_selected)
        self.open_button = self._button(self.menu_page, "Show directions  >", self._select_list_item,
                                       style="Primary.TButton")
        self.open_button.grid(row=4, column=0, sticky="w", pady=(6, 0))
        self.search_var.trace_add("write", self._search_changed)
        self._visible_destinations = ()

    def _build_directions(self):
        self.directions_page = ttk.Frame(self.page_host)
        self.direction_title = ttk.Label(self.directions_page, style="Heading.TLabel")
        self.direction_title.pack(anchor="w")
        self.route_origin = ttk.Label(self.directions_page, style="Small.TLabel", wraplength=530)
        self.route_origin.pack(anchor="w", pady=(5, 7))
        self.step_label = ttk.Label(self.directions_page, foreground=TEAL, font=("Segoe UI", 10, "bold"))
        self.step_label.pack(anchor="w")
        self.step_text = tk.Text(self.directions_page, height=4, width=30, wrap="word",
                                 background=PANEL, foreground=INK, font=("Segoe UI", 12),
                                 padx=12, pady=10, relief="flat", cursor="arrow", takefocus=False)
        self.step_text.pack(fill="both", expand=True, pady=(7, 8))
        self.step_text.configure(state="disabled")
        step_nav = ttk.Frame(self.directions_page)
        step_nav.pack(fill="x")
        self.previous_button = self._button(step_nav, "<  Previous step", lambda: self.controller.change_step(-1))
        self.previous_button.pack(side="left")
        self.next_button = self._button(step_nav, "Next step  >", lambda: self.controller.change_step(1),
                                       style="Primary.TButton")
        self.next_button.pack(side="left", padx=8)
        self.route_complete = ttk.Label(step_nav, text="Route complete", foreground=TEAL)

    def _build_controls(self, parent):
        controls = ttk.Frame(parent)
        controls.grid(row=2, column=0, sticky="ew", pady=(16, 0))
        ttk.Label(controls, text="ROBOT SANDBOX", style="Small.TLabel").pack(anchor="w", pady=(0, 5))
        gestures = ttk.Frame(controls)
        gestures.pack(fill="x")
        for name, label in (("wave", "Wave"), ("nod", "Nod"), ("look", "Look around"),
                            ("point", "Point"), ("neutral", "Reset pose")):
            self._button(gestures, label, lambda name=name: self.controller.gesture(name)).pack(side="left", padx=(0, 5))
        sensor_row = ttk.Frame(controls)
        sensor_row.pack(fill="x", pady=(8, 0))
        self.auto_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(sensor_row, text="Automatic distance", variable=self.auto_var,
                        command=lambda: self.dispatch(self._set_sensor_mode)).pack(side="left")
        self.distance_value = tk.StringVar(value="100 cm")
        ttk.Label(sensor_row, textvariable=self.distance_value, style="Small.TLabel").pack(side="right")
        self.distance_slider = ttk.Scale(sensor_row, from_=2, to=200, value=100,
                                        command=self._manual_distance)
        self.distance_slider.pack(side="left", fill="x", expand=True, padx=8)
        self.distance_slider.state(["disabled"])
        ttk.Label(controls, text="Turn automatic off to use the slider. Below 45 cm, GuideBot greets a visitor on Home.",
                  style="Small.TLabel", wraplength=610).pack(anchor="w", pady=(4, 0))

    def _build_telemetry(self, parent):
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=12)
        panel.pack(fill="x", pady=(14, 0))
        ttk.Label(panel, text="LIVE STATUS", style="Panel.TLabel", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.state_var = tk.StringVar()
        ttk.Label(panel, textvariable=self.state_var, style="Panel.TLabel", wraplength=220).pack(anchor="w", pady=(5, 4))
        self.distance_status = tk.StringVar()
        ttk.Label(panel, textvariable=self.distance_status, style="Panel.TLabel").pack(anchor="w", pady=(0, 6))
        self.servo_vars = {}
        for name in SERVO_NAMES:
            var = tk.StringVar()
            self.servo_vars[name] = var
            ttk.Label(panel, textvariable=var, style="Panel.TLabel", font=("Consolas", 10)).pack(anchor="w")
        self.device_status = tk.StringVar(value="Drivers: simulated only")
        ttk.Label(panel, textvariable=self.device_status, style="Panel.TLabel", foreground=TEAL,
                  wraplength=220).pack(anchor="w", pady=(8, 0))

    def dispatch(self, action):
        if self._closed:
            return
        try:
            action()
            self.error_text.set("")
            self._render_page()
        except Exception as exc:
            logger.exception("User action failed")
            self.error_text.set(f"Action failed: {exc}")

    def _resize(self, event):
        if event.widget is self.root and not self._closed:
            # Keep route controls visible on a 1366x768 laptop, including DPI scaling.
            height = max(40, min(180, event.height - 674))
            if int(float(self.face.cget("height"))) != height:
                self.face.configure(height=height)

    def _search_changed(self, *_):
        self.dispatch(lambda: self.controller.search(self.search_var.get()))

    def _open_first_result(self, _event=None):
        if self.controller.results:
            self.dispatch(lambda: self.controller.select(self.controller.results[0].id))
        return "break"

    def _open_selected(self, _event=None):
        self.dispatch(self._select_list_item)
        return "break"

    def _select_list_item(self):
        selection = self.destination_list.curselection()
        if selection and selection[0] < len(self._visible_destinations):
            self.controller.select(self._visible_destinations[selection[0]].id)

    def _set_sensor_mode(self):
        self.sensor.automatic = self.auto_var.get()
        self.distance_slider.state(["disabled"] if self.sensor.automatic else ["!disabled"])
        if not self.sensor.automatic:
            self.sensor.set_manual_cm(float(self.distance_slider.get()))

    def _manual_distance(self, value):
        self.distance_value.set(f"{float(value):.0f} cm")
        if not self.sensor.automatic:
            self.dispatch(lambda: self.sensor.set_manual_cm(float(value)))

    def _render_page(self):
        c = self.controller
        page_changed = self._last_signature is None or self._last_signature[0] != c.page
        signature = (c.page, c.query, c.destination.id if c.destination else None, c.step_index)
        if signature != self._last_signature:
            for frame in (self.welcome_page, self.menu_page, self.directions_page):
                frame.grid_remove()
            frame = {Page.WELCOME: self.welcome_page, Page.MENU: self.menu_page,
                     Page.DIRECTIONS: self.directions_page}[c.page]
            frame.grid(row=0, column=0, sticky="nsew")
            self.back_button.state(["disabled"] if c.page == Page.WELCOME else ["!disabled"])
            self.breadcrumb.configure(text={Page.WELCOME: "Welcome", Page.MENU: "Campus / Destinations",
                                            Page.DIRECTIONS: "Campus / Directions"}[c.page])
            if (self.search_var.get().strip() != c.query
                    or (c.page == Page.WELCOME and self.search_var.get() != c.query)):
                self.search_var.set(c.query)
            if c.page == Page.MENU:
                self._visible_destinations = c.results
                self.destination_list.delete(0, "end")
                for item in self._visible_destinations:
                    self.destination_list.insert("end", f"  {item.name}  /  {item.category}")
                count = len(self._visible_destinations)
                self.results_count.configure(text=f"{count} destination{'s' if count != 1 else ''}  /  Try books, records, ICT"
                                             if count else "No matches. Try another keyword.")
                self.open_button.state(["!disabled"] if count else ["disabled"])
                if count:
                    self.destination_list.selection_set(0)
                    self.destination_list.activate(0)
                if page_changed:
                    self.search_entry.focus_set()
            if c.page == Page.DIRECTIONS and c.destination:
                self.direction_title.configure(text=c.destination.name)
                self.route_origin.configure(text=f"Start: {c.database.starting_point}")
                self.step_label.configure(text=f"STEP {c.step_index+1} OF {len(c.destination.steps)}  •  "
                                          + ("PLACEHOLDER" if c.database.is_placeholder else "LOCAL ROUTE"))
                self.step_text.configure(state="normal")
                self.step_text.delete("1.0", "end")
                self.step_text.insert("1.0", c.destination.steps[c.step_index])
                self.step_text.configure(state="disabled")
                self.previous_button.state(["disabled"] if c.step_index == 0 else ["!disabled"])
                last = c.step_index == len(c.destination.steps)-1
                self.next_button.state(["disabled"] if last else ["!disabled"])
                if last:
                    self.route_complete.pack(side="left")
                else:
                    self.route_complete.pack_forget()
            self._last_signature = signature
        self.preview.render()

    def _animate(self):
        if self._closed:
            return
        now = time.monotonic()
        dt = min(0.1, max(0.0, now-self._last_time))
        self._last_time = now
        try:
            c = self.controller
            c.tick(dt)
            self.face.delete("all")
            width, height = max(1, self.face.winfo_width()), max(1, self.face.winfo_height())
            robot_width = min(340, width, height * 400 / 260)
            draw_robot(self.face, (width-robot_width)/2, 0, robot_width, height,
                       c.expression, c.elapsed, c.servos.angles)
            if c.elapsed-self._last_preview >= 0.1:
                self.preview.render()
                self._last_preview = c.elapsed
            if c.elapsed-self._last_telemetry >= 0.15:
                self.state_var.set(c.state)
                self.expression_label.configure(text=f"Expression: {c.expression}  /  Motion: {c.servos.active_gesture}")
                self.distance_status.set("Distance: unavailable" if c.distance_cm is None else
                                         f"Distance: {c.distance_cm:.1f} cm" + ("  /  visitor" if c.nearby else ""))
                for name, var in self.servo_vars.items():
                    var.set(f"{name.replace('_', ' '):<12} {c.servos.angles[name]:6.1f}°")
                errors = [message for message in (c.sensor_error, c.motion_error) if message]
                self.device_status.set("Device error: " + "; ".join(errors) if errors else "Drivers: simulated only")
                self._last_telemetry = c.elapsed
        except Exception as exc:
            logger.exception("Animation frame failed")
            self.error_text.set(f"Display update failed: {exc}")
        finally:
            if not self._closed:
                self._timer = self.root.after(33, self._animate)

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._timer is not None:
            self.root.after_cancel(self._timer)
            self._timer = None
        self.controller.close()
        logger.info("GuideBot closed")
        self.root.destroy()
