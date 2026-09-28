"""Phan tu huu han - khung phang (2D frame). Thuan thu vien chuan Python.

Phan tu dam-cot Euler-Bernoulli, 6 bac tu do (u, v, theta o moi nut).
Phan tich:
    * tinh hoc tuyen tinh          K u = F
    * on dinh dan hoi (tri rieng)  (K + lambda*Kg) phi = 0  -> he so tai toi han

He don vi noi bo:  mm, N, MPa (= N/mm^2).
Truc: x sang phai, y len tren, moment nguoc chieu kim dong ho la duong.

Quy uoc noi luc moi phan tu (he toa do dia phuong):
    f = [N1, V1, M1, N2, V2, M2]  -- luc tac dung LEN phan tu tai hai dau.
    Luc doc truc quy uoc KEO duong:  N = f[3].
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import linalg as la

TOL = 1e-6          # mm - sai so gop nut


# --------------------------------------------------------------------------
# mo hinh
# --------------------------------------------------------------------------
@dataclass
class Node:
    x: float
    y: float
    idx: int = -1


@dataclass
class Element:
    n1: int
    n2: int
    E: float            # MPa
    A: float            # mm^2
    I: float            # mm^4
    wx: float = 0.0     # N/mm theo phuong X toan cuc
    wy: float = 0.0     # N/mm theo phuong Y toan cuc
    member: int = -1    # thanh vat ly chua phan tu nay

    L: float = 0.0
    c: float = 1.0
    s: float = 0.0


@dataclass
class Support:
    node: int
    ux: bool = True
    uy: bool = True
    rz: bool = True


@dataclass
class PointLoad:
    node: int
    fx: float = 0.0
    fy: float = 0.0
    mz: float = 0.0


@dataclass
class Model:
    nodes: list[Node] = field(default_factory=list)
    elements: list[Element] = field(default_factory=list)
    supports: list[Support] = field(default_factory=list)
    loads: list[PointLoad] = field(default_factory=list)

    def add_node(self, x: float, y: float) -> int:
        for n in self.nodes:
            if abs(n.x - x) <= TOL and abs(n.y - y) <= TOL:
                return n.idx
        n = Node(x, y, len(self.nodes))
        self.nodes.append(n)
        return n.idx

    @property
    def ndof(self) -> int:
        return 3 * len(self.nodes)


# --------------------------------------------------------------------------
# ma tran phan tu
# --------------------------------------------------------------------------
def _geometry(m: Model, e: Element) -> None:
    n1, n2 = m.nodes[e.n1], m.nodes[e.n2]
    dx, dy = n2.x - n1.x, n2.y - n1.y
    e.L = math.hypot(dx, dy)
    if e.L <= TOL:
        raise ValueError("Phan tu co chieu dai bang 0 (hai nut trung nhau).")
    e.c, e.s = dx / e.L, dy / e.L


def _k_local(e: Element):
    E, A, I, L = e.E, e.A, e.I, e.L
    ea = E * A / L
    a = 12.0 * E * I / L ** 3
    b = 6.0 * E * I / L ** 2
    c4 = 4.0 * E * I / L
    c2 = 2.0 * E * I / L
    return [
        [ ea,  0.0, 0.0, -ea,  0.0, 0.0],
        [0.0,   a,   b,  0.0,  -a,   b ],
        [0.0,   b,  c4,  0.0,  -b,  c2 ],
        [-ea, 0.0, 0.0,  ea,  0.0, 0.0],
        [0.0,  -a,  -b,  0.0,   a,  -b ],
        [0.0,   b,  c2,  0.0,  -b,  c4 ],
    ]


def _kg_local(L: float, N: float):
    """Ma tran do cung hinh hoc (consistent). N duong = KEO."""
    f = N / L
    L2 = L * L
    return [
        [0.0, 0.0,        0.0,          0.0, 0.0,        0.0        ],
        [0.0, f * 1.2,    f * L / 10,   0.0, -f * 1.2,   f * L / 10 ],
        [0.0, f * L / 10, f * 2 * L2 / 15, 0.0, -f * L / 10, -f * L2 / 30],
        [0.0, 0.0,        0.0,          0.0, 0.0,        0.0        ],
        [0.0, -f * 1.2,   -f * L / 10,  0.0, f * 1.2,    -f * L / 10],
        [0.0, f * L / 10, -f * L2 / 30, 0.0, -f * L / 10, f * 2 * L2 / 15],
    ]


def _to_global(e: Element, kl):
    """T^T k T, khai trien truc tiep de khoi nhan ba ma tran 6x6."""
    c, s = e.c, e.s
    # T[i][j]
    T = [[c, s, 0, 0, 0, 0],
         [-s, c, 0, 0, 0, 0],
         [0, 0, 1, 0, 0, 0],
         [0, 0, 0, c, s, 0],
         [0, 0, 0, -s, c, 0],
         [0, 0, 0, 0, 0, 1]]
    # tmp = k*T
    tmp = [[sum(kl[i][k] * T[k][j] for k in range(6)) for j in range(6)]
           for i in range(6)]
    return [[sum(T[k][i] * tmp[k][j] for k in range(6)) for j in range(6)]
            for i in range(6)]


def _local_from_global(e: Element, ug):
    c, s = e.c, e.s
    return [c * ug[0] + s * ug[1],
            -s * ug[0] + c * ug[1],
            ug[2],
            c * ug[3] + s * ug[4],
            -s * ug[3] + c * ug[4],
            ug[5]]


def _global_from_local(e: Element, fl):
    c, s = e.c, e.s
    return [c * fl[0] - s * fl[1],
            s * fl[0] + c * fl[1],
            fl[2],
            c * fl[3] - s * fl[4],
            s * fl[3] + c * fl[4],
            fl[5]]


def _fef_local(e: Element):
    """Luc ngam hai dau do tai phan bo deu, he dia phuong."""
    p = e.wx * e.c + e.wy * e.s
    q = -e.wx * e.s + e.wy * e.c
    L = e.L
    return [-p * L / 2.0,
            -q * L / 2.0,
            -q * L * L / 12.0,
            -p * L / 2.0,
            -q * L / 2.0,
            q * L * L / 12.0]


def _dofs(e: Element) -> list[int]:
    return [3 * e.n1, 3 * e.n1 + 1, 3 * e.n1 + 2,
            3 * e.n2, 3 * e.n2 + 1, 3 * e.n2 + 2]


# --------------------------------------------------------------------------
# ket qua
# --------------------------------------------------------------------------
@dataclass
class ElementResult:
    element: int
    member: int
    L: float
    f_local: list[float]
    N: float                     # luc doc truc tai dau 2 (keo duong)
    N1: float                    # luc doc truc tai dau 1
    x: list[float]
    M: list[float]
    V: list[float]

    @property
    def M_max_abs(self) -> float:
        return max(abs(v) for v in self.M)

    @property
    def V_max_abs(self) -> float:
        return max(abs(v) for v in self.V)


@dataclass
class Solution:
    u: list[float]
    reactions: list[float]
    elements: list[ElementResult]
    free: list[int]
    L_chol: list[list[float]]

    def node_disp(self, i: int):
        return self.u[3 * i], self.u[3 * i + 1], self.u[3 * i + 2]

    @property
    def max_translation(self):
        best, at = 0.0, 0
        for i in range(len(self.u) // 3):
            d = math.hypot(self.u[3 * i], self.u[3 * i + 1])
            if d > best:
                best, at = d, i
        return best, at


# --------------------------------------------------------------------------
# lap rap va giai
# --------------------------------------------------------------------------
def assemble(m: Model):
    for e in m.elements:
        _geometry(m, e)

    n = m.ndof
    K = la.zeros(n, n)
    F = la.zeros(n)

    for e in m.elements:
        kg = _to_global(e, _k_local(e))
        d = _dofs(e)
        for a in range(6):
            Ka = K[d[a]]
            kga = kg[a]
            for b in range(6):
                Ka[d[b]] += kga[b]
        if e.wx or e.wy:
            fef = _fef_local(e)
            eq = _global_from_local(e, [-v for v in fef])
            for a in range(6):
                F[d[a]] += eq[a]

    for ld in m.loads:
        F[3 * ld.node] += ld.fx
        F[3 * ld.node + 1] += ld.fy
        F[3 * ld.node + 2] += ld.mz

    return K, F


def _free_dofs(m: Model) -> list[int]:
    fixed = [False] * m.ndof
    for s in m.supports:
        if s.ux:
            fixed[3 * s.node] = True
        if s.uy:
            fixed[3 * s.node + 1] = True
        if s.rz:
            fixed[3 * s.node + 2] = True
    return [i for i, f in enumerate(fixed) if not f]


def solve(m: Model, nstation: int = 21) -> Solution:
    K, F = assemble(m)
    free = _free_dofs(m)

    if not free:
        raise ValueError("Moi bac tu do deu bi khoa - khong co gi de giai.")
    if len(free) == m.ndof:
        raise ValueError(
            "Chua khai bao goi tua nao.\n"
            "Phai co it nhat mot nut duoc lien ket voi ket cau do.")

    Kff = la.submatrix(K, free)
    Ff = la.subvector(F, free)
    try:
        Lc = la.cholesky(Kff)
    except la.SingularMatrix as exc:
        raise ValueError(
            "Ket cau khong on dinh (thieu lien ket).\n\n%s\n\n"
            "Thuong gap khi: chi co mot goi khop ma khong co thanh giang, "
            "hai thanh khong thuc su noi voi nhau tai toa do trung nhau, "
            "hoac mot thanh bi tach roi khoi phan con lai." % exc) from exc

    uf = la.chol_solve(Lc, Ff)
    u = la.zeros(m.ndof)
    for k, i in enumerate(free):
        u[i] = uf[k]

    Ku = la.matvec(K, u)
    reactions = [Ku[i] - F[i] for i in range(m.ndof)]

    results = []
    for k, e in enumerate(m.elements):
        d = _dofs(e)
        ug = [u[i] for i in d]
        ul = _local_from_global(e, ug)
        kl = _k_local(e)
        fef = _fef_local(e)
        f = [sum(kl[i][j] * ul[j] for j in range(6)) + fef[i] for i in range(6)]

        # Voi tai phan bo doc truc, N bien thien tuyen tinh doc phan tu
        # -> phai giu ca hai dau, neu khong se bo sot gia tri lon nhat.
        N = f[3]
        N1 = -f[0]
        q = -e.wx * e.s + e.wy * e.c
        xs = [e.L * i / (nstation - 1) for i in range(nstation)]
        # Can bang doan [0, x] tinh tu dau 1 (f = luc tac dung LEN phan tu):
        #   sum Fy : f1 + q*x + V(x) = 0        -> V(x) = -f1 - q*x
        #   sum M  : f2 - f1*x - q*x^2/2 + M(x) = 0
        #                                       -> M(x) = -f2 + f1*x + q*x^2/2
        V = [-f[1] - q * x for x in xs]
        M = [-f[2] + f[1] * x + q * x * x / 2.0 for x in xs]

        results.append(ElementResult(k, e.member, e.L, f, N, N1, xs, M, V))

    return Solution(u, reactions, results, free, Lc)


MAX_DOF_BUCKLING = 400


def buckling(m: Model, sol: Solution, nmodes: int = 3):
    """Phan tich on dinh dan hoi bang tri rieng.

    Giai (K + lambda*Kg) phi = 0 voi Kg dung tu luc doc truc cua `sol`.
    lambda_cr = 2.5 nghia la ket cau mat on dinh khi tai hien tai tang 2.5 lan.

    Tra ve (danh sach lambda tang dan, danh sach dang mat on dinh, ghi chu).
    """
    free = sol.free
    if len(free) > MAX_DOF_BUCKLING:
        return [], [], ("Bo qua phan tich on dinh: mo hinh co %d bac tu do "
                        "(gioi han %d). Giam so doan chia moi thanh."
                        % (len(free), MAX_DOF_BUCKLING))

    n = m.ndof
    Kg = la.zeros(n, n)
    any_compression = False
    for e, r in zip(m.elements, sol.elements):
        if r.N < 0:
            any_compression = True
        kg = _to_global(e, _kg_local(e.L, r.N))
        d = _dofs(e)
        for a in range(6):
            row = Kg[d[a]]
            kga = kg[a]
            for b in range(6):
                row[d[b]] += kga[b]

    if not any_compression:
        return [], [], ("Khong co thanh nao chiu nen - ket cau khong the "
                        "mat on dinh duoi to hop tai nay.")

    G = [[-Kg[i][j] for j in free] for i in free]
    lams, modes_f = la.smallest_positive_eigen(sol.L_chol, G, nmodes=nmodes)

    shapes = []
    for mf in modes_f:
        phi = la.zeros(n)
        for k, i in enumerate(free):
            phi[i] = mf[k]
        shapes.append(phi)

    return lams, shapes, ""


# --------------------------------------------------------------------------
# tien ich chia luoi
# --------------------------------------------------------------------------
def mesh_member(m: Model, p1, p2, E, A, I, nseg, member,
                wx: float = 0.0, wy: float = 0.0, forced=None) -> list[int]:
    """Chia mot thanh vat ly thanh nhieu phan tu.

    `forced` la cac diem BAT BUOC co nut (vi du diem dat luc nam giua thanh).
    """
    (x1, y1), (x2, y2) = p1, p2
    L = math.hypot(x2 - x1, y2 - y1)
    if L <= TOL:
        raise ValueError("Thanh %d co chieu dai bang 0." % (member + 1))

    nseg = max(1, int(nseg))
    ts = {0.0, 1.0}
    for i in range(1, nseg):
        ts.add(i / nseg)

    for fx, fy in (forced or []):
        t = ((fx - x1) * (x2 - x1) + (fy - y1) * (y2 - y1)) / (L * L)
        if -1e-9 <= t <= 1 + 1e-9:
            px, py = x1 + t * (x2 - x1), y1 + t * (y2 - y1)
            if math.hypot(fx - px, fy - py) <= 1e-3:
                ts.add(min(1.0, max(0.0, t)))

    tl = sorted(ts)
    made = []
    for ta, tb in zip(tl[:-1], tl[1:]):
        if tb - ta < 1e-9:
            continue
        na = m.add_node(x1 + ta * (x2 - x1), y1 + ta * (y2 - y1))
        nb = m.add_node(x1 + tb * (x2 - x1), y1 + tb * (y2 - y1))
        m.elements.append(Element(na, nb, E, A, I, wx, wy, member))
        made.append(len(m.elements) - 1)
    return made


def point_on_segment(px, py, x1, y1, x2, y2):
    """Tra ve (khoang cach tu diem den doan thang, tham so t kep ve [0,1])."""
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    if L2 <= TOL:
        return math.hypot(px - x1, py - y1), 0.0
    t = ((px - x1) * dx + (py - y1) * dy) / L2
    tc = min(1.0, max(0.0, t))
    return math.hypot(px - (x1 + tc * dx), py - (y1 + tc * dy)), tc
