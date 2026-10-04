import random

import pytest
import reedsolo

from basic_qrcode.reed_solomon import (
    ReedSolomonError,
    calc_syndromes,
    generator_poly,
    rs_decode,
    rs_parity,
)

LEVELS = {"L": 10, "M": 16, "Q": 22, "H": 28}  # octets de correction en version 2
N = 44


def random_codeword(rng, nsym):
    data = [rng.randrange(256) for _ in range(N - nsym)]
    return data + rs_parity(data, nsym)


def test_generator_poly_roots():
    from basic_qrcode import gf256 as gf

    g = generator_poly(10)
    assert len(g) == 11 and g[-1] == 1
    for i in range(10):
        assert gf.poly_eval(g, gf.alpha_pow(i)) == 0
    assert gf.poly_eval(g, gf.alpha_pow(10)) != 0


@pytest.mark.parametrize("nsym", LEVELS.values())
def test_parity_matches_reedsolo(nsym):
    rng = random.Random(nsym)
    codec = reedsolo.RSCodec(nsym)
    for _ in range(50):
        data = [rng.randrange(256) for _ in range(N - nsym)]
        assert rs_parity(data, nsym) == list(codec.encode(bytes(data))[-nsym:])


@pytest.mark.parametrize("nsym", LEVELS.values())
def test_valid_codeword_has_zero_syndromes(nsym):
    word = random_codeword(random.Random(1), nsym)
    assert not any(calc_syndromes(word, nsym))
    assert rs_decode(word, nsym) == (word, [])


@pytest.mark.parametrize("nsym", LEVELS.values())
def test_corrects_up_to_capacity(nsym):
    rng = random.Random(nsym + 100)
    for _ in range(200):
        word = random_codeword(rng, nsym)
        positions = rng.sample(range(N), rng.randint(1, nsym // 2))
        damaged = list(word)
        for p in positions:
            damaged[p] ^= rng.randrange(1, 256)
        fixed, found = rs_decode(damaged, nsym)
        assert fixed == word
        assert found == sorted(positions)


@pytest.mark.parametrize("nsym", LEVELS.values())
def test_beyond_capacity_is_detected_or_gives_valid_codeword(nsym):
    """Au-delà de nsym // 2 erreurs, la détection n'est pas garantie : on exige seulement de
    ne jamais renvoyer un mot invalide, et de lever l'erreur dans la quasi-totalité des cas."""
    rng = random.Random(nsym + 200)
    trials, raised = 200, 0
    for _ in range(trials):
        word = random_codeword(rng, nsym)
        damaged = list(word)
        for p in rng.sample(range(N), nsym // 2 + 1):
            damaged[p] ^= rng.randrange(1, 256)
        try:
            fixed, _ = rs_decode(damaged, nsym)
        except ReedSolomonError:
            raised += 1
        else:
            assert not any(calc_syndromes(fixed, nsym))
    assert raised >= 0.9 * trials
