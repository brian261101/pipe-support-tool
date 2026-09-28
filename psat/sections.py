"""Dac trung hinh hoc tiet dien thep.

Moi dac trung deu duoc TINH TU KICH THUOC ma nguoi dung nhap, khong tra bang.
Nho vay khong co so lieu nao bi bia ra: nhap dung kich thuoc thi ra dung
dac trung. Cac "preset" phia duoi chi dien san kich thuoc danh nghia - van
phai doi chieu catalogue cua nha san xuat truoc khi dung cho thiet ke.

Bo qua ban kinh luon goc va ban kinh vat meo -> ket qua thien ve AN TOAN
(A, I nho hon thuc te mot chut).

Don vi: mm, mm^2, mm^4, mm^3.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class SectionProps:
    name: str
    shape: str
    A: float            # dien tich                      mm^2
    Ix: float           # moment quan tinh truc khoe     mm^4
    Iy: float           # moment quan tinh truc yeu      mm^4
    Sx: float           # moment khang uon dan hoi x     mm^3
    Sy: float
    Zx: float           # moment khang uon deo x         mm^3
    Zy: float
    Av: float           # dien tich chiu cat (truc khoe) mm^2
    h: float            # chieu cao bao                  mm
    b: float            # chieu rong bao                 mm
    closed: bool = False        # tiet dien kin (ong, hop)
    note: str = ""

    @property
    def rx(self) -> float:
        return math.sqrt(self.Ix / self.A) if self.A > 0 else 0.0

    @property
    def ry(self) -> float:
        return math.sqrt(self.Iy / self.A) if self.A > 0 else 0.0

    @property
    def rmin(self) -> float:
        return min(self.rx, self.ry)

    @property
    def Imin(self) -> float:
        return min(self.Ix, self.Iy)

    def mass_per_m(self, rho: float = 7850.0) -> float:
        """kg/m, rho theo kg/m^3."""
        return self.A * 1e-6 * rho

    def summary(self) -> str:
        return (
            "A = %.0f mm2   Ix = %.3e mm4   Iy = %.3e mm4\n"
            "Sx = %.3e mm3  Sy = %.3e mm3\n"
            "rx = %.1f mm   ry = %.1f mm   r_min = %.1f mm\n"
            "khoi luong = %.2f kg/m"
            % (self.A, self.Ix, self.Iy, self.Sx, self.Sy,
               self.rx, self.ry, self.rmin, self.mass_per_m())
        )


# --------------------------------------------------------------------------
# cac ham tinh
# --------------------------------------------------------------------------
def round_hss(D: float, t: float, name: str = "") -> SectionProps:
    """Ong tron / round HSS. D = duong kinh ngoai."""
    if t <= 0 or D <= 2 * t:
        raise ValueError("Ong tron: can D > 2t va t > 0.")
    d = D - 2 * t
    A = math.pi / 4 * (D ** 2 - d ** 2)
    I = math.pi / 64 * (D ** 4 - d ** 4)
    S = I / (D / 2)
    Z = (D ** 3 - d ** 3) / 6
    return SectionProps(name or "PIPE %gx%g" % (D, t), "round_hss",
                        A, I, I, S, S, Z, Z, 0.5 * A, D, D, True)


def solid_round(D: float, name: str = "") -> SectionProps:
    A = math.pi / 4 * D ** 2
    I = math.pi / 64 * D ** 4
    S = I / (D / 2)
    Z = D ** 3 / 6
    return SectionProps(name or "ROUND D%g" % D, "solid_round",
                        A, I, I, S, S, Z, Z, 0.9 * A, D, D, True)


def rect_hss(H: float, B: float, t: float, name: str = "") -> SectionProps:
    """Hop vuong / chu nhat (SHS / RHS). H theo phuong truc khoe."""
    if t <= 0 or H <= 2 * t or B <= 2 * t:
        raise ValueError("Hop: can H > 2t, B > 2t, t > 0.")
    hi, bi = H - 2 * t, B - 2 * t
    A = H * B - hi * bi
    Ix = (B * H ** 3 - bi * hi ** 3) / 12
    Iy = (H * B ** 3 - hi * bi ** 3) / 12
    Sx, Sy = 2 * Ix / H, 2 * Iy / B
    Zx = B * H ** 2 / 4 - bi * hi ** 2 / 4
    Zy = H * B ** 2 / 4 - hi * bi ** 2 / 4
    return SectionProps(name or "SHS %gx%gx%g" % (H, B, t), "rect_hss",
                        A, Ix, Iy, Sx, Sy, Zx, Zy, 2 * H * t, H, B, True)


def flat_bar(H: float, B: float, name: str = "") -> SectionProps:
    """Thep ban / thanh dac chu nhat. H = chieu cao (phuong uon khoe)."""
    A = B * H
    Ix, Iy = B * H ** 3 / 12, H * B ** 3 / 12
    return SectionProps(name or "FLAT %gx%g" % (H, B), "flat_bar",
                        A, Ix, Iy, B * H ** 2 / 6, H * B ** 2 / 6,
                        B * H ** 2 / 4, H * B ** 2 / 4,
                        2.0 / 3.0 * A, H, B)


def i_beam(H: float, B: float, tw: float, tf: float, name: str = "") -> SectionProps:
    """Tiet dien chu I / H doi xung hai truc. H = tong chieu cao."""
    if tf <= 0 or tw <= 0 or H <= 2 * tf:
        raise ValueError("Chu I: can H > 2tf, tw > 0, tf > 0.")
    hw = H - 2 * tf
    A = 2 * B * tf + hw * tw
    Ix = (B * H ** 3 - (B - tw) * hw ** 3) / 12
    Iy = (2 * tf * B ** 3 + hw * tw ** 3) / 12
    Sx, Sy = 2 * Ix / H, 2 * Iy / B
    Zx = B * tf * (H - tf) + tw * hw ** 2 / 4
    Zy = tf * B ** 2 / 2 + hw * tw ** 2 / 4
    return SectionProps(name or "I %gx%gx%gx%g" % (H, B, tw, tf), "i_beam",
                        A, Ix, Iy, Sx, Sy, Zx, Zy, H * tw, H, B)


def channel(H: float, B: float, tw: float, tf: float, name: str = "") -> SectionProps:
    """Thep U / C. Bung dat doc, hai canh huong cung mot phia.

    Doi xung qua truc x, KHONG doi xung qua truc y -> Sy lay theo thot bien xa
    nhat, va Zy lay bang Sy (thien ve an toan).
    """
    if tf <= 0 or tw <= 0 or H <= 2 * tf or B <= tw:
        raise ValueError("Thep U: can H > 2tf, B > tw, tw > 0, tf > 0.")
    hi = H - 2 * tf
    A = B * H - (B - tw) * hi
    Ix = (B * H ** 3 - (B - tw) * hi ** 3) / 12
    Sx = 2 * Ix / H
    Zx = B * H ** 2 / 4 - (B - tw) * hi ** 2 / 4

    # truc y: phai tim trong tam
    a_web, x_web = tw * H, tw / 2.0
    a_fl, x_fl = 2 * tf * (B - tw), tw + (B - tw) / 2.0
    xb = (a_web * x_web + a_fl * x_fl) / A
    Iy = (H * tw ** 3 / 12 + a_web * (x_web - xb) ** 2
          + 2 * (tf * (B - tw) ** 3 / 12) + a_fl * (x_fl - xb) ** 2)
    Sy = Iy / max(xb, B - xb)

    return SectionProps(name or "C %gx%gx%gx%g" % (H, B, tw, tf), "channel",
                        A, Ix, Iy, Sx, Sy, Zx, Sy, H * tw, H, B,
                        note="Zy lay = Sy (an toan). Tam cat lech khoi trong tam "
                             "-> tranh dat tai gay xoan.")


def angle(H: float, B: float, t: float, name: str = "") -> SectionProps:
    """Thep goc L (deu hoac khong deu), hai canh vuong goc.

    Ix, Iy tinh quanh truc song song canh (KHONG phai truc chinh u-v).
    Voi thep goc, truc yeu that su la truc v; r_min thuc te NHO HON ry o day.
    Ham nay uoc luong r_min theo truc chinh de khong danh gia thieu do manh.
    """
    if t <= 0 or H <= t or B <= t:
        raise ValueError("Thep goc: can H > t, B > t, t > 0.")
    a1, a2 = H * t, (B - t) * t          # canh dung, canh nam
    A = a1 + a2
    xb = (a1 * t / 2 + a2 * (t + (B - t) / 2)) / A
    yb = (a1 * H / 2 + a2 * t / 2) / A

    Ix = (t * H ** 3 / 12 + a1 * (H / 2 - yb) ** 2
          + (B - t) * t ** 3 / 12 + a2 * (t / 2 - yb) ** 2)
    Iy = (H * t ** 3 / 12 + a1 * (t / 2 - xb) ** 2
          + t * (B - t) ** 3 / 12 + a2 * (t + (B - t) / 2 - xb) ** 2)
    Ixy = (a1 * (t / 2 - xb) * (H / 2 - yb)
           + a2 * (t + (B - t) / 2 - xb) * (t / 2 - yb))

    # truc chinh
    avg, dif = (Ix + Iy) / 2.0, (Ix - Iy) / 2.0
    R = math.hypot(dif, Ixy)
    Imin_principal = avg - R

    Sx = Ix / max(yb, H - yb)
    Sy = Iy / max(xb, B - xb)

    sp = SectionProps(name or "L %gx%gx%g" % (H, B, t), "angle",
                      A, Ix, Iy, Sx, Sy, Sx, Sy, H * t, H, B,
                      note="Z lay = S (an toan). r_min theo truc chinh v.")
    sp._Imin_principal = Imin_principal        # type: ignore[attr-defined]
    return sp


def tee(H: float, B: float, tw: float, tf: float, name: str = "") -> SectionProps:
    """Tiet dien chu T: canh tren rong B day tf, bung cao (H - tf) day tw."""
    if tf <= 0 or tw <= 0 or H <= tf:
        raise ValueError("Chu T: can H > tf, tw > 0, tf > 0.")
    hw = H - tf
    a_f, y_f = B * tf, H - tf / 2.0
    a_w, y_w = hw * tw, hw / 2.0
    A = a_f + a_w
    yb = (a_f * y_f + a_w * y_w) / A
    Ix = (B * tf ** 3 / 12 + a_f * (y_f - yb) ** 2
          + tw * hw ** 3 / 12 + a_w * (y_w - yb) ** 2)
    Iy = (tf * B ** 3 + hw * tw ** 3) / 12
    Sx = Ix / max(yb, H - yb)
    Sy = 2 * Iy / B
    return SectionProps(name or "T %gx%gx%gx%g" % (H, B, tw, tf), "tee",
                        A, Ix, Iy, Sx, Sy, Sx, Sy, hw * tw, H, B,
                        note="Z lay = S (an toan).")


# --------------------------------------------------------------------------
# dieu phoi
# --------------------------------------------------------------------------
SHAPES = {
    "Ong tron (Pipe / CHS)":      ("round_hss", ["D ngoai", "t"]),
    "Hop vuong-CN (SHS / RHS)":   ("rect_hss",  ["H", "B", "t"]),
    "Chu I / H":                  ("i_beam",    ["H", "B", "tw", "tf"]),
    "Thep U / C":                 ("channel",   ["H", "B", "tw", "tf"]),
    "Thep goc L":                 ("angle",     ["H", "B", "t"]),
    "Chu T":                      ("tee",       ["H", "B", "tw", "tf"]),
    "Thep ban / thanh dac":       ("flat_bar",  ["H", "B"]),
    "Tron dac":                   ("solid_round", ["D"]),
}

_BUILDERS = {
    "round_hss": round_hss,
    "rect_hss": rect_hss,
    "i_beam": i_beam,
    "channel": channel,
    "angle": angle,
    "tee": tee,
    "flat_bar": flat_bar,
    "solid_round": solid_round,
}


def build(shape: str, dims: list[float], name: str = "") -> SectionProps:
    fn = _BUILDERS.get(shape)
    if fn is None:
        raise ValueError("Khong biet dang tiet dien: %r" % shape)
    return fn(*dims, name=name)


def r_min_effective(sp: SectionProps) -> float:
    """Ban kinh quan tinh nho nhat, co xet truc chinh cua thep goc."""
    Ip = getattr(sp, "_Imin_principal", None)
    if Ip is not None and sp.A > 0:
        return math.sqrt(max(Ip, 1e-12) / sp.A)
    return sp.rmin


# --------------------------------------------------------------------------
# kich thuoc danh nghia thuong gap -- CHI DE DIEN NHANH, PHAI DOI CHIEU CATALOGUE
# --------------------------------------------------------------------------
PRESETS: dict[str, list[tuple[str, str, list[float]]]] = {
    "Thep goc L (deu canh)": [
        ("L40x40x4",   "angle", [40, 40, 4]),
        ("L50x50x5",   "angle", [50, 50, 5]),
        ("L63x63x6",   "angle", [63, 63, 6]),
        ("L70x70x7",   "angle", [70, 70, 7]),
        ("L75x75x6",   "angle", [75, 75, 6]),
        ("L80x80x8",   "angle", [80, 80, 8]),
        ("L100x100x10", "angle", [100, 100, 10]),
        ("L120x120x12", "angle", [120, 120, 12]),
    ],
    "Hop vuong SHS": [
        ("SHS 40x40x3",   "rect_hss", [40, 40, 3]),
        ("SHS 50x50x4",   "rect_hss", [50, 50, 4]),
        ("SHS 60x60x4",   "rect_hss", [60, 60, 4]),
        ("SHS 75x75x5",   "rect_hss", [75, 75, 5]),
        ("SHS 100x100x5", "rect_hss", [100, 100, 5]),
        ("SHS 100x100x6", "rect_hss", [100, 100, 6]),
        ("SHS 125x125x6", "rect_hss", [125, 125, 6]),
        ("SHS 150x150x8", "rect_hss", [150, 150, 8]),
    ],
    "Hop chu nhat RHS": [
        ("RHS 80x40x3",    "rect_hss", [80, 40, 3]),
        ("RHS 100x50x4",   "rect_hss", [100, 50, 4]),
        ("RHS 120x60x4",   "rect_hss", [120, 60, 4]),
        ("RHS 150x100x5",  "rect_hss", [150, 100, 5]),
        ("RHS 200x100x6",  "rect_hss", [200, 100, 6]),
    ],
    "Thep U / C": [
        ("C80x40x4x6",    "channel", [80, 40, 4, 6]),
        ("C100x50x5x6",   "channel", [100, 50, 5, 6]),
        ("C120x55x6x7",   "channel", [120, 55, 6, 7]),
        ("C150x75x6x9",   "channel", [150, 75, 6, 9]),
        ("C200x80x7x11",  "channel", [200, 80, 7, 11]),
    ],
    "Chu I / H": [
        ("I100x55x4.5x7",   "i_beam", [100, 55, 4.5, 7]),
        ("I150x75x5x9",     "i_beam", [150, 75, 5, 9]),
        ("I200x100x5.5x8",  "i_beam", [200, 100, 5.5, 8]),
        ("H100x100x6x8",    "i_beam", [100, 100, 6, 8]),
        ("H150x150x7x10",   "i_beam", [150, 150, 7, 10]),
        ("H200x200x8x12",   "i_beam", [200, 200, 8, 12]),
    ],
    "Ong tron": [
        ("PIPE 48.3x3.7",  "round_hss", [48.3, 3.7]),
        ("PIPE 60.3x3.9",  "round_hss", [60.3, 3.9]),
        ("PIPE 88.9x5.5",  "round_hss", [88.9, 5.5]),
        ("PIPE 114.3x6.0", "round_hss", [114.3, 6.0]),
        ("PIPE 168.3x7.1", "round_hss", [168.3, 7.1]),
    ],
    "Thep ban": [
        ("FB 100x10", "flat_bar", [100, 10]),
        ("FB 150x12", "flat_bar", [150, 12]),
        ("FB 200x16", "flat_bar", [200, 16]),
    ],
}

PRESET_WARNING = (
    "Kich thuoc preset la kich thuoc DANH NGHIA thuong gap, dung de dien nhanh. "
    "Truoc khi phat hanh thiet ke phai doi chieu catalogue nha san xuat / "
    "tieu chuan ap dung (JIS G3192, EN 10056, EN 10219, ASTM A500, TCVN 1656...)."
)
