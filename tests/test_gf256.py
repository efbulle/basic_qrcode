import pytest

from basic_qrcode import gf256 as gf


def slow_mul(x, y, prim=0x11D):
    """Multiplication « à l'école » (décalages et XOR), indépendante des tables de logs."""
    r = 0
    while y:
        if y & 1:
            r ^= x
        y >>= 1
        x <<= 1
        if x & 0x100:
            x ^= prim
    return r


def test_mul_matches_schoolbook_multiplication():
    for x in range(256):
        for y in range(256):
            assert gf.mul(x, y) == slow_mul(x, y)


def test_div_and_inverse():
    for x in range(1, 256):
        assert gf.mul(x, gf.inv(x)) == 1
        for y in (1, 2, 3, 77, 255):
            assert gf.div(gf.mul(x, y), y) == x


def test_division_by_zero():
    with pytest.raises(ZeroDivisionError):
        gf.div(5, 0)


def test_alpha_is_primitive():
    powers = {gf.alpha_pow(k) for k in range(255)}
    assert powers == set(range(1, 256))
    assert gf.alpha_pow(255) == 1
    assert gf.mul(gf.alpha_pow(-3), gf.alpha_pow(3)) == 1


def test_poly_eval_and_mul():
    p = [3, 0, 1]  # 1·x² + 3
    assert gf.poly_eval(p, 0) == 3
    assert gf.poly_eval(p, 1) == 3 ^ 1
    q = [1, 1]  # x + 1
    for x in range(256):
        assert gf.poly_eval(gf.poly_mul(p, q), x) == gf.mul(
            gf.poly_eval(p, x), gf.poly_eval(q, x)
        )


def test_poly_derivative_char_2():
    # (x³ + x² + x + 1)' = 3x² + 2x + 1 = x² + 1 en caractéristique 2
    assert gf.poly_derivative([1, 1, 1, 1]) == [1, 0, 1]
