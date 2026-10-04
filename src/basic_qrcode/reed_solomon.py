"""Code de Reed-Solomon tel qu'il est utilisé dans les QR codes.

Un mot de code est une liste d'octets ``[données..., parité...]``, vue comme le polynôme
m(x) = msg[0]·x^(n-1) + ... + msg[n-1]. Le polynôme générateur est
g(x) = (x - α^0)(x - α^1)...(x - α^(nsym-1)) : un mot de code valide s'annule en
α^0, ..., α^(nsym-1). Les « syndromes » S_j = m(α^j) mesurent l'écart à un mot valide.

Le décodeur ci-dessous corrige jusqu'à nsym // 2 octets erronés, à des positions inconnues
(pas de gestion des effacements). Étapes :

1. syndromes ;
2. polynôme localisateur d'erreurs Λ(x), par l'algorithme de Berlekamp-Massey ;
3. positions des erreurs : racines de Λ, par recherche exhaustive (Chien) ;
4. valeurs des erreurs, par la formule de Forney ;
5. vérification : les syndromes du mot corrigé doivent tous être nuls.
"""

from . import gf256 as gf


class ReedSolomonError(ValueError):
    """Le mot de code contient trop d'erreurs pour être corrigé."""


def generator_poly(nsym):
    """g(x) = Π (x + α^i) pour i < nsym (croissant : le dernier coefficient vaut 1)."""
    g = [1]
    for i in range(nsym):
        g = gf.poly_mul(g, [gf.alpha_pow(i), 1])
    return g


def rs_parity(data, nsym):
    """Octets de parité : reste de la division de data(x)·x^nsym par g(x)."""
    gen = generator_poly(nsym)[::-1]  # décroissant, gen[0] == 1
    rem = [0] * nsym
    for byte in data:
        factor = byte ^ rem[0]
        rem = rem[1:] + [0]
        for i in range(nsym):
            rem[i] ^= gf.mul(gen[i + 1], factor)
    return rem


def calc_syndromes(msg, nsym):
    poly = list(msg)[
        ::-1
    ]  # le premier octet transmis est le coefficient de plus haut degré
    return [gf.poly_eval(poly, gf.alpha_pow(j)) for j in range(nsym)]


def berlekamp_massey(synd):
    """Polynôme localisateur Λ(x) = 1 + Λ1·x + ... (croissant) et son degré L.

    On construit Λ de façon itérative pour que la récurrence linéaire
    S_n + Λ1·S_(n-1) + ... + ΛL·S_(n-L) = 0 soit vérifiée pour tous les n.
    À chaque étape on mesure l'écart d (« discrepancy ») : s'il est non nul, on corrige Λ
    avec l'ancien polynôme B décalé de m rangs.
    """
    lam, prev = [1], [1]
    L, m, b = 0, 1, 1
    for n, s in enumerate(synd):
        d = s
        for i in range(1, min(L, len(lam) - 1) + 1):
            d ^= gf.mul(lam[i], synd[n - i])
        if d == 0:
            m += 1
            continue
        update = [0] * m + gf.poly_scale(prev, gf.div(d, b))
        old = lam
        lam = gf.poly_add(lam, update)
        if 2 * L <= n:
            L, prev, b, m = n + 1 - L, old, d, 1
        else:
            m += 1
    return gf.poly_trim(lam), L


def find_error_powers(lam, n):
    """Exposants j (0 ≤ j < n) tels que Λ(α^-j) = 0 : l'octet d'indice n-1-j est erroné."""
    return [j for j in range(n) if gf.poly_eval(lam, gf.alpha_pow(-j)) == 0]


def error_values(synd, lam, powers):
    """Formule de Forney (première racine du générateur : α^0) : e = X·Ω(1/X) / Λ'(1/X),
    avec X = α^j et Ω(x) = S(x)·Λ(x) mod x^nsym."""
    nsym = len(synd)
    omega = gf.poly_mul(synd, lam)[:nsym]
    dlam = gf.poly_derivative(lam)
    values = []
    for j in powers:
        x = gf.alpha_pow(j)
        x_inv = gf.alpha_pow(-j)
        denom = gf.poly_eval(dlam, x_inv)
        if denom == 0:
            raise ReedSolomonError("localisateur dégénéré")
        values.append(gf.div(gf.mul(x, gf.poly_eval(omega, x_inv)), denom))
    return values


def rs_decode(msg, nsym):
    """Corrige ``msg`` (données + nsym octets de parité).

    Renvoie ``(mot_corrigé, positions)`` où ``positions`` liste les indices corrigés.
    Lève ``ReedSolomonError`` si la correction échoue. Au-delà de nsym // 2 erreurs, le
    décodeur détecte presque toujours l'échec mais pas à coup sûr : il peut aussi
    « corriger » vers un autre mot de code valide.
    """
    msg = list(msg)
    n = len(msg)
    synd = calc_syndromes(msg, nsym)
    if not any(synd):
        return msg, []

    lam, L = berlekamp_massey(synd)
    if len(lam) - 1 != L or 2 * L > nsym:
        raise ReedSolomonError(
            f"trop d'erreurs ({L} localisées, {nsym // 2} corrigeables)"
        )

    powers = find_error_powers(lam, n)
    if len(powers) != L:
        raise ReedSolomonError("positions des erreurs introuvables")

    for j, e in zip(powers, error_values(synd, lam, powers)):
        msg[n - 1 - j] ^= e

    if any(calc_syndromes(msg, nsym)):
        raise ReedSolomonError("le mot corrigé n'est pas un mot de code valide")
    return msg, sorted(n - 1 - j for j in powers)
