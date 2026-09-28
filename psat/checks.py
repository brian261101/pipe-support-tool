# -*- coding: utf-8 -*-
"""Kiểm tra khả năng chịu lực của thanh thép, từ kết quả PTHH.

Phuong phap: ung suat cho phep (ASD) theo tinh than AISC 360.
    keo     Ft = 0.6 Fy                      (tuong duong Fy / 1.67)
    uon     Fb = 0.6 Fy                      (an toan - khong tinh du tru deo,
                                              khong cong diem cho on dinh ngang)
    cat     Fv = 0.4 Fy
    nen     Fa = Fcr / 1.67  voi Fcr theo AISC 360 chuong E:
                Fe = pi^2 E / (KL/r)^2
                KL/r <= 4.71 sqrt(E/Fy):  Fcr = 0.658^(Fy/Fe) * Fy
                nguoc lai             :  Fcr = 0.877 Fe
    to hop  AISC H1-1:
                fa/Fa >= 0.2 :  fa/Fa + (8/9)(fb/Fb) <= 1
                fa/Fa <  0.2 :  fa/(2Fa) + fb/Fb     <= 1

Cach lam nay THIEN VE AN TOAN so voi AISC day du (khong xet tiet dien dac chac,
khong xet he so Cb cho on dinh ngang). Voi gia do duong ong - noi tiet dien
thuong nho va ngan - do la lua chon hop ly.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .sections import SectionProps, r_min_effective

SF = 1.67
SLENDER_LIMIT_C = 200.0     # AISC khuyen nghi cho thanh nen
SLENDER_LIMIT_T = 300.0     # cho thanh keo


@dataclass
class MemberCheck:
    member: int
    name: str
    L: float                    # chieu dai thanh vat ly [mm]

    N: float                    # luc doc truc quyet dinh [N], keo duong
    M: float                    # moment lon nhat [N.mm]
    V: float                    # luc cat lon nhat [N]
    x_crit: float               # vi tri mat cat nguy hiem doc thanh [mm]
    xy_crit: tuple[float, float]  # toa do toan cuc cua mat cat do

    fa: float
    fb: float
    fv: float
    Fa: float
    Fb: float
    Fv: float

    slenderness: float
    Fe: float
    Fcr: float

    u_axial: float
    u_bend: float
    u_shear: float
    u_combined: float

    warnings: list[str] = field(default_factory=list)

    @property
    def utilization(self) -> float:
        return max(self.u_axial, self.u_bend, self.u_shear, self.u_combined)

    @property
    def action(self) -> str:
        if self.N > 1e-6:
            return "KÉO"
        if self.N < -1e-6:
            return "NÉN"
        return "-"

    @property
    def ok(self) -> bool:
        return self.utilization <= 1.0

    @property
    def dominant(self) -> str:
        """Yếu tố chi phối: uốn hay dọc trục."""
        a = self.fa / self.Fa if self.Fa > 0 else 0.0
        b = self.fb / self.Fb if self.Fb > 0 else 0.0
        if b > 2.0 * a:
            return "uốn"
        if a > 2.0 * b:
            return "dọc trục"
        return "uốn + dọc trục"


def compressive_stress(Fy: float, E: float, KLr: float) -> tuple[float, float, float]:
    """Tra ve (Fe, Fcr, Fa) theo AISC 360 chuong E."""
    if KLr <= 1e-9:
        return float('inf'), Fy, Fy / SF
    Fe = math.pi ** 2 * E / (KLr ** 2)
    if KLr <= 4.71 * math.sqrt(E / Fy):
        Fcr = (0.658 ** (Fy / Fe)) * Fy
    else:
        Fcr = 0.877 * Fe
    return Fe, Fcr, Fcr / SF


def check_member(member: int, name: str, sp: SectionProps,
                 Fy: float, E: float,
                 N: float, M: float, V: float,
                 L: float, K: float,
                 x_crit: float, xy_crit: tuple[float, float],
                 expected: str = "Tu dong") -> MemberCheck:
    """Kiem tra mot thanh voi noi luc quyet dinh lay tu PTHH."""
    warn: list[str] = []

    r = r_min_effective(sp)
    KLr = K * L / r if r > 0 else 0.0

    fa = abs(N) / sp.A
    fb = abs(M) / sp.Sx if sp.Sx > 0 else 0.0
    fv = abs(V) / sp.Av if sp.Av > 0 else 0.0

    Fb = 0.6 * Fy
    Fv = 0.4 * Fy

    if N >= 0:                                   # keo
        Fa = 0.6 * Fy
        Fe = Fcr = float('nan')
        if KLr > SLENDER_LIMIT_T:
            warn.append("Độ mảnh KL/r = %.0f vượt khuyến nghị %.0f cho thanh kéo."
                        % (KLr, SLENDER_LIMIT_T))
    else:                                        # nen
        Fe, Fcr, Fa = compressive_stress(Fy, E, KLr)
        if KLr > SLENDER_LIMIT_C:
            warn.append("Độ mảnh KL/r = %.0f VƯỢT giới hạn %.0f cho thanh nén — "
                        "phải giằng bớt hoặc tăng tiết diện."
                        % (KLr, SLENDER_LIMIT_C))
        elif KLr > 120:
            warn.append("Thanh mảnh (KL/r = %.0f) — khả năng chịu nén giảm nhiều."
                        % KLr)

    u_axial = fa / Fa if Fa > 0 else float('inf')
    u_bend = fb / Fb if Fb > 0 else 0.0
    u_shear = fv / Fv if Fv > 0 else 0.0

    if u_axial >= 0.2:
        u_comb = u_axial + (8.0 / 9.0) * u_bend
    else:
        u_comb = u_axial / 2.0 + u_bend

    if expected == "Keo" and N < -1e-6:
        warn.append("Bạn khai báo thanh này CHỊU KÉO nhưng PTHH cho ra CHỊU NÉN "
                    "(%.0f N). Nếu thanh chỉ là thanh giằng hoặc cáp thì phải "
                    "bố trí lại." % N)
    if expected == "Nen" and N > 1e-6:
        warn.append("Bạn khai báo thanh này CHỊU NÉN nhưng PTHH cho ra CHỊU KÉO "
                    "(%.0f N)." % N)

    if sp.shape == "angle" and abs(N) > 1e-6:
        warn.append("Thép góc chịu lực dọc trục thường lệch tâm — khả năng thực "
                    "tế thấp hơn kết quả ở đây. Xem AISC 360 mục E5.")
    if sp.shape == "channel" and abs(M) > 1e-6:
        warn.append("Thép U có tâm cắt lệch khỏi trọng tâm — nếu tải không đi qua "
                    "tâm cắt sẽ sinh xoắn, chưa tính ở đây.")

    return MemberCheck(member, name, L, N, M, V, x_crit, xy_crit,
                       fa, fb, fv, Fa, Fb, Fv,
                       KLr, Fe, Fcr,
                       u_axial, u_bend, u_shear, u_comb, warn)


# --------------------------------------------------------------------------
# tong hop
# --------------------------------------------------------------------------
@dataclass
class Assessment:
    members: list[MemberCheck]
    lambda_strength: float          # he so tai dat gioi han ben
    lambda_buckling: float          # he so tai toi han theo on dinh (0 = khong xet)
    buckling_note: str
    max_disp: float
    max_disp_node: int
    disp_limit: float
    governing: MemberCheck | None

    @property
    def lambda_allow(self) -> float:
        """He so tai cho phep = min(ben, on dinh / he so an toan on dinh)."""
        vals = [self.lambda_strength]
        if self.lambda_buckling > 0:
            vals.append(self.lambda_buckling / SF)
        return min(vals)

    @property
    def governed_by(self) -> str:
        if self.lambda_buckling > 0 and self.lambda_buckling / SF < self.lambda_strength:
            return "ổn định tổng thể (mất ổn định)"
        if self.governing is None:
            return "-"
        return "bền — %s (%s)" % (self.governing.name,
                                  self.governing.dominant)

    @property
    def disp_ok(self) -> bool:
        return self.disp_limit <= 0 or self.max_disp <= self.disp_limit


def assess(checks: list[MemberCheck], lambda_buckling: float, buckling_note: str,
           max_disp: float, max_disp_node: int, disp_limit: float) -> Assessment:
    gov = max(checks, key=lambda c: c.utilization) if checks else None
    umax = gov.utilization if gov else 0.0
    lam_s = (1.0 / umax) if umax > 1e-12 else float('inf')
    return Assessment(checks, lam_s, lambda_buckling, buckling_note,
                      max_disp, max_disp_node, disp_limit, gov)
