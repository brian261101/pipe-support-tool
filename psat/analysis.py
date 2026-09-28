"""Dieu phoi: du lieu nhap -> mo hinh PTHH -> noi luc -> kiem tra -> ket luan."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import checks as chk
from . import fem
from .sections import SectionProps

SNAP_TOL = 1.0          # mm - diem dat luc cach thanh duoi muc nay coi nhu nam tren thanh


@dataclass
class MemberIn:
    x1: float
    y1: float
    x2: float
    y2: float
    section: SectionProps
    expected: str = "Tu dong"      # "Tu dong" | "Keo" | "Nen"
    label: str = ""

    @property
    def length(self) -> float:
        return math.hypot(self.x2 - self.x1, self.y2 - self.y1)

    @property
    def p1(self):
        return (self.x1, self.y1)

    @property
    def p2(self):
        return (self.x2, self.y2)


@dataclass
class LoadIn:
    x: float
    y: float
    magnitude: float               # N, luon duong
    angle: float = -90.0           # do, do tu truc +X nguoc chieu kim dong ho
    label: str = ""

    @property
    def fx(self) -> float:
        return self.magnitude * math.cos(math.radians(self.angle))

    @property
    def fy(self) -> float:
        return self.magnitude * math.sin(math.radians(self.angle))


@dataclass
class SupportIn:
    x: float
    y: float
    kind: str = "Ngam"             # "Ngam" | "Khop" | "Con lan dung" | "Con lan ngang"

    def flags(self):
        if self.kind == "Ngam":
            return True, True, True
        if self.kind == "Khop":
            return True, True, False
        if self.kind == "Con lan dung":        # chi chan theo phuong Y
            return False, True, False
        if self.kind == "Con lan ngang":       # chi chan theo phuong X
            return True, False, False
        raise ValueError("Loai goi tua khong hop le: %r" % self.kind)


@dataclass
class Project:
    members: list[MemberIn] = field(default_factory=list)
    loads: list[LoadIn] = field(default_factory=list)
    supports: list[SupportIn] = field(default_factory=list)

    Fy: float = 235.0
    E: float = 210000.0
    rho_steel: float = 7850.0

    nseg: int = 4
    K_factor: float = 1.0
    disp_limit: float = 0.0        # mm, 0 = khong kiem tra
    self_weight: bool = True
    do_buckling: bool = True


@dataclass
class Result:
    model: fem.Model
    solution: fem.Solution
    assessment: chk.Assessment
    buckling_modes: list[list[float]]
    lambdas: list[float]
    notes: list[str]
    node_of_load: list[int]


class InputError(Exception):
    pass


# --------------------------------------------------------------------------
def _validate(p: Project) -> list[str]:
    notes: list[str] = []
    if not p.members:
        raise InputError("Chua khai bao thanh support nao.")
    if not p.supports:
        raise InputError("Chua khai bao goi tua (diem lien ket voi ket cau do).")
    if not p.loads:
        raise InputError("Chua khai bao luc tac dung.")

    for i, m in enumerate(p.members):
        if m.length < 1.0:
            raise InputError("Thanh %d co chieu dai %.3f mm - kiem tra lai toa do."
                             % (i + 1, m.length))

    # diem dat luc phai nam tren mot thanh nao do
    for j, ld in enumerate(p.loads):
        best_d, best_i = float('inf'), -1
        for i, m in enumerate(p.members):
            d, _ = fem.point_on_segment(ld.x, ld.y, m.x1, m.y1, m.x2, m.y2)
            if d < best_d:
                best_d, best_i = d, i
        if best_d > SNAP_TOL:
            raise InputError(
                "Diem dat luc %d tai (%.1f, %.1f) KHONG nam tren thanh nao.\n\n"
                "Thanh gan nhat la thanh %d, cach %.1f mm.\n\n"
                "Luc chi co the truyen vao ket cau qua mot thanh. Hay:\n"
                "  - doi toa do diem dat luc ve nam tren mot thanh, hoac\n"
                "  - them mot thanh chay den diem do (vi du thanh doi tu khung "
                "ra vi tri ong)."
                % (j + 1, ld.x, ld.y, best_i + 1, best_d))

    # goi tua nen trung voi dau thanh
    for k, s in enumerate(p.supports):
        best = float('inf')
        for m in p.members:
            best = min(best,
                       math.hypot(s.x - m.x1, s.y - m.y1),
                       math.hypot(s.x - m.x2, s.y - m.y2))
        if best > SNAP_TOL:
            notes.append("Goi tua %d tai (%.0f, %.0f) khong trung dau thanh nao "
                         "(cach %.1f mm) - se duoc gan vao nut gan nhat tren luoi."
                         % (k + 1, s.x, s.y, best))
    return notes


def build_model(p: Project) -> tuple[fem.Model, list[list[int]], list[int]]:
    """Dung mo hinh PTHH. Tra ve (model, phan tu cua tung thanh, nut cua tung luc)."""
    m = fem.Model()
    forced = [(ld.x, ld.y) for ld in p.loads]
    for s in p.supports:
        forced.append((s.x, s.y))

    per_member: list[list[int]] = []
    for i, mi in enumerate(p.members):
        wy = 0.0
        if p.self_weight:
            # N/mm, huong xuong
            wy = -mi.section.A * 1e-6 * p.rho_steel * 9.80665 / 1000.0
        ids = fem.mesh_member(m, mi.p1, mi.p2, p.E, mi.section.A, mi.section.Ix,
                              p.nseg, i, wy=wy, forced=forced)
        per_member.append(ids)

    node_of_load = []
    for ld in p.loads:
        n = m.add_node(ld.x, ld.y)
        node_of_load.append(n)
        m.loads.append(fem.PointLoad(n, fx=ld.fx, fy=ld.fy))

    for s in p.supports:
        # gan vao nut gan nhat
        best_i, best_d = 0, float('inf')
        for nd in m.nodes:
            d = math.hypot(nd.x - s.x, nd.y - s.y)
            if d < best_d:
                best_i, best_d = nd.idx, d
        ux, uy, rz = s.flags()
        m.supports.append(fem.Support(best_i, ux, uy, rz))

    return m, per_member, node_of_load


def run(p: Project) -> Result:
    notes = _validate(p)
    model, per_member, node_of_load = build_model(p)

    if len(model.elements) > 400:
        raise InputError("Mo hinh co %d phan tu - qua lon. Giam so doan chia "
                         "moi thanh." % len(model.elements))

    sol = fem.solve(model)

    # --- gom noi luc ve tung thanh vat ly ---
    member_checks = []
    for i, mi in enumerate(p.members):
        ids = per_member[i]
        if not ids:
            continue
        N_c = 0.0       # nen lon nhat (am)
        N_t = 0.0       # keo lon nhat (duong)
        M_max = 0.0
        V_max = 0.0
        x_crit = 0.0
        xy_crit = mi.p1
        offset = 0.0

        for eid in ids:
            r = sol.elements[eid]
            N_c = min(N_c, r.N, r.N1)
            N_t = max(N_t, r.N, r.N1)
            V_max = max(V_max, r.V_max_abs)
            for xs, mv in zip(r.x, r.M):
                if abs(mv) > M_max:
                    M_max = abs(mv)
                    x_crit = offset + xs
                    t = x_crit / mi.length if mi.length else 0.0
                    xy_crit = (mi.x1 + t * (mi.x2 - mi.x1),
                               mi.y1 + t * (mi.y2 - mi.y1))
            offset += r.L

        # luc doc truc quyet dinh: nen bat loi hon keo
        N = N_c if abs(N_c) >= abs(N_t) else N_t

        member_checks.append(chk.check_member(
            i, mi.label or ("Thanh %d" % (i + 1)), mi.section,
            p.Fy, p.E, N, M_max, V_max, mi.length, p.K_factor,
            x_crit, xy_crit, mi.expected))

    # --- on dinh tong the ---
    lambdas: list[float] = []
    modes: list[list[float]] = []
    bnote = ""
    if p.do_buckling:
        lambdas, modes, bnote = fem.buckling(model, sol, nmodes=2)
        if bnote:
            notes.append(bnote)
    lam_b = lambdas[0] if lambdas else 0.0

    dmax, dnode = sol.max_translation
    a = chk.assess(member_checks, lam_b, bnote, dmax, dnode, p.disp_limit)

    return Result(model, sol, a, modes, lambdas, notes, node_of_load)


# --------------------------------------------------------------------------
# tu dong chon tiet dien
# --------------------------------------------------------------------------
def auto_size(p: Project, candidates: list[SectionProps],
              target: float = 1.0, apply_to: int | None = None):
    """Thu lan luot cac tiet dien, tra ve phuong an nhe nhat con DAT.

    Vi do cung thay doi se phan bo lai noi luc, moi phuong an deu duoc
    chay lai TOAN BO bai toan PTHH chu khong suy dien tu mot lan giai.

    Tra ve danh sach (tiet dien, ket qua, dat/khong) theo thu tu khoi luong tang.
    """
    ordered = sorted(candidates, key=lambda s: s.A)
    out = []
    for sp in ordered:
        trial = Project(
            members=[MemberIn(m.x1, m.y1, m.x2, m.y2,
                              sp if (apply_to is None or apply_to == i) else m.section,
                              m.expected, m.label)
                     for i, m in enumerate(p.members)],
            loads=list(p.loads), supports=list(p.supports),
            Fy=p.Fy, E=p.E, rho_steel=p.rho_steel, nseg=p.nseg,
            K_factor=p.K_factor, disp_limit=p.disp_limit,
            self_weight=p.self_weight, do_buckling=p.do_buckling)
        try:
            r = run(trial)
        except Exception as exc:                    # tiet dien qua yeu -> bo qua
            out.append((sp, None, False, str(exc)))
            continue
        ok = (r.assessment.lambda_allow >= target) and r.assessment.disp_ok
        out.append((sp, r, ok, ""))
    return out
