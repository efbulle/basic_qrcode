"""Arithmétique dans le corps fini GF(2^8) et sur les polynômes à coefficients dans ce corps.

Les octets sont vus comme des polynômes à coefficients dans {0, 1}, modulo le polynôme
irréductible x^8 + x^4 + x^3 + x^2 + 1 (0x11D), celui qu'utilisent les QR codes.
L'élément α = 2 engendre tous les éléments non nuls : on calcule donc produits et
quotients par des tables de logarithmes.

Convention pour les polynômes : une liste de coefficients par puissances CROISSANTES
(``p[i]`` est le coefficient de x^i).
"""

PRIMITIVE_POLY = 0x11D


def _build_tables(prim=PRIMITIVE_POLY):
    exp = [0] * 512  # table doublée : évite un "% 255" dans mul()
    log = [0] * 256
    x = 1
    for i in range(255):
        exp[i] = x
        log[x] = i
        x <<= 1  # multiplication par α
        if x & 0x100:
            x ^= prim
    for i in range(255, 512):
        exp[i] = exp[i - 255]
    return exp, log


EXP, LOG = _build_tables()


def alpha_pow(k):
    """α^k, pour tout entier k (positif ou négatif)."""
    return EXP[k % 255]


def mul(x, y):
    if x == 0 or y == 0:
        return 0
    return EXP[LOG[x] + LOG[y]]


def div(x, y):
    if y == 0:
        raise ZeroDivisionError("division par 0 dans GF(256)")
    if x == 0:
        return 0
    return EXP[LOG[x] - LOG[y] + 255]


def inv(x):
    return div(1, x)


# --- polynômes (coefficients par puissances croissantes) ---------------------------------


def poly_scale(p, c):
    return [mul(a, c) for a in p]


def poly_add(p, q):
    """Somme (= différence : c'est un XOR) de deux polynômes."""
    r = [0] * max(len(p), len(q))
    for i, a in enumerate(p):
        r[i] ^= a
    for i, a in enumerate(q):
        r[i] ^= a
    return r


def poly_mul(p, q):
    r = [0] * (len(p) + len(q) - 1)
    for i, a in enumerate(p):
        for j, b in enumerate(q):
            r[i + j] ^= mul(a, b)
    return r


def poly_eval(p, x):
    """Évalue p en x par la méthode de Horner."""
    y = 0
    for coef in reversed(p):
        y = mul(y, x) ^ coef
    return y


def poly_trim(p):
    """Supprime les coefficients nuls de plus haut degré (en gardant au moins un terme)."""
    n = len(p)
    while n > 1 and p[n - 1] == 0:
        n -= 1
    return p[:n]


def poly_derivative(p):
    """Dérivée formelle. En caractéristique 2, n·c = c si n est impair et 0 sinon."""
    return [p[i] if i % 2 == 1 else 0 for i in range(1, len(p))] or [0]
