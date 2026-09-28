# -*- coding: utf-8 -*-
"""Giao diện Tkinter cho công cụ tính gia đỡ đường ống."""

from __future__ import annotations

import math
import tkinter as tk
import traceback
from tkinter import filedialog, messagebox, ttk

from . import advice as adv
from . import analysis as an
from . import data as dt
from . import pipe as pp
from . import report as rp
from . import sections as sc
from .draw import FrameCanvas

PAD = 8
MONO = ("Consolas", 9)


def _f(widget, default=0.0) -> float:
    """Đọc số từ ô nhập, chấp nhận cả dấu phẩy thập phân."""
    s = widget.get().strip().replace(",", ".")
    if not s:
        return default
    return float(s)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tính gia đỡ đường ống — phân tích phần tử hữu hạn")
        self.geometry("1440x900")
        self.minsize(1100, 700)

        try:
            ttk.Style().theme_use("vista")
        except tk.TclError:
            pass

        self.section_lib: dict[str, sc.SectionProps] = {}
        self.result: an.Result | None = None
        self.project: an.Project | None = None
        self.pipe_result: pp.PipeLoad | None = None
        self.span_result: pp.SpanResult | None = None

        self._seed_sections()
        self._build()
        self.load_example()

    # ==================================================================
    # khung giao diện
    # ==================================================================
    def _build(self):
        head = ttk.Frame(self, padding=(PAD, 6))
        head.pack(fill="x")
        ttk.Label(head, text="GIA ĐỠ ĐƯỜNG ỐNG",
                  font=("Segoe UI Semibold", 13)).pack(side="left")
        ttk.Label(head, text="  phần tử hữu hạn khung phẳng · kiểm tra ASD",
                  foreground="#666").pack(side="left")

        ttk.Button(head, text="Nạp ví dụ", command=self.load_example
                   ).pack(side="right", padx=3)
        ttk.Button(head, text="Lưu báo cáo…", command=self.save_report
                   ).pack(side="right", padx=3)
        ttk.Button(head, text="Tự chọn tiết diện", command=self.do_autosize
                   ).pack(side="right", padx=3)
        b = ttk.Button(head, text="TÍNH  (F5)", command=self.compute)
        b.pack(side="right", padx=8)
        self.bind("<F5>", lambda e: self.compute())

        pw = ttk.PanedWindow(self, orient="horizontal")
        pw.pack(fill="both", expand=True, padx=PAD, pady=(0, PAD))

        # Be rong YEU CAU cua o nhap lieu (bang + nhan wraplength) len toi
        # ~940 px, va ttk.PanedWindow khong bao gio thu mot o xuong duoi be
        # rong yeu cau cua no. Khoa be rong yeu cau lai de canvas co cho ve.
        left = ttk.Frame(pw, width=700, height=640)
        left.pack_propagate(False)
        right = ttk.Frame(pw, width=520, height=640)
        right.pack_propagate(False)
        pw.add(left, weight=3)
        pw.add(right, weight=4)
        # ttk chi ap dung `weight` khi nguoi dung keo hoac cua so doi kich thuoc;
        # vi tri ban dau lay theo be rong yeu cau cua tung o, ma bang nhap lieu
        # doi rat rong. Dat tay mot lan sau khi cua so da duoc ve.
        self._pw = pw
        self.after(120, self._place_sash)

        self.nb = ttk.Notebook(left)
        self.nb.pack(fill="both", expand=True)
        self._tab_pipe()
        self._tab_section()
        self._tab_frame()
        self._tab_result()
        self._tab_report()

        self.canvas = FrameCanvas(right)
        self.canvas.pack(fill="both", expand=True)

        opt = ttk.Frame(right)
        opt.pack(fill="x", pady=(4, 0))
        self.v_defl = tk.BooleanVar(value=True)
        self.v_mom = tk.BooleanVar(value=False)
        self.v_mode = tk.BooleanVar(value=False)
        for txt, var in (("Biến dạng", self.v_defl),
                         ("Biểu đồ moment", self.v_mom),
                         ("Dạng mất ổn định", self.v_mode)):
            ttk.Checkbutton(opt, text=txt, variable=var,
                            command=self._refresh_canvas).pack(side="left", padx=6)

        self.status = tk.StringVar(value="Sẵn sàng.")
        sb = ttk.Label(self, textvariable=self.status, relief="sunken",
                       anchor="w", padding=(6, 3))
        sb.pack(fill="x", side="bottom")

    def _place_sash(self):
        try:
            w = self._pw.winfo_width()
            if w > 200:
                self._pw.sashpos(0, int(w * 0.52))
        except tk.TclError:
            pass

    # ------------------------------------------------------------------
    def _tab_pipe(self):
        f = ttk.Frame(self.nb, padding=PAD)
        self.nb.add(f, text="1· Ống & môi chất")

        g = ttk.LabelFrame(f, text="Tiêu chuẩn áp dụng", padding=PAD)
        g.pack(fill="x")
        self.cb_stdgroup = ttk.Combobox(g, values=list(dt.STANDARDS.keys()),
                                        state="readonly", width=34)
        self.cb_stdgroup.set("LNG / NG - nha may, cong nghe")
        self.cb_stdgroup.grid(row=0, column=0, sticky="w")
        self.cb_stdgroup.bind("<<ComboboxSelected>>", lambda e: self._fill_std())
        self.cb_std = ttk.Combobox(g, state="readonly", width=30)
        self.cb_std.grid(row=0, column=1, sticky="w", padx=6)
        self.cb_std.bind("<<ComboboxSelected>>", lambda e: self._std_note())
        self.lb_std = ttk.Label(g, foreground="#555", wraplength=520,
                                justify="left")
        self.lb_std.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))
        self._fill_std()

        g = ttk.LabelFrame(f, text="Kích thước ống", padding=PAD)
        g.pack(fill="x", pady=(PAD, 0))
        ttk.Label(g, text="NPS").grid(row=0, column=0, sticky="w")
        self.cb_nps = ttk.Combobox(g, values=list(dt.PIPE_OD.keys()),
                                   state="readonly", width=9)
        self.cb_nps.set("6")
        self.cb_nps.grid(row=0, column=1, sticky="w")
        self.cb_nps.bind("<<ComboboxSelected>>", lambda e: self._fill_sched())

        ttk.Label(g, text="Schedule").grid(row=0, column=2, sticky="w", padx=(12, 0))
        self.cb_sch = ttk.Combobox(g, state="readonly", width=12)
        self.cb_sch.grid(row=0, column=3, sticky="w")
        self.cb_sch.bind("<<ComboboxSelected>>", lambda e: self._apply_sched())

        self.e_od = self._row(g, 1, 0, "OD [mm]", "168.3")
        self.e_tw = self._row(g, 1, 2, "Chiều dày t [mm]", "7.11")
        self.e_corr = self._row(g, 2, 0, "Dư ăn mòn [mm]", "0")
        self.e_extra = self._row(g, 2, 2, "Tải phụ [kg/m]", "0")
        ttk.Label(g, text="OD và t có thể sửa tay — bảng tra chỉ để điền nhanh.",
                  foreground="#777").grid(row=3, column=0, columnspan=4,
                                          sticky="w", pady=(4, 0))
        self._fill_sched()

        g = ttk.LabelFrame(f, text="Vật liệu ống & môi chất", padding=PAD)
        g.pack(fill="x", pady=(PAD, 0))
        ttk.Label(g, text="Vật liệu").grid(row=0, column=0, sticky="w")
        self.cb_pmat = ttk.Combobox(g, values=list(dt.PIPE_MATERIALS.keys()),
                                    state="readonly", width=40)
        self.cb_pmat.set("A312 TP304 / 304L (inox austenit)")
        self.cb_pmat.grid(row=0, column=1, columnspan=3, sticky="w")
        self.cb_pmat.bind("<<ComboboxSelected>>", lambda e: self._mat_note())
        self.lb_pmat = ttk.Label(g, foreground="#555", wraplength=520,
                                 justify="left")
        self.lb_pmat.grid(row=1, column=0, columnspan=4, sticky="w", pady=(2, 6))

        ttk.Label(g, text="Môi chất").grid(row=2, column=0, sticky="w")
        self.cb_fluid = ttk.Combobox(g, values=list(dt.FLUIDS.keys()),
                                     state="readonly", width=28)
        self.cb_fluid.set(dt.DEFAULT_FLUID)
        self.cb_fluid.grid(row=2, column=1, sticky="w")
        self.cb_fluid.bind("<<ComboboxSelected>>", lambda e: self._fluid_note())
        self.e_rhof = self._row(g, 2, 2, "ρ môi chất [kg/m³]", "450")
        self.lb_fluid = ttk.Label(g, foreground="#555", wraplength=520)
        self.lb_fluid.grid(row=3, column=0, columnspan=4, sticky="w")

        ttk.Label(g, text="Bảo ôn").grid(row=4, column=0, sticky="w", pady=(6, 0))
        self.cb_ins = ttk.Combobox(g, values=list(dt.INSULATION.keys()),
                                   state="readonly", width=28)
        self.cb_ins.set("Cellular glass (Foamglas)")
        self.cb_ins.grid(row=4, column=1, sticky="w", pady=(6, 0))
        self.cb_ins.bind("<<ComboboxSelected>>", lambda e: self._ins_note())
        self.e_tins = self._row(g, 4, 2, "Dày bảo ôn [mm]", "80")
        self._mat_note(); self._fluid_note(); self._ins_note()

        g = ttk.LabelFrame(f, text="Khoảng cách gối đỡ", padding=PAD)
        g.pack(fill="x", pady=(PAD, 0))
        ttk.Label(g, text="Sơ đồ").grid(row=0, column=0, sticky="w")
        self.cb_scheme = ttk.Combobox(g, values=list(pp.SPAN_SCHEMES.keys()),
                                      state="readonly", width=34)
        self.cb_scheme.set(pp.DEFAULT_SPAN_SCHEME)
        self.cb_scheme.grid(row=0, column=1, columnspan=3, sticky="w")
        self.e_sigall = self._row(g, 1, 0, "σ uốn cho phép [MPa]",
                                  str(pp.B31_1_SIGMA))
        self.e_sag = self._row(g, 1, 2, "Độ võng cho phép [mm]", str(pp.B31_1_SAG))
        ttk.Label(g, text="Mặc định 15,9 MPa và 2,5 mm là cơ sở của ASME B31.1 "
                          "Table 121.5.", foreground="#777", wraplength=520
                  ).grid(row=2, column=0, columnspan=4, sticky="w", pady=(4, 0))

        bar = ttk.Frame(f)
        bar.pack(fill="x", pady=(PAD, 0))
        ttk.Button(bar, text="Tính tải ống", command=self.calc_pipe
                   ).pack(side="left")
        ttk.Button(bar, text="→ Dùng làm lực tác dụng",
                   command=self.push_load).pack(side="left", padx=6)

        self.txt_pipe = tk.Text(f, height=13, width=1, font=MONO, wrap="word")
        self.txt_pipe.pack(fill="both", expand=True, pady=(PAD, 0))

    def _row(self, parent, r, c, label, default):
        ttk.Label(parent, text=label).grid(row=r, column=c, sticky="w",
                                           padx=(12 if c else 0, 0), pady=2)
        e = ttk.Entry(parent, width=12)
        e.insert(0, default)
        e.grid(row=r, column=c + 1, sticky="w", pady=2)
        return e

    # ------------------------------------------------------------------
    def _tab_section(self):
        f = ttk.Frame(self.nb, padding=PAD)
        self.nb.add(f, text="2· Tiết diện thép")

        g = ttk.LabelFrame(f, text="Thép kết cấu", padding=PAD)
        g.pack(fill="x")
        ttk.Label(g, text="Mác thép").grid(row=0, column=0, sticky="w")
        self.cb_steel = ttk.Combobox(g, values=list(dt.SUPPORT_STEEL.keys()),
                                     state="readonly", width=28)
        self.cb_steel.set(dt.DEFAULT_STEEL)
        self.cb_steel.grid(row=0, column=1, sticky="w")
        self.cb_steel.bind("<<ComboboxSelected>>", lambda e: self._steel_note())
        self.lb_steel = ttk.Label(g, foreground="#555", wraplength=520)
        self.lb_steel.grid(row=1, column=0, columnspan=4, sticky="w", pady=(2, 0))
        self._steel_note()

        g = ttk.LabelFrame(f, text="Định nghĩa tiết diện", padding=PAD)
        g.pack(fill="x", pady=(PAD, 0))
        ttk.Label(g, text="Dạng").grid(row=0, column=0, sticky="w")
        self.cb_shape = ttk.Combobox(g, values=list(sc.SHAPES.keys()),
                                     state="readonly", width=28)
        self.cb_shape.set("Hop vuong-CN (SHS / RHS)")
        self.cb_shape.grid(row=0, column=1, sticky="w")
        self.cb_shape.bind("<<ComboboxSelected>>", lambda e: self._shape_fields())

        ttk.Label(g, text="Kích thước có sẵn").grid(row=0, column=2, sticky="w",
                                                    padx=(12, 0))
        self.cb_preset = ttk.Combobox(g, state="readonly", width=22)
        self.cb_preset.grid(row=0, column=3, sticky="w")
        self.cb_preset.bind("<<ComboboxSelected>>", lambda e: self._apply_preset())

        self.dim_frame = ttk.Frame(g)
        self.dim_frame.grid(row=1, column=0, columnspan=4, sticky="w", pady=(6, 0))
        self.dim_entries: list[ttk.Entry] = []

        ttk.Label(g, text="Tên").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.e_secname = ttk.Entry(g, width=26)
        self.e_secname.grid(row=2, column=1, sticky="w", pady=(6, 0))
        ttk.Button(g, text="Tính & thêm vào thư viện", command=self.add_section
                   ).grid(row=2, column=2, columnspan=2, sticky="w",
                          padx=(12, 0), pady=(6, 0))
        ttk.Label(g, text=sc.PRESET_WARNING, foreground="#a15", wraplength=560,
                  justify="left").grid(row=3, column=0, columnspan=4,
                                       sticky="w", pady=(6, 0))
        self._shape_fields()

        g = ttk.LabelFrame(f, text="Thư viện tiết diện", padding=PAD)
        g.pack(fill="both", expand=True, pady=(PAD, 0))
        cols = ("ten", "A", "Ix", "Sx", "rmin", "kg")
        self.tv_sec = ttk.Treeview(g, columns=cols, show="headings", height=8)
        for c, t, w in (("ten", "Tên", 170), ("A", "A [mm²]", 80),
                        ("Ix", "Ix [mm⁴]", 100), ("Sx", "Sx [mm³]", 100),
                        ("rmin", "r min [mm]", 80), ("kg", "kg/m", 70)):
            self.tv_sec.heading(c, text=t)
            self.tv_sec.column(c, width=w, anchor="e" if c != "ten" else "w")
        self.tv_sec.pack(fill="both", expand=True, side="left")
        ttk.Button(g, text="Xoá", command=self.del_section).pack(side="left",
                                                                 padx=6, anchor="n")
        self.txt_sec = tk.Text(f, height=6, width=1, font=MONO)
        self.txt_sec.pack(fill="x", pady=(PAD, 0))
        self._refresh_sec_table()

    # ------------------------------------------------------------------
    def _tab_frame(self):
        f = ttk.Frame(self.nb, padding=PAD)
        self.nb.add(f, text="3· Khung support")

        top = ttk.Frame(f)
        top.pack(fill="x")
        ttk.Label(top, text="Đơn vị toạ độ").pack(side="left")
        self.cb_unit = ttk.Combobox(top, values=["mm", "m"], state="readonly",
                                    width=6)
        self.cb_unit.set("mm")
        self.cb_unit.pack(side="left", padx=6)
        ttk.Label(top, text="Chia lưới / thanh").pack(side="left", padx=(16, 4))
        self.e_nseg = ttk.Entry(top, width=5)
        self.e_nseg.insert(0, "4")
        self.e_nseg.pack(side="left")
        ttk.Label(top, text="K").pack(side="left", padx=(16, 4))
        self.e_kfac = ttk.Entry(top, width=5)
        self.e_kfac.insert(0, "1.0")
        self.e_kfac.pack(side="left")
        ttk.Label(top, text="Giới hạn chuyển vị [mm]").pack(side="left", padx=(16, 4))
        self.e_dlim = ttk.Entry(top, width=7)
        self.e_dlim.insert(0, "10")
        self.e_dlim.pack(side="left")
        self.v_sw = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="Trọng lượng bản thân",
                        variable=self.v_sw).pack(side="left", padx=12)
        self.v_buck = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="Phân tích ổn định",
                        variable=self.v_buck).pack(side="left")

        # ---- thanh ----
        g = ttk.LabelFrame(f, text="Thanh support — mỗi dòng một thanh, "
                                   "toạ độ trùng nhau thì nối với nhau", padding=PAD)
        g.pack(fill="both", expand=True, pady=(PAD, 0))
        cols = ("nhan", "x1", "y1", "x2", "y2", "L", "sec", "exp")
        self.tv_mem = ttk.Treeview(g, columns=cols, show="headings", height=7)
        for c, t, w in (("nhan", "Nhãn", 60), ("x1", "x1", 70), ("y1", "y1", 70),
                        ("x2", "x2", 70), ("y2", "y2", 70), ("L", "L [mm]", 80),
                        ("sec", "Tiết diện", 150), ("exp", "Dự kiến", 80)):
            self.tv_mem.heading(c, text=t)
            self.tv_mem.column(c, width=w, anchor="w" if c in ("nhan", "sec") else "e")
        self.tv_mem.pack(fill="both", expand=True)
        self.tv_mem.bind("<<TreeviewSelect>>", lambda e: self._load_mem_form())

        fr = ttk.Frame(g)
        fr.pack(fill="x", pady=(6, 0))
        self.m_lab = self._mini(fr, "Nhãn", 7, "A")
        self.m_x1 = self._mini(fr, "x1", 8, "0")
        self.m_y1 = self._mini(fr, "y1", 8, "0")
        self.m_x2 = self._mini(fr, "x2", 8, "0")
        self.m_y2 = self._mini(fr, "y2", 8, "1000")
        ttk.Label(fr, text="Tiết diện").pack(side="left", padx=(8, 2))
        self.m_sec = ttk.Combobox(fr, state="readonly", width=20)
        self.m_sec.pack(side="left")
        ttk.Label(fr, text="Dự kiến").pack(side="left", padx=(8, 2))
        self.m_exp = ttk.Combobox(fr, values=["Tu dong", "Keo", "Nen"],
                                  state="readonly", width=8)
        self.m_exp.set("Tu dong")
        self.m_exp.pack(side="left")
        fr2 = ttk.Frame(g)
        fr2.pack(fill="x", pady=(4, 0))
        ttk.Button(fr2, text="Thêm", command=self.add_member).pack(side="left")
        ttk.Button(fr2, text="Cập nhật", command=self.upd_member).pack(side="left", padx=4)
        ttk.Button(fr2, text="Xoá", command=self.del_member).pack(side="left")

        # ---- lực ----
        g = ttk.LabelFrame(f, text="Lực tác dụng — điểm đặt lực phải nằm TRÊN "
                                   "một thanh", padding=PAD)
        g.pack(fill="both", expand=True, pady=(PAD, 0))
        cols = ("nhan", "x", "y", "N", "goc", "kieu")
        self.tv_load = ttk.Treeview(g, columns=cols, show="headings", height=4)
        for c, t, w in (("nhan", "Nhãn", 60), ("x", "x", 80), ("y", "y", 80),
                        ("N", "Độ lớn [N]", 100), ("goc", "Góc [°]", 70),
                        ("kieu", "Hướng", 110)):
            self.tv_load.heading(c, text=t)
            self.tv_load.column(c, width=w, anchor="w" if c in ("nhan", "kieu") else "e")
        self.tv_load.pack(fill="both", expand=True)
        self.tv_load.bind("<<TreeviewSelect>>", lambda e: self._load_load_form())

        fr = ttk.Frame(g)
        fr.pack(fill="x", pady=(6, 0))
        self.l_lab = self._mini(fr, "Nhãn", 7, "C")
        self.l_x = self._mini(fr, "x", 8, "0")
        self.l_y = self._mini(fr, "y", 8, "0")
        self.l_N = self._mini(fr, "Độ lớn [N]", 10, "5000")
        self.l_ang = self._mini(fr, "Góc [°]", 7, "-90")
        ttk.Button(fr, text="↓ Thẳng đứng xuống",
                   command=lambda: self._set_ang(-90)).pack(side="left", padx=(8, 2))
        ttk.Button(fr, text="→ Ngang",
                   command=lambda: self._set_ang(0)).pack(side="left")
        fr2 = ttk.Frame(g)
        fr2.pack(fill="x", pady=(4, 0))
        ttk.Button(fr2, text="Thêm", command=self.add_load).pack(side="left")
        ttk.Button(fr2, text="Cập nhật", command=self.upd_load).pack(side="left", padx=4)
        ttk.Button(fr2, text="Xoá", command=self.del_load).pack(side="left")
        ttk.Label(fr2, text="Góc đo từ trục +X ngược chiều kim đồng hồ: "
                            "−90° = xuống, 0° = sang phải.",
                  foreground="#777").pack(side="left", padx=12)

        # ---- gối tựa ----
        g = ttk.LabelFrame(f, text="Gối tựa — điểm liên kết với kết cấu đỡ",
                           padding=PAD)
        g.pack(fill="both", expand=True, pady=(PAD, 0))
        cols = ("x", "y", "kieu")
        self.tv_sup = ttk.Treeview(g, columns=cols, show="headings", height=3)
        for c, t, w in (("x", "x", 90), ("y", "y", 90), ("kieu", "Loại", 160)):
            self.tv_sup.heading(c, text=t)
            self.tv_sup.column(c, width=w, anchor="w" if c == "kieu" else "e")
        self.tv_sup.pack(fill="both", expand=True)
        self.tv_sup.bind("<<TreeviewSelect>>", lambda e: self._load_sup_form())

        fr = ttk.Frame(g)
        fr.pack(fill="x", pady=(6, 0))
        self.s_x = self._mini(fr, "x", 8, "0")
        self.s_y = self._mini(fr, "y", 8, "0")
        ttk.Label(fr, text="Loại").pack(side="left", padx=(8, 2))
        self.s_kind = ttk.Combobox(fr, state="readonly", width=16,
                                   values=["Ngam", "Khop", "Con lan dung",
                                           "Con lan ngang"])
        self.s_kind.set("Ngam")
        self.s_kind.pack(side="left")
        ttk.Button(fr, text="Thêm", command=self.add_sup).pack(side="left", padx=(8, 2))
        ttk.Button(fr, text="Cập nhật", command=self.upd_sup).pack(side="left")
        ttk.Button(fr, text="Xoá", command=self.del_sup).pack(side="left", padx=2)

    def _mini(self, parent, label, width, default):
        ttk.Label(parent, text=label).pack(side="left", padx=(8, 2))
        e = ttk.Entry(parent, width=width)
        e.insert(0, default)
        e.pack(side="left")
        return e

    def _set_ang(self, a):
        self.l_ang.delete(0, "end")
        self.l_ang.insert(0, str(a))

    # ------------------------------------------------------------------
    def _tab_result(self):
        f = ttk.Frame(self.nb, padding=PAD)
        self.nb.add(f, text="4· Kết quả")

        self.lb_verdict = ttk.Label(f, text="Chưa tính.",
                                    font=("Segoe UI Semibold", 12))
        self.lb_verdict.pack(anchor="w")
        self.lb_sub = ttk.Label(f, foreground="#555", wraplength=620,
                                justify="left")
        self.lb_sub.pack(anchor="w", pady=(2, PAD))

        cols = ("ten", "tn", "N", "M", "V", "klr", "u")
        self.tv_res = ttk.Treeview(f, columns=cols, show="headings", height=7)
        for c, t, w in (("ten", "Thanh", 80), ("tn", "Kéo/Nén", 70),
                        ("N", "N [N]", 90), ("M", "M [N·mm]", 110),
                        ("V", "V [N]", 80), ("klr", "KL/r", 60),
                        ("u", "Sử dụng", 80)):
            self.tv_res.heading(c, text=t)
            self.tv_res.column(c, width=w, anchor="w" if c == "ten" else "e")
        self.tv_res.pack(fill="x")

        ttk.Label(f, text="Nhận xét & đề xuất",
                  font=("Segoe UI Semibold", 10)).pack(anchor="w", pady=(PAD, 2))
        self.txt_adv = tk.Text(f, font=("Segoe UI", 9), wrap="word", height=18, width=1)
        self.txt_adv.pack(fill="both", expand=True)
        self.txt_adv.tag_configure("hi", foreground="#b3261e",
                                   font=("Segoe UI Semibold", 9))
        self.txt_adv.tag_configure("mid", foreground="#8a6100",
                                   font=("Segoe UI Semibold", 9))
        self.txt_adv.tag_configure("info", foreground="#15603a",
                                   font=("Segoe UI Semibold", 9))
        self.txt_adv.tag_configure("body", foreground="#333")

    def _tab_report(self):
        f = ttk.Frame(self.nb, padding=PAD)
        self.nb.add(f, text="5· Báo cáo")
        self.txt_rep = tk.Text(f, font=MONO, wrap="none", width=1)
        sy = ttk.Scrollbar(f, orient="vertical", command=self.txt_rep.yview)
        sx = ttk.Scrollbar(f, orient="horizontal", command=self.txt_rep.xview)
        self.txt_rep.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.txt_rep.grid(row=0, column=0, sticky="nsew")
        sy.grid(row=0, column=1, sticky="ns")
        sx.grid(row=1, column=0, sticky="ew")
        f.rowconfigure(0, weight=1)
        f.columnconfigure(0, weight=1)

    # ==================================================================
    # ghi chú động
    # ==================================================================
    def _fill_std(self):
        grp = dt.STANDARDS[self.cb_stdgroup.get()]
        self.cb_std["values"] = [s for s, _ in grp]
        self.cb_std.set(grp[0][0])
        self._std_note()

    def _std_note(self):
        for grp in dt.STANDARDS.values():
            for code, desc in grp:
                if code == self.cb_std.get():
                    self.lb_std.config(text=desc)
                    return

    def _mat_note(self):
        v = dt.PIPE_MATERIALS.get(self.cb_pmat.get())
        if v:
            self.lb_pmat.config(text=v[2])

    def _fluid_note(self):
        v = dt.FLUIDS.get(self.cb_fluid.get())
        if v:
            self.e_rhof.delete(0, "end")
            self.e_rhof.insert(0, "%g" % v[0])
            self.lb_fluid.config(text=v[1])

    def _ins_note(self):
        v = dt.INSULATION.get(self.cb_ins.get())
        if v and v[0] == 0:
            self.e_tins.delete(0, "end")
            self.e_tins.insert(0, "0")

    def _steel_note(self):
        v = dt.SUPPORT_STEEL.get(self.cb_steel.get())
        if v:
            self.lb_steel.config(
                text="Fy = %.0f MPa · Fu = %.0f MPa · E = %.0f MPa. %s"
                     % (v[0], v[1], v[2], v[4]))

    def _fill_sched(self):
        nps = self.cb_nps.get()
        vals = dt.schedules_for(nps)
        self.cb_sch["values"] = vals
        if vals:
            self.cb_sch.set("40 (STD)" if "40 (STD)" in vals else vals[0])
        self._apply_sched()

    def _apply_sched(self):
        nps, sch = self.cb_nps.get(), self.cb_sch.get()
        od = dt.PIPE_OD.get(nps)
        t = dt.PIPE_WALL.get(nps, {}).get(sch)
        if od:
            self.e_od.delete(0, "end")
            self.e_od.insert(0, "%g" % od)
        if t:
            self.e_tw.delete(0, "end")
            self.e_tw.insert(0, "%g" % t)

    # ==================================================================
    # tiết diện
    # ==================================================================
    def _seed_sections(self):
        for name, shape, dims in (("SHS 100x100x5", "rect_hss", [100, 100, 5]),
                                  ("L75x75x6", "angle", [75, 75, 6]),
                                  ("C100x50x5x6", "channel", [100, 50, 5, 6]),
                                  ("H150x150x7x10", "i_beam", [150, 150, 7, 10])):
            self.section_lib[name] = sc.build(shape, dims, name)

    def _shape_fields(self):
        for w in self.dim_frame.winfo_children():
            w.destroy()
        self.dim_entries = []
        shape, labels = sc.SHAPES[self.cb_shape.get()]
        for lab in labels:
            ttk.Label(self.dim_frame, text=lab + " [mm]").pack(side="left", padx=(0, 3))
            e = ttk.Entry(self.dim_frame, width=8)
            e.pack(side="left", padx=(0, 10))
            self.dim_entries.append(e)
        defaults = {"round_hss": [114.3, 6], "rect_hss": [100, 100, 5],
                    "i_beam": [150, 150, 7, 10], "channel": [100, 50, 5, 6],
                    "angle": [75, 75, 6], "tee": [100, 100, 6, 8],
                    "flat_bar": [100, 10], "solid_round": [40]}
        for e, v in zip(self.dim_entries, defaults.get(shape, [])):
            e.insert(0, str(v))
        # preset khớp dạng này
        keys = [k for k, lst in sc.PRESETS.items()
                if lst and lst[0][1] == shape]
        vals = []
        for k in keys:
            vals += [n for n, _, _ in sc.PRESETS[k]]
        self.cb_preset["values"] = vals
        self.cb_preset.set("")

    def _apply_preset(self):
        want = self.cb_preset.get()
        for lst in sc.PRESETS.values():
            for name, shape, dims in lst:
                if name == want:
                    for e, v in zip(self.dim_entries, dims):
                        e.delete(0, "end")
                        e.insert(0, str(v))
                    self.e_secname.delete(0, "end")
                    self.e_secname.insert(0, name)
                    return

    def add_section(self):
        try:
            shape, _ = sc.SHAPES[self.cb_shape.get()]
            dims = [_f(e) for e in self.dim_entries]
            name = self.e_secname.get().strip()
            sp = sc.build(shape, dims, name)
            self.section_lib[sp.name] = sp
            self._refresh_sec_table()
            self.txt_sec.delete("1.0", "end")
            self.txt_sec.insert("1.0", sp.name + "\n" + sp.summary()
                                + ("\n" + sp.note if sp.note else ""))
            self.status.set("Đã thêm tiết diện %s." % sp.name)
        except Exception as exc:
            messagebox.showerror("Lỗi tiết diện", str(exc))

    def del_section(self):
        for i in self.tv_sec.selection():
            name = self.tv_sec.item(i, "values")[0]
            self.section_lib.pop(name, None)
        self._refresh_sec_table()

    def _refresh_sec_table(self):
        self.tv_sec.delete(*self.tv_sec.get_children())
        for name, sp in self.section_lib.items():
            self.tv_sec.insert("", "end", values=(
                name, "%.0f" % sp.A, "%.3e" % sp.Ix, "%.3e" % sp.Sx,
                "%.1f" % sc.r_min_effective(sp), "%.2f" % sp.mass_per_m()))
        names = list(self.section_lib.keys())
        if hasattr(self, "m_sec"):
            self.m_sec["values"] = names
            if names and not self.m_sec.get():
                self.m_sec.set(names[0])

    # ==================================================================
    # bảng khung
    # ==================================================================
    def _u(self) -> float:
        return 1000.0 if self.cb_unit.get() == "m" else 1.0

    def _mem_rows(self):
        return [self.tv_mem.item(i, "values") for i in self.tv_mem.get_children()]

    def add_member(self):
        try:
            k = self._u()
            x1, y1 = _f(self.m_x1) * k, _f(self.m_y1) * k
            x2, y2 = _f(self.m_x2) * k, _f(self.m_y2) * k
            L = math.hypot(x2 - x1, y2 - y1)
            if L < 1.0:
                raise ValueError("Chiều dài thanh phải lớn hơn 0.")
            if not self.m_sec.get():
                raise ValueError("Chưa chọn tiết diện.")
            self.tv_mem.insert("", "end", values=(
                self.m_lab.get() or "T%d" % (len(self._mem_rows()) + 1),
                self.m_x1.get(), self.m_y1.get(), self.m_x2.get(), self.m_y2.get(),
                "%.0f" % L, self.m_sec.get(), self.m_exp.get()))
            self._refresh_canvas()
        except Exception as exc:
            messagebox.showerror("Lỗi nhập thanh", str(exc))

    def upd_member(self):
        sel = self.tv_mem.selection()
        if not sel:
            return
        k = self._u()
        L = math.hypot(_f(self.m_x2) * k - _f(self.m_x1) * k,
                       _f(self.m_y2) * k - _f(self.m_y1) * k)
        self.tv_mem.item(sel[0], values=(
            self.m_lab.get(), self.m_x1.get(), self.m_y1.get(),
            self.m_x2.get(), self.m_y2.get(), "%.0f" % L,
            self.m_sec.get(), self.m_exp.get()))
        self._refresh_canvas()

    def del_member(self):
        for i in self.tv_mem.selection():
            self.tv_mem.delete(i)
        self._refresh_canvas()

    def _load_mem_form(self):
        sel = self.tv_mem.selection()
        if not sel:
            return
        v = self.tv_mem.item(sel[0], "values")
        for e, val in ((self.m_lab, v[0]), (self.m_x1, v[1]), (self.m_y1, v[2]),
                       (self.m_x2, v[3]), (self.m_y2, v[4])):
            e.delete(0, "end")
            e.insert(0, val)
        self.m_sec.set(v[6])
        self.m_exp.set(v[7])

    def add_load(self):
        try:
            ang = _f(self.l_ang, -90)
            kind = "xuống" if abs(ang + 90) < 1 else ("ngang" if abs(ang) < 1 else "%g°" % ang)
            self.tv_load.insert("", "end", values=(
                self.l_lab.get() or "P%d" % (len(self.tv_load.get_children()) + 1),
                self.l_x.get(), self.l_y.get(), self.l_N.get(),
                self.l_ang.get(), kind))
            self._refresh_canvas()
        except Exception as exc:
            messagebox.showerror("Lỗi nhập lực", str(exc))

    def upd_load(self):
        sel = self.tv_load.selection()
        if not sel:
            return
        ang = _f(self.l_ang, -90)
        kind = "xuống" if abs(ang + 90) < 1 else ("ngang" if abs(ang) < 1 else "%g°" % ang)
        self.tv_load.item(sel[0], values=(
            self.l_lab.get(), self.l_x.get(), self.l_y.get(),
            self.l_N.get(), self.l_ang.get(), kind))
        self._refresh_canvas()

    def del_load(self):
        for i in self.tv_load.selection():
            self.tv_load.delete(i)
        self._refresh_canvas()

    def _load_load_form(self):
        sel = self.tv_load.selection()
        if not sel:
            return
        v = self.tv_load.item(sel[0], "values")
        for e, val in ((self.l_lab, v[0]), (self.l_x, v[1]), (self.l_y, v[2]),
                       (self.l_N, v[3]), (self.l_ang, v[4])):
            e.delete(0, "end")
            e.insert(0, val)

    def add_sup(self):
        self.tv_sup.insert("", "end", values=(self.s_x.get(), self.s_y.get(),
                                              self.s_kind.get()))
        self._refresh_canvas()

    def upd_sup(self):
        sel = self.tv_sup.selection()
        if sel:
            self.tv_sup.item(sel[0], values=(self.s_x.get(), self.s_y.get(),
                                             self.s_kind.get()))
            self._refresh_canvas()

    def del_sup(self):
        for i in self.tv_sup.selection():
            self.tv_sup.delete(i)
        self._refresh_canvas()

    def _load_sup_form(self):
        sel = self.tv_sup.selection()
        if not sel:
            return
        v = self.tv_sup.item(sel[0], "values")
        for e, val in ((self.s_x, v[0]), (self.s_y, v[1])):
            e.delete(0, "end")
            e.insert(0, val)
        self.s_kind.set(v[2])

    # ==================================================================
    # tính toán
    # ==================================================================
    def calc_pipe(self):
        try:
            rho_p = dt.PIPE_MATERIALS[self.cb_pmat.get()][0]
            E_p = dt.PIPE_MATERIALS[self.cb_pmat.get()][1]
            rho_i = dt.INSULATION[self.cb_ins.get()][0]
            pl = pp.pipe_load(_f(self.e_od), _f(self.e_tw), rho_p,
                              _f(self.e_rhof), _f(self.e_tins), rho_i,
                              _f(self.e_corr), _f(self.e_extra))
            sr = pp.max_span(pl.w_total, pl.Z, pl.I, E_p,
                             _f(self.e_sigall, pp.B31_1_SIGMA),
                             _f(self.e_sag, pp.B31_1_SAG),
                             self.cb_scheme.get())
            self.pipe_result, self.span_result = pl, sr

            t = ["TẢI TRỌNG ĐƯỜNG ỐNG", "-" * 62,
                 "%-26s %12s %12s" % ("Thành phần", "N/mm", "kg/m")]
            for name, w, kg in pl.breakdown():
                t.append("%-26s %12.4f %12.2f" % (name, w, kg))
            t += ["", "Đặc trưng tiết diện ống (đã trừ ăn mòn):",
                  "  A = %.0f mm²   I = %.4e mm⁴   Z = %.4e mm³"
                  % (pl.A_metal, pl.I, pl.Z),
                  "", "KHOẢNG CÁCH GỐI ĐỠ", "-" * 62,
                  "  Sơ đồ                 : %s" % sr.scheme,
                  "  Theo ứng suất (%.1f MPa): %8.0f mm" % (sr.sigma_allow, sr.L_stress),
                  "  Theo độ võng  (%.1f mm) : %8.0f mm" % (sr.sag_allow, sr.L_defl),
                  "  → CHỌN                : %8.0f mm  (quyết định bởi %s)"
                  % (sr.L_max, sr.governed_by),
                  "", "PHẢN LỰC MỘT GỐI ĐỠ", "-" * 62,
                  "  N = w × L = %.4f × %.0f = %.0f N = %.2f kN"
                  % (pl.w_total, sr.L_max, pp.support_reaction(pl.w_total, sr.L_max),
                     pp.support_reaction(pl.w_total, sr.L_max) / 1000.0),
                  "", dt.DISCLAIMER]
            self.txt_pipe.delete("1.0", "end")
            self.txt_pipe.insert("1.0", "\n".join(t))
            self.status.set("Đã tính tải ống.")
        except Exception as exc:
            messagebox.showerror("Lỗi tính ống", str(exc))

    def push_load(self):
        if not self.pipe_result or not self.span_result:
            self.calc_pipe()
        if not self.pipe_result:
            return
        N = pp.support_reaction(self.pipe_result.w_total, self.span_result.L_max)
        self.l_N.delete(0, "end")
        self.l_N.insert(0, "%.0f" % N)
        self._set_ang(-90)
        self.nb.select(2)
        self.status.set("Đã đưa N = %.0f N sang ô lực. Đặt toạ độ rồi bấm Thêm." % N)

    def _gather(self) -> an.Project:
        k = self._u()
        members = []
        for v in self._mem_rows():
            sp = self.section_lib.get(v[6])
            if sp is None:
                raise an.InputError("Thanh %s dùng tiết diện %r không còn trong "
                                    "thư viện." % (v[0], v[6]))
            members.append(an.MemberIn(
                float(v[1].replace(",", ".")) * k, float(v[2].replace(",", ".")) * k,
                float(v[3].replace(",", ".")) * k, float(v[4].replace(",", ".")) * k,
                sp, v[7], v[0]))
        loads = []
        for i in self.tv_load.get_children():
            v = self.tv_load.item(i, "values")
            loads.append(an.LoadIn(float(v[1].replace(",", ".")) * k,
                                   float(v[2].replace(",", ".")) * k,
                                   float(v[3].replace(",", ".")),
                                   float(v[4].replace(",", ".")), v[0]))
        sups = []
        for i in self.tv_sup.get_children():
            v = self.tv_sup.item(i, "values")
            sups.append(an.SupportIn(float(v[0].replace(",", ".")) * k,
                                     float(v[1].replace(",", ".")) * k, v[2]))

        st = dt.SUPPORT_STEEL[self.cb_steel.get()]
        return an.Project(members, loads, sups, Fy=st[0], E=st[2], rho_steel=st[3],
                          nseg=int(_f(self.e_nseg, 4)),
                          K_factor=_f(self.e_kfac, 1.0),
                          disp_limit=_f(self.e_dlim, 0.0),
                          self_weight=self.v_sw.get(),
                          do_buckling=self.v_buck.get())

    def compute(self):
        try:
            self.status.set("Đang giải…")
            self.update_idletasks()
            p = self._gather()
            r = an.run(p)
        except an.InputError as exc:
            messagebox.showwarning("Dữ liệu chưa hợp lệ", str(exc))
            self.status.set("Dừng: dữ liệu chưa hợp lệ.")
            return
        except Exception as exc:
            messagebox.showerror("Lỗi khi giải",
                                 "%s\n\n%s" % (exc, traceback.format_exc()))
            self.status.set("Lỗi.")
            return

        self.project, self.result = p, r
        self._show_result()
        self._refresh_canvas()
        self.nb.select(3)
        self.status.set("Xong: %d phần tử, %d nút."
                        % (len(r.model.elements), len(r.model.nodes)))

    def _show_result(self):
        p, r = self.project, self.result
        a = r.assessment
        ok = a.lambda_allow >= 1.0 and a.disp_ok
        self.lb_verdict.config(
            text=("ĐẠT — hệ số dư tải %.2f" % a.lambda_allow) if ok
            else ("KHÔNG ĐẠT — chỉ đạt %.0f%% tải yêu cầu" % (a.lambda_allow * 100)),
            foreground="#15603a" if ok else "#b3261e")

        tot = sum(l.magnitude for l in p.loads)
        self.lb_sub.config(text=(
            "Tải đang xét %.2f kN → tải tối đa chịu được %.2f kN. "
            "Quyết định bởi: %s. Chuyển vị lớn nhất %.1f mm."
            % (tot / 1000, tot * a.lambda_allow / 1000, a.governed_by, a.max_disp)))

        self.tv_res.delete(*self.tv_res.get_children())
        for c in a.members:
            self.tv_res.insert("", "end", values=(
                c.name, c.action, "%.0f" % c.N, "%.3e" % c.M, "%.0f" % c.V,
                "%.1f" % c.slenderness, "%.0f%%" % (c.utilization * 100)))

        dT = -162.0 if "LNG" in self.cb_fluid.get() else 0.0
        run_m = (self.span_result.L_max / 1000.0 * 10) if self.span_result else 0.0
        items = adv.all_advice(p, r, self.cb_fluid.get(), self.cb_pmat.get(),
                               dT, run_m)
        self.txt_adv.delete("1.0", "end")
        tagmap = {"!": "hi", "*": "mid", "-": "info"}
        for lv, title, body in items:
            self.txt_adv.insert("end", "● " + title + "\n", tagmap.get(lv, "info"))
            if body:
                self.txt_adv.insert("end", "   " + body + "\n", "body")
            self.txt_adv.insert("end", "\n")

        pinfo = ""
        if self.pipe_result and self.span_result:
            pl, sr = self.pipe_result, self.span_result
            pinfo = ("Ong  : OD %.1f x t %.2f mm, %s\n"
                     "Moi chat: %s\nBao on : %s day %.0f mm\n"
                     "Tai phan bo w = %.4f N/mm (%.2f kg/m)\n"
                     "Khoang cach goi do chon %.0f mm (quyet dinh boi %s)\n"
                     "Phan luc mot goi N = %.0f N\n"
                     % (pl.OD, pl.t_corroded, self.cb_pmat.get(),
                        self.cb_fluid.get(), self.cb_ins.get(), _f(self.e_tins),
                        pl.w_total, pl.kg_per_m(pl.w_total),
                        sr.L_max, sr.governed_by,
                        pp.support_reaction(pl.w_total, sr.L_max)))
        sinfo = "".join("  %-16s %s\n" % (n, s.summary().replace("\n", "\n" + " " * 19))
                        for n, s in self.section_lib.items()
                        if any(m.section.name == n for m in p.members))
        self.txt_rep.delete("1.0", "end")
        self.txt_rep.insert("1.0", rp.build(p, r, items, pinfo, sinfo))

    def _refresh_canvas(self):
        self.canvas.show_deflection = self.v_defl.get()
        self.canvas.show_moment = self.v_mom.get()
        self.canvas.show_mode = self.v_mode.get()
        try:
            p = self.project if self.result else self._gather()
        except Exception:
            p = self.project
        self.canvas.set_data(p, self.result if p is self.project else None)

    # ==================================================================
    def do_autosize(self):
        try:
            p = self._gather()
        except Exception as exc:
            messagebox.showwarning("Dữ liệu chưa hợp lệ", str(exc))
            return
        cands = list(self.section_lib.values())
        if len(cands) < 2:
            messagebox.showinfo(
                "Cần thêm tiết diện",
                "Thư viện chỉ có %d tiết diện. Hãy thêm vài phương án ở tab "
                "'Tiết diện thép' rồi chạy lại — công cụ sẽ giải lại toàn bộ "
                "bài toán PTHH cho từng phương án và chọn cái nhẹ nhất còn đạt."
                % len(cands))
            return
        self.status.set("Đang thử %d tiết diện…" % len(cands))
        self.update_idletasks()
        try:
            res = an.auto_size(p, cands)
        except Exception as exc:
            messagebox.showerror("Lỗi", str(exc))
            return

        win = tk.Toplevel(self)
        win.title("Tự chọn tiết diện")
        win.geometry("760x420")
        ttk.Label(win, text="Mỗi phương án được giải lại toàn bộ bài toán PTHH "
                            "(đổi độ cứng sẽ phân bố lại nội lực).",
                  foreground="#555", padding=8).pack(anchor="w")
        cols = ("ten", "kg", "lam", "u", "kl")
        tv = ttk.Treeview(win, columns=cols, show="headings")
        for c, t, w in (("ten", "Tiết diện", 200), ("kg", "kg/m", 80),
                        ("lam", "Hệ số tải", 90), ("u", "Sử dụng", 90),
                        ("kl", "Kết luận", 260)):
            tv.heading(c, text=t)
            tv.column(c, width=w, anchor="w" if c in ("ten", "kl") else "e")
        tv.pack(fill="both", expand=True, padx=8, pady=8)

        best = None
        for sp, r, ok, err in res:
            if r is None:
                tv.insert("", "end", values=(sp.name, "%.2f" % sp.mass_per_m(),
                                             "-", "-", "Không giải được: " + err[:60]))
                continue
            u = r.assessment.governing.utilization if r.assessment.governing else 0
            verdict = "ĐẠT" if ok else "không đạt"
            if ok and best is None:
                best = sp
                verdict = "ĐẠT — nhẹ nhất"
            tv.insert("", "end", values=(
                sp.name, "%.2f" % sp.mass_per_m(),
                "%.2f" % r.assessment.lambda_allow, "%.0f%%" % (u * 100), verdict))

        msg = ("Phương án nhẹ nhất còn đạt: %s (%.2f kg/m)" % (best.name, best.mass_per_m())
               if best else "Không tiết diện nào trong thư viện đạt — cần tăng kích thước "
                            "hoặc đổi sơ đồ (thêm thanh chéo).")
        ttk.Label(win, text=msg, font=("Segoe UI Semibold", 10),
                  padding=8, wraplength=720, justify="left").pack(anchor="w")
        self.status.set("Đã thử %d tiết diện." % len(res))

    def save_report(self):
        if not self.result:
            messagebox.showinfo("Chưa có kết quả", "Bấm TÍNH trước đã.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Văn bản", "*.txt")],
            initialfile="bao_cao_gia_do.txt")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.txt_rep.get("1.0", "end"))
        self.status.set("Đã lưu %s" % path)

    # ==================================================================
    def load_example(self):
        """Ví dụ: đúng sơ đồ trong đề bài, nhưng điểm đặt lực đưa về nằm trên thanh."""
        self.cb_unit.set("m")
        self.tv_mem.delete(*self.tv_mem.get_children())
        self.tv_load.delete(*self.tv_load.get_children())
        self.tv_sup.delete(*self.tv_sup.get_children())
        self._refresh_sec_table()

        rows = [("A", "1", "1", "1", "5", "SHS 100x100x5", "Tu dong"),
                ("B", "1", "5", "4", "5", "SHS 100x100x5", "Tu dong"),
                ("C-giang", "1", "3", "3", "5", "L75x75x6", "Nen")]
        for lab, x1, y1, x2, y2, sec, exp in rows:
            L = math.hypot((float(x2) - float(x1)) * 1000,
                           (float(y2) - float(y1)) * 1000)
            self.tv_mem.insert("", "end", values=(lab, x1, y1, x2, y2,
                                                  "%.0f" % L, sec, exp))
        self.tv_load.insert("", "end", values=("P", "3", "5", "5000", "-90", "xuống"))
        self.tv_sup.insert("", "end", values=("1", "1", "Ngam"))
        self.tv_sup.insert("", "end", values=("1", "3", "Khop"))
        self._refresh_canvas()
        self.status.set("Đã nạp ví dụ (đơn vị mét). Bấm TÍNH.")


def main():
    App().mainloop()
