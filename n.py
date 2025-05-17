import numpy as np

# f(t) 関数
def f(t):
    delta = 6/29
    if t > delta**3:
        return t ** (1/3)
    else:
        return t / (3 * delta**2) + 4/29

# XYZ → LAB変換
def xyz_to_lab(X, Y, Z, Xn, Yn, Zn):
    fx = f(X / Xn)
    fy = f(Y / Yn)
    fz = f(Z / Zn)

    L = 116 * fy - 16
    a = 500 * (fx - fy)
    b = 200 * (fy - fz)

    return L, a, b

# (1) の計算
Xn, Yn, Zn = 95.04, 100.00, 108.88
X1, Y1, Z1 = 30, 50, 60

L1, a1, b1 = xyz_to_lab(X1, Y1, Z1, Xn, Yn, Zn)
print(f"(1) L* = {L1:.2f}, a* = {a1:.2f}, b* = {b1:.2f}")

# (2) の計算
X2, Y2, Z2 = 60, 100, 90

L2, a2, b2 = xyz_to_lab(X2, Y2, Z2, Xn, Yn, Zn)

deltaE = np.sqrt((L1 - L2)**2 + (a1 - a2)**2 + (b1 - b2)**2)
print(f"(2) 色差 ΔE = {deltaE:.2f}")
