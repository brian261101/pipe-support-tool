"""Kiem chung solver PTHH bang cac bai toan co nghiem giai tich.

Chay:  python tests/verify_fem.py
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from psat import fem  # noqa: E402

E = 210000.0          # MPa
A = 3000.0            # mm^2
I = 2.0e7             # mm^4
L = 3000.0            # mm

_fails = []


def check(name, got, want, rtol=2e-3, atol=None):
    # khi gia tri dich bang 0 thi chi so tuong doi vo nghia
    tol = rtol * abs(want) if want else (atol if atol is not None else 1e-6)
    ok = abs(got - want) <= tol
    print("  %-52s %14.6g  %14.6g   %s"
          % (name, got, want, "OK" if ok else "*** SAI ***"))
    if not ok:
        _fails.append(name)


def cantilever_point():
    """Cong xon, luc tap trung P o dau tu do."""
    P = -5000.0                                   # N, huong xuong
    m = fem.Model()
    fem.mesh_member(m, (0, 0), (L, 0), E, A, I, nseg=8, member=0)
    tip = m.add_node(L, 0)
    m.supports.append(fem.Support(m.add_node(0, 0)))
    m.loads.append(fem.PointLoad(tip, fy=P))
    s = fem.solve(m)

    dy = s.node_disp(tip)[1]
    check("cong xon + P: chuyen vi dau tu do [mm]",
          dy, P * L ** 3 / (3 * E * I))

    mmax = max(r.M_max_abs for r in s.elements)
    check("cong xon + P: moment ngam [N.mm]", mmax, abs(P) * L)


def cantilever_udl():
    """Cong xon, tai phan bo deu w."""
    w = -2.0                                       # N/mm huong xuong
    m = fem.Model()
    fem.mesh_member(m, (0, 0), (L, 0), E, A, I, nseg=10, member=0, wy=w)
    tip = m.add_node(L, 0)
    m.supports.append(fem.Support(m.add_node(0, 0)))
    s = fem.solve(m)

    dy = s.node_disp(tip)[1]
    check("cong xon + UDL: chuyen vi dau tu do [mm]",
          dy, w * L ** 4 / (8 * E * I))

    mmax = max(r.M_max_abs for r in s.elements)
    check("cong xon + UDL: moment ngam [N.mm]", mmax, abs(w) * L ** 2 / 2)


def simply_supported_mid():
    """Dam don gian, luc tap trung giua nhip."""
    P = -8000.0
    m = fem.Model()
    fem.mesh_member(m, (0, 0), (L, 0), E, A, I, nseg=8, member=0,
                    forced=[(L / 2, 0.0)])
    n0 = m.add_node(0, 0)
    n1 = m.add_node(L, 0)
    nm = m.add_node(L / 2, 0)
    m.supports.append(fem.Support(n0, ux=True, uy=True, rz=False))
    m.supports.append(fem.Support(n1, ux=False, uy=True, rz=False))
    m.loads.append(fem.PointLoad(nm, fy=P))
    s = fem.solve(m)

    check("dam don gian + P giua nhip: do vong [mm]",
          s.node_disp(nm)[1], P * L ** 3 / (48 * E * I))
    check("dam don gian + P giua nhip: moment max [N.mm]",
          max(r.M_max_abs for r in s.elements), abs(P) * L / 4)


def axial_bar():
    """Thanh chiu keo doc truc."""
    P = 40000.0
    m = fem.Model()
    fem.mesh_member(m, (0, 0), (0, L), E, A, I, nseg=4, member=0)
    top = m.add_node(0, L)
    m.supports.append(fem.Support(m.add_node(0, 0)))
    m.loads.append(fem.PointLoad(top, fy=P))
    s = fem.solve(m)

    check("thanh keo doc truc: gian dai [mm]",
          s.node_disp(top)[1], P * L / (E * A))
    check("thanh keo doc truc: luc doc truc [N] (keo duong)",
          s.elements[0].N, P)


def euler_pinned():
    """Cot hai dau khop:  Pcr = pi^2 EI / L^2."""
    m = fem.Model()
    fem.mesh_member(m, (0, 0), (0, L), E, A, I, nseg=10, member=0)
    base = m.add_node(0, 0)
    top = m.add_node(0, L)
    m.supports.append(fem.Support(base, ux=True, uy=True, rz=False))
    m.supports.append(fem.Support(top, ux=True, uy=False, rz=False))
    m.loads.append(fem.PointLoad(top, fy=-1000.0))
    s = fem.solve(m)
    lam, _, _ = fem.buckling(m, s)

    check("cot 2 dau khop: Pcr [N]", lam[0] * 1000.0,
          math.pi ** 2 * E * I / L ** 2, rtol=5e-3)


def euler_fixed_free():
    """Cot ngam - tu do:  Pcr = pi^2 EI / (2L)^2."""
    m = fem.Model()
    fem.mesh_member(m, (0, 0), (0, L), E, A, I, nseg=12, member=0)
    base = m.add_node(0, 0)
    top = m.add_node(0, L)
    m.supports.append(fem.Support(base))               # ngam hoan toan
    m.loads.append(fem.PointLoad(top, fy=-1000.0))
    s = fem.solve(m)
    lam, _, _ = fem.buckling(m, s)

    check("cot ngam - tu do: Pcr [N]", lam[0] * 1000.0,
          math.pi ** 2 * E * I / (2 * L) ** 2, rtol=5e-3)


def euler_fixed_pinned():
    """Cot ngam - khop:  Pcr = pi^2 EI / (0.6992 L)^2."""
    m = fem.Model()
    fem.mesh_member(m, (0, 0), (0, L), E, A, I, nseg=12, member=0)
    base = m.add_node(0, 0)
    top = m.add_node(0, L)
    m.supports.append(fem.Support(base))                          # ngam
    m.supports.append(fem.Support(top, ux=True, uy=False, rz=False))  # khop truot
    m.loads.append(fem.PointLoad(top, fy=-1000.0))
    s = fem.solve(m)
    lam, _, _ = fem.buckling(m, s)

    check("cot ngam - khop: Pcr [N]", lam[0] * 1000.0,
          math.pi ** 2 * E * I / (0.6992 * L) ** 2, rtol=1e-2)


def equilibrium():
    """Tong phan luc phai can bang voi tong tai tac dung."""
    m = fem.Model()
    fem.mesh_member(m, (0, 0), (0, 2000), E, A, I, nseg=4, member=0)
    fem.mesh_member(m, (0, 2000), (2500, 2000), E, A, I, nseg=6, member=1, wy=-1.5)
    base = m.add_node(0, 0)
    tip = m.add_node(2500, 2000)
    m.supports.append(fem.Support(base))
    m.loads.append(fem.PointLoad(tip, fy=-7000.0, fx=1200.0))
    s = fem.solve(m)

    rx = s.reactions[3 * base]
    ry = s.reactions[3 * base + 1]
    check("can bang khung: tong Fx [N]", rx + 1200.0, 0.0, atol=1e-6)
    check("can bang khung: tong Fy [N]", ry - 7000.0 - 1.5 * 2500, 0.0, atol=1e-6)


if __name__ == "__main__":
    print("%-54s %14s %14s" % ("KIEM CHUNG PTHH", "PTHH", "GIAI TICH"))
    print("-" * 92)
    cantilever_point()
    cantilever_udl()
    simply_supported_mid()
    axial_bar()
    euler_pinned()
    euler_fixed_free()
    euler_fixed_pinned()
    equilibrium()
    print("-" * 92)
    if _fails:
        print("THAT BAI: %d phep kiem tra" % len(_fails))
        for f in _fails:
            print("   -", f)
        sys.exit(1)
    print("TAT CA DEU DAT.")
