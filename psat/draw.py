"""Ve so do khung tren Tkinter Canvas - khong can matplotlib."""

from __future__ import annotations

import math
import tkinter as tk

BG = "#10161f"
GRID = "#1b2532"
AXIS = "#2b3a4d"
MEMBER = "#5fa8d3"
MEMBER_OK = "#3ec98a"
MEMBER_WARN = "#e8b84b"
MEMBER_BAD = "#e5544b"
NODE = "#c9d6e2"
SUPPORT = "#9aa7b5"
LOADC = "#ff8c42"
DEFL = "#7b61ff"
MOMENT = "#e5544b"
MODE = "#2ec4b6"
TEXT = "#c9d6e2"
DIM = "#6b7c8f"


class FrameCanvas(tk.Canvas):
    """Canvas tu dong scale de ve khung, tai, goi tua va ket qua."""

    def __init__(self, master, **kw):
        kw.setdefault("bg", BG)
        kw.setdefault("highlightthickness", 0)
        super().__init__(master, **kw)
        self.sx = self.sy = 1.0
        self.ox = self.oy = 0.0
        self.show_deflection = True
        self.show_moment = False
        self.show_mode = False
        self._data = None
        self.bind("<Configure>", lambda e: self.redraw())

    # ---------------- bien doi toa do ----------------
    def _fit(self, xs, ys, pad=60):
        w = max(self.winfo_width(), 50)
        h = max(self.winfo_height(), 50)
        if not xs or not ys:
            self.sx = self.sy = 1.0
            self.ox, self.oy = w / 2, h / 2
            return
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        dx = max(x1 - x0, 1.0)
        dy = max(y1 - y0, 1.0)
        s = min((w - 2 * pad) / dx, (h - 2 * pad) / dy)
        s = max(s, 1e-9)
        self.sx = self.sy = s
        self.ox = (w - s * (x0 + x1)) / 2
        self.oy = (h + s * (y0 + y1)) / 2

    def W(self, x, y):
        """The gioi (mm) -> man hinh (px). Truc y lat nguoc."""
        return self.ox + self.sx * x, self.oy - self.sy * y

    # ---------------- API ----------------
    def set_data(self, project=None, result=None, mode_index=0):
        self._data = (project, result, mode_index)
        self.redraw()

    def redraw(self):
        self.delete("all")
        if not self._data:
            self._empty()
            return
        project, result, mode_index = self._data
        if project is None or not project.members:
            self._empty()
            return

        xs, ys = [], []
        for m in project.members:
            xs += [m.x1, m.x2]
            ys += [m.y1, m.y2]
        self._fit(xs, ys)

        self._grid(xs, ys)
        self._members(project, result)
        if result is not None:
            if self.show_moment:
                self._moment(project, result)
            if self.show_mode and result.buckling_modes:
                self._mode(result, mode_index)
            if self.show_deflection:
                self._deflected(result)
        self._supports(project)
        self._loads(project)
        self._legend(project, result)

    # ---------------- cac lop ve ----------------
    def _empty(self):
        w = max(self.winfo_width(), 50)
        h = max(self.winfo_height(), 50)
        self.create_text(w / 2, h / 2, fill=DIM, font=("Segoe UI", 10),
                         text="Nhap thanh support o bang ben trai roi bam Tinh")

    def _grid(self, xs, ys):
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        span = max(x1 - x0, y1 - y0, 1.0)
        step = 10 ** math.floor(math.log10(span))
        if span / step < 3:
            step /= 2
        elif span / step > 8:
            step *= 2

        gx0 = math.floor((x0 - step) / step) * step
        gx1 = math.ceil((x1 + step) / step) * step
        gy0 = math.floor((y0 - step) / step) * step
        gy1 = math.ceil((y1 + step) / step) * step

        n = 0
        g = gx0
        while g <= gx1 + 1e-9 and n < 400:
            a = self.W(g, gy0)
            b = self.W(g, gy1)
            self.create_line(a[0], a[1], b[0], b[1],
                             fill=AXIS if abs(g) < 1e-9 else GRID)
            g += step
            n += 1
        g = gy0
        n = 0
        while g <= gy1 + 1e-9 and n < 400:
            a = self.W(gx0, g)
            b = self.W(gx1, g)
            self.create_line(a[0], a[1], b[0], b[1],
                             fill=AXIS if abs(g) < 1e-9 else GRID)
            g += step
            n += 1

        px, py = self.W(gx0, gy0)
        self.create_text(px + 4, py - 8, anchor="w", fill=DIM,
                         font=("Consolas", 8), text="o luoi = %g mm" % step)

    def _member_colour(self, result, i):
        if result is None:
            return MEMBER, 4
        for c in result.assessment.members:
            if c.member == i:
                u = c.utilization
                if u > 1.0:
                    return MEMBER_BAD, 6
                if u > 0.85:
                    return MEMBER_WARN, 5
                return MEMBER_OK, 4
        return MEMBER, 4

    def _members(self, project, result):
        for i, m in enumerate(project.members):
            col, wdt = self._member_colour(result, i)
            a = self.W(m.x1, m.y1)
            b = self.W(m.x2, m.y2)
            self.create_line(a[0], a[1], b[0], b[1], fill=col, width=wdt,
                             capstyle="round")
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            lab = m.label or "T%d" % (i + 1)
            if result is not None:
                for c in result.assessment.members:
                    if c.member == i:
                        lab += "  %.0f%%" % (c.utilization * 100)
                        break
            # day nhan ra khoi truc thanh
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / L, dx / L
            self.create_text(mx + nx * 14, my + ny * 14, fill=TEXT,
                             font=("Consolas", 8), text=lab)

        for i, m in enumerate(project.members):
            for (x, y) in (m.p1, m.p2):
                px, py = self.W(x, y)
                self.create_oval(px - 3, py - 3, px + 3, py + 3,
                                 fill=NODE, outline="")

    def _supports(self, project):
        for s in project.supports:
            x, y = self.W(s.x, s.y)
            if s.kind == "Ngam":
                self.create_rectangle(x - 13, y - 3, x + 13, y + 3,
                                      outline=SUPPORT, width=2)
                for k in range(-12, 13, 6):
                    self.create_line(x + k, y + 3, x + k - 5, y + 11,
                                     fill=SUPPORT)
            elif s.kind == "Khop":
                self.create_polygon(x, y, x - 10, y + 16, x + 10, y + 16,
                                    outline=SUPPORT, fill="", width=2)
                for k in range(-10, 13, 6):
                    self.create_line(x + k, y + 16, x + k - 5, y + 24,
                                     fill=SUPPORT)
            else:
                self.create_polygon(x, y, x - 10, y + 13, x + 10, y + 13,
                                    outline=SUPPORT, fill="", width=2)
                self.create_oval(x - 11, y + 13, x - 5, y + 19, outline=SUPPORT)
                self.create_oval(x + 5, y + 13, x + 11, y + 19, outline=SUPPORT)
            self.create_text(x, y + 30, fill=DIM, font=("Consolas", 7),
                             text=s.kind)

    def _loads(self, project):
        if not project.loads:
            return
        mx = max(l.magnitude for l in project.loads) or 1.0
        for ld in project.loads:
            x, y = self.W(ld.x, ld.y)
            L = 30 + 30 * (ld.magnitude / mx)
            a = math.radians(ld.angle)
            # mui ten ket thuc TAI diem dat luc
            x0 = x - L * math.cos(a)
            y0 = y + L * math.sin(a)
            self.create_line(x0, y0, x, y, fill=LOADC, width=3,
                             arrow="last", arrowshape=(12, 14, 5))
            txt = "%s%.2f kN" % ((ld.label + " ") if ld.label else "",
                                 ld.magnitude / 1000.0)
            self.create_text(x0, y0 - 10, fill=LOADC, font=("Consolas", 8),
                             text=txt)

    def _deflected(self, result):
        sol = result.solution
        model = result.model
        dmax = max((math.hypot(sol.u[3 * i], sol.u[3 * i + 1])
                    for i in range(len(model.nodes))), default=0.0)
        if dmax <= 1e-12:
            return
        # phong to sao cho chuyen vi lon nhat chiem ~8% be ngang khung
        target_px = 0.08 * max(self.winfo_width(), 100)
        k = target_px / (dmax * self.sx)

        for e in model.elements:
            n1, n2 = model.nodes[e.n1], model.nodes[e.n2]
            a = self.W(n1.x + k * sol.u[3 * e.n1], n1.y + k * sol.u[3 * e.n1 + 1])
            b = self.W(n2.x + k * sol.u[3 * e.n2], n2.y + k * sol.u[3 * e.n2 + 1])
            self.create_line(a[0], a[1], b[0], b[1], fill=DEFL, width=2,
                             dash=(4, 3))
        self.create_text(10, 10, anchor="nw", fill=DEFL, font=("Consolas", 8),
                         text="- - -  bien dang (x%.0f), lon nhat %.1f mm"
                              % (k, dmax))

    def _moment(self, project, result):
        model = result.model
        mmax = 0.0
        for r in result.solution.elements:
            mmax = max(mmax, r.M_max_abs)
        if mmax <= 1e-9:
            return
        target_px = 0.13 * max(self.winfo_height(), 100)
        k = target_px / mmax

        for e, r in zip(model.elements, result.solution.elements):
            n1, n2 = model.nodes[e.n1], model.nodes[e.n2]
            dx, dy = n2.x - n1.x, n2.y - n1.y
            L = math.hypot(dx, dy) or 1.0
            ux, uy = dx / L, dy / L
            nx, ny = -uy, ux
            pts = []
            for xx, mm in zip(r.x, r.M):
                bx = n1.x + ux * xx
                by = n1.y + uy * xx
                off = mm * k / self.sx
                pts.append(self.W(bx + nx * off, by + ny * off))
            flat = [c for p in pts for c in p]
            if len(flat) >= 4:
                self.create_line(*flat, fill=MOMENT, width=1)
            a = self.W(n1.x, n1.y)
            self.create_line(a[0], a[1], pts[0][0], pts[0][1], fill=MOMENT)
            b = self.W(n2.x, n2.y)
            self.create_line(b[0], b[1], pts[-1][0], pts[-1][1], fill=MOMENT)

        self.create_text(10, 26, anchor="nw", fill=MOMENT, font=("Consolas", 8),
                         text="bieu do moment, lon nhat %.3e N.mm" % mmax)

    def _mode(self, result, idx):
        if idx >= len(result.buckling_modes):
            return
        phi = result.buckling_modes[idx]
        model = result.model
        dmax = max((math.hypot(phi[3 * i], phi[3 * i + 1])
                    for i in range(len(model.nodes))), default=0.0)
        if dmax <= 1e-12:
            return
        target_px = 0.10 * max(self.winfo_width(), 100)
        k = target_px / (dmax * self.sx)
        for e in model.elements:
            n1, n2 = model.nodes[e.n1], model.nodes[e.n2]
            a = self.W(n1.x + k * phi[3 * e.n1], n1.y + k * phi[3 * e.n1 + 1])
            b = self.W(n2.x + k * phi[3 * e.n2], n2.y + k * phi[3 * e.n2 + 1])
            self.create_line(a[0], a[1], b[0], b[1], fill=MODE, width=2)
        lam = result.lambdas[idx] if idx < len(result.lambdas) else 0.0
        self.create_text(10, 42, anchor="nw", fill=MODE, font=("Consolas", 8),
                         text="dang mat on dinh %d, lambda_cr = %.2f" % (idx + 1, lam))

    def _legend(self, project, result):
        if result is None:
            return
        a = result.assessment
        w = max(self.winfo_width(), 100)
        lines = [
            "he so tai cho phep  %.2f" % a.lambda_allow,
            "quyet dinh boi      %s" % a.governed_by,
            "chuyen vi lon nhat  %.1f mm" % a.max_disp,
        ]
        for i, t in enumerate(lines):
            self.create_text(w - 10, 10 + 14 * i, anchor="ne", fill=TEXT,
                             font=("Consolas", 8), text=t)
