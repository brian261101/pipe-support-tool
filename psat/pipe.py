"""Tai trong duong ong va khoang cach gia do.

Tinh khoi luong ong + moi chat + bao on, tu do suy ra:
    * tai phan bo deu w  [N/mm]
    * khoang cach gia do lon nhat theo dieu kien ung suat va dieu kien do vong
    * phan luc goi do  N = w * L_nhip

Don vi noi bo: mm, N, MPa.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .data import GRAVITY


@dataclass
class PipeLoad:
    """Ket qua tinh tai trong duong ong. Tat ca theo N/mm va kg/m."""
    w_pipe: float
    w_fluid: float
    w_insul: float
    w_extra: float

    OD: float
    ID: float
    t_corroded: float
    A_metal: float
    I: float
    Z: float

    @property
    def w_total(self) -> float:
        return self.w_pipe + self.w_fluid + self.w_insul + self.w_extra

    def kg_per_m(self, w: float) -> float:
        return w * 1000.0 / GRAVITY

    def breakdown(self) -> list[tuple[str, float, float]]:
        """[(ten, N/mm, kg/m)]"""
        rows = [
            ("Ong (thep)", self.w_pipe, self.kg_per_m(self.w_pipe)),
            ("Moi chat trong ong", self.w_fluid, self.kg_per_m(self.w_fluid)),
            ("Bao on", self.w_insul, self.kg_per_m(self.w_insul)),
        ]
        if self.w_extra:
            rows.append(("Tai phu them", self.w_extra, self.kg_per_m(self.w_extra)))
        rows.append(("TONG", self.w_total, self.kg_per_m(self.w_total)))
        return rows


def pipe_load(OD: float, t: float, rho_pipe: float, rho_fluid: float,
              t_insul: float = 0.0, rho_insul: float = 0.0,
              corrosion: float = 0.0, extra_kg_per_m: float = 0.0) -> PipeLoad:
    """Tinh tai phan bo cua duong ong.

    OD, t, t_insul, corrosion [mm]; rho [kg/m3]; extra [kg/m].

    Chieu day an mon duoc TRU khoi thanh ong khi tinh do ben (A, I, Z) nhung
    khoi luong thep van tinh theo chieu day danh nghia - day la cach lam
    thien ve an toan o ca hai phia.
    """
    if OD <= 0 or t <= 0 or OD <= 2 * t:
        raise ValueError("Kich thuoc ong khong hop le: can OD > 2t > 0.")

    ID = OD - 2 * t
    tc = max(t - corrosion, 1e-6)
    if OD <= 2 * tc:
        raise ValueError("Chieu day sau an mon khong hop le.")
    ODc_id = OD - 2 * tc

    # khoi luong theo chieu day danh nghia -> N/mm
    A_nom = math.pi / 4 * (OD ** 2 - ID ** 2)             # mm2
    w_pipe = A_nom * 1e-6 * rho_pipe * GRAVITY / 1000.0   # N/mm

    A_fluid = math.pi / 4 * ID ** 2
    w_fluid = A_fluid * 1e-6 * rho_fluid * GRAVITY / 1000.0

    if t_insul > 0 and rho_insul > 0:
        OD_i = OD + 2 * t_insul
        A_i = math.pi / 4 * (OD_i ** 2 - OD ** 2)
        w_insul = A_i * 1e-6 * rho_insul * GRAVITY / 1000.0
    else:
        w_insul = 0.0

    w_extra = extra_kg_per_m * GRAVITY / 1000.0

    # dac trung chiu luc tinh theo chieu day DA TRU an mon
    A_metal = math.pi / 4 * (OD ** 2 - ODc_id ** 2)
    I = math.pi / 64 * (OD ** 4 - ODc_id ** 4)
    Z = I / (OD / 2)

    return PipeLoad(w_pipe, w_fluid, w_insul, w_extra,
                    OD, ID, tc, A_metal, I, Z)


# --------------------------------------------------------------------------
# khoang cach gia do
# --------------------------------------------------------------------------
# He so so do dam:  (he so moment, he so do vong)
#   M = w L^2 / cm        delta = w L^4 / (cd * E * I)
SPAN_SCHEMES = {
    "Nhieu nhip lien tuc (thuong dung)": (10.0, 185.0),
    "Dam don gian (2 goi, an toan hon)": (8.0, 76.8),   # 384/5 = 76.8
}
DEFAULT_SPAN_SCHEME = "Nhieu nhip lien tuc (thuong dung)"

# Co so cua ASME B31.1 Table 121.5
B31_1_SIGMA = 15.9      # MPa  (2300 psi)
B31_1_SAG = 2.5         # mm   (0.1 in)


@dataclass
class SpanResult:
    L_stress: float
    L_defl: float
    scheme: str
    sigma_allow: float
    sag_allow: float

    @property
    def L_max(self) -> float:
        return min(self.L_stress, self.L_defl)

    @property
    def governed_by(self) -> str:
        return "ung suat" if self.L_stress <= self.L_defl else "do vong"


def max_span(w: float, Z: float, I: float, E: float,
             sigma_allow: float = B31_1_SIGMA,
             sag_allow: float = B31_1_SAG,
             scheme: str = DEFAULT_SPAN_SCHEME) -> SpanResult:
    """Khoang cach gia do lon nhat [mm].

    w  [N/mm]  tai phan bo deu
    Z  [mm3]   moment khang uon cua ong
    I  [mm4]   moment quan tinh cua ong
    E  [MPa]

    Dieu kien ung suat:  w L^2 / cm / Z <= sigma_allow
    Dieu kien do vong :  w L^4 / (cd E I) <= sag_allow
    """
    cm, cd = SPAN_SCHEMES[scheme]
    if w <= 0:
        raise ValueError("Tai phan bo phai lon hon 0.")
    L_sigma = math.sqrt(cm * sigma_allow * Z / w)
    L_delta = (cd * E * I * sag_allow / w) ** 0.25
    return SpanResult(L_sigma, L_delta, scheme, sigma_allow, sag_allow)


def support_reaction(w: float, span: float, concentrated: float = 0.0) -> float:
    """Phan luc thang dung tren mot gia do [N].

    Mot gia do o giua tuyen gánh nua nhip moi ben = w * span.
    `concentrated` [N] cong them cho van, phu kien, nguoi di lai...
    """
    return w * span + concentrated


# --------------------------------------------------------------------------
# co giãn nhiet - rat quan trong voi LNG
# --------------------------------------------------------------------------
# he so gian no nhiet trung binh [1/C] tu nhiet do thuong den nhiet do van hanh
THERMAL_ALPHA = {
    "Thep carbon":      1.17e-5,
    "Thep 9% Ni":       1.0e-5,
    "Inox austenit":    1.6e-5,
    "Nhom":             2.3e-5,
}


def thermal_movement(length_mm: float, dT: float, alpha: float) -> float:
    """Do co/gian cua mot doan ong [mm]. dT am = lanh di = co lai."""
    return alpha * dT * length_mm
