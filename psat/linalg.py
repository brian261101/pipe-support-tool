"""Dai so tuyen tinh thuan Python - khong can numpy/scipy.

Ma tran = list cac list (hang), vector = list float.

Du cho bai toan PTHH khung phang co vai tram bac tu do. Cac ham deu viet
theo huong "vong lap chat", tranh tao doi tuong trung gian.
"""

from __future__ import annotations

import math


class SingularMatrix(Exception):
    """Ma tran khong kha nghich / khong xac dinh duong.

    Trong bai toan ket cau, dieu nay gan nhu luon co nghia la ket cau
    thieu lien ket (co cau) chu khong phai loi so hoc.
    """


# --------------------------------------------------------------------------
# tien ich
# --------------------------------------------------------------------------
def zeros(n: int, m: int | None = None):
    if m is None:
        return [0.0] * n
    return [[0.0] * m for _ in range(n)]


def dot(a: list[float], b: list[float]) -> float:
    s = 0.0
    for i in range(len(a)):
        s += a[i] * b[i]
    return s


def norm(a: list[float]) -> float:
    return math.sqrt(dot(a, a))


def scale(a: list[float], k: float) -> list[float]:
    return [v * k for v in a]


def matvec(A, x: list[float]) -> list[float]:
    n = len(A)
    out = [0.0] * n
    for i in range(n):
        Ai = A[i]
        s = 0.0
        for j in range(len(x)):
            v = Ai[j]
            if v:
                s += v * x[j]
        out[i] = s
    return out


def submatrix(A, idx: list[int]):
    return [[A[i][j] for j in idx] for i in idx]


def subvector(v: list[float], idx: list[int]) -> list[float]:
    return [v[i] for i in idx]


# --------------------------------------------------------------------------
# Cholesky  A = L L^T   (A doi xung, xac dinh duong)
# --------------------------------------------------------------------------
def cholesky(A) -> list[list[float]]:
    """Phan tich Cholesky. Nem SingularMatrix neu A khong xac dinh duong."""
    n = len(A)
    L = [[0.0] * n for _ in range(n)]
    for i in range(n):
        Li = L[i]
        Ai = A[i]
        for j in range(i + 1):
            Lj = L[j]
            s = 0.0
            for k in range(j):
                s += Li[k] * Lj[k]
            if i == j:
                d = Ai[i] - s
                if d <= 1e-12 * max(1.0, abs(Ai[i])):
                    raise SingularMatrix(
                        "Ma tran do cung khong xac dinh duong tai bac tu do %d. "
                        "Ket cau thieu lien ket hoac co thanh bi tach roi." % i)
                Li[j] = math.sqrt(d)
            else:
                Li[j] = (Ai[j] - s) / Lj[j]
    return L


def forward_sub(L, b: list[float]) -> list[float]:
    """Giai L y = b, L tam giac duoi."""
    n = len(L)
    y = [0.0] * n
    for i in range(n):
        Li = L[i]
        s = b[i]
        for k in range(i):
            s -= Li[k] * y[k]
        y[i] = s / Li[i]
    return y


def back_sub_T(L, y: list[float]) -> list[float]:
    """Giai L^T x = y, L tam giac duoi."""
    n = len(L)
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = y[i]
        for k in range(i + 1, n):
            s -= L[k][i] * x[k]
        x[i] = s / L[i][i]
    return x


def chol_solve(L, b: list[float]) -> list[float]:
    return back_sub_T(L, forward_sub(L, b))


def solve_spd(A, b: list[float]) -> list[float]:
    return chol_solve(cholesky(A), b)


# --------------------------------------------------------------------------
# tri rieng: bai toan K phi = lambda (-Kg) phi
# --------------------------------------------------------------------------
def _orthogonalize(v: list[float], basis: list[list[float]]) -> list[float]:
    for u in basis:
        c = dot(v, u)
        for i in range(len(v)):
            v[i] -= c * u[i]
    return v


def smallest_positive_eigen(L, G, nmodes: int = 3, iters: int = 300,
                            tol: float = 1e-9):
    """Tim cac he so tai toi han nho nhat cua  K phi = lambda * G * phi.

    `L` la Cholesky cua K, `G` la ma tran (-Kg) - doi xung.

    Doi bien psi = L^T phi  ->  M psi = (1/lambda) psi  voi
    M = L^-1 G L^-T (doi xung). M khong bao gio duoc dung hien;
    moi buoc lap chi can mot phep the thuan va mot phep the nguoc.

    Tra ve (danh sach lambda tang dan, danh sach dang phi tuong ung).
    """
    n = len(L)

    def M_apply(psi: list[float]) -> list[float]:
        z = back_sub_T(L, psi)          # z = L^-T psi
        w = matvec(G, z)                # w = G z
        return forward_sub(L, w)        # L^-1 w

    def rayleigh(v):
        return dot(v, M_apply(v))

    def power(shift, basis, iters_):
        """Lap luy thua tren (M + shift*I), da truc giao voi `basis`."""
        v = [math.sin(3.0 * i + 1.0) for i in range(n)]
        _orthogonalize(v, basis)
        nv = norm(v)
        if nv < 1e-300:
            return None, None
        v = scale(v, 1.0 / nv)
        mu = 0.0
        for it in range(iters_):
            w = M_apply(v)
            if shift:
                for i in range(n):
                    w[i] += shift * v[i]
            _orthogonalize(w, basis)
            nw = norm(w)
            if nw < 1e-300:
                return None, None
            w = scale(w, 1.0 / nw)
            mu_new = rayleigh(w)
            if it > 5 and abs(mu_new - mu) <= tol * max(1.0, abs(mu_new)):
                return mu_new, w
            v, mu = w, mu_new
        return mu, v

    # Hai giai doan. Voi bai toan on dinh thong thuong (cac thanh chiu nen),
    # pho cua M khong am nen KHONG can dich - lap luy thua tran hoi tu rat
    # nhanh theo ty so lambda_1/lambda_2. Chi khi tri rieng troi lai am
    # (mat on dinh duoi tai dao chieu) moi can dich, va khi do dich dung
    # bang do lon cua no - dich lon hon se lam hoi tu cham di rat nhieu.
    mu0, _ = power(0.0, [], iters)
    if mu0 is None:
        return [], []
    base_shift = 0.0 if mu0 > 0 else abs(mu0) * 1.02

    lams: list[float] = []
    modes: list[list[float]] = []
    found: list[list[float]] = []

    for _ in range(nmodes):
        mu, v = power(base_shift, found, iters)
        if mu is None or mu <= 1e-14:
            break                            # khong con tri rieng duong
        lam = 1.0 / mu
        phi = back_sub_T(L, v)               # doi nguoc ve phi
        mx = max((abs(x) for x in phi), default=0.0)
        if mx > 0:
            phi = scale(phi, 1.0 / mx)
        lams.append(lam)
        modes.append(phi)
        found.append(v[:])

    order = sorted(range(len(lams)), key=lambda i: lams[i])
    return [lams[i] for i in order], [modes[i] for i in order]
