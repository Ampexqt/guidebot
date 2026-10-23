"""Canvas robot renderer shared by the desktop and 240x320 preview."""

import math

BG = "#101f32"
INK = "#eaf4ff"
MUTED = "#95aac4"
TEAL = "#54ebcf"


def draw_robot(canvas, x, y, width, height, expression, elapsed, angles, *, body=True):
    """Draw one frame. All movement uses logical simulator angles."""
    sx, sy = width / 400, height / 260

    def oval(a, b, c, d, **kw):
        return canvas.create_oval(x + a*sx, y + b*sy, x + c*sx, y + d*sy, **kw)

    def line(points, **kw):
        scaled = [x + value*sx if index % 2 == 0 else y + value*sy
                  for index, value in enumerate(points)]
        return canvas.create_line(*scaled, **kw)

    pan = (angles["head_pan"] - 90) * 0.25
    tilt = (angles["head_tilt"] - 90) * 0.16
    if body:
        oval(136, 174, 264, 290, fill="#1c3650", outline="#365b78", width=2)
        for shoulder_x, name, sign in ((139, "left_arm", -1), (261, "right_arm", 1)):
            radians = math.radians(angles[name] - 90)
            end_x = shoulder_x + sign * (35 + 46 * math.sin(radians))
            end_y = 183 + 63 * math.cos(radians)
            line([shoulder_x, 183, end_x, end_y], fill="#4a6c88", width=max(5, 14*sx), capstyle="round")
            oval(end_x-8, end_y-8, end_x+8, end_y+8, fill=TEAL, outline="")
        oval(190, 207, 210, 227, fill=TEAL, outline="")
    # Head displacement makes pan/tilt visible without a physical servo.
    x += pan*sx
    y += tilt*sy
    oval(76, 28, 324, 196, fill="#25435d", outline="#4a6b86", width=2, tags="robot-head")
    oval(89, 40, 311, 183, fill="#071421", outline="#315875", width=2)
    oval(63, 91, 86, 139, fill="#3b607d", outline="")
    oval(314, 91, 337, 139, fill="#3b607d", outline="")
    line([200, 29, 200, 12], fill="#4a6b86", width=3)
    oval(193, 3, 207, 17, fill=TEAL, outline="")
    phase = elapsed % 4.6
    openness = 1.0
    if phase < 0.22:
        openness = max(0.07, abs(phase - 0.11) / 0.11)
    eye_height = 38 if expression != "focused" else 26
    if expression == "curious":
        eye_height = 44
    gaze = math.sin(elapsed * 0.6)*4 + pan*0.3
    for center in (151, 249):
        h = eye_height * openness
        oval(center-27+gaze, 104-h/2, center+27+gaze, 104+h/2,
             fill=TEAL if expression != "concerned" else "#ffd17a", outline="",
             tags=("robot-eye", "eye-left" if center == 151 else "eye-right"))
        if openness > 0.4:
            oval(center-12+gaze, 97-h/4, center-5+gaze, 104-h/4, fill="#dbfff6", outline="")
    if expression in ("friendly", "happy", "curious"):
        canvas.create_arc(x+170*sx, y+130*sy, x+230*sx, y+159*sy,
                          start=185, extent=170, style="arc", outline=TEAL,
                          width=max(2, 3*sx))
    elif expression == "concerned":
        canvas.create_arc(x+177*sx, y+147*sy, x+223*sx, y+169*sy,
                          start=15, extent=150, style="arc", outline="#ffd17a", width=2)
    else:
        line([183, 151, 217, 151], fill=TEAL, width=3, capstyle="round")
