import random
import string

import numpy as np
import pytest
from conftest import MAX_LENGTH
from PIL import Image

from basic_qrcode import ReedSolomonError, decode_image, qr


def random_message(rng, ec_level):
    length = rng.randint(1, MAX_LENGTH[ec_level])
    return "".join(
        rng.choice(string.ascii_letters + string.digits + " .,!?-")
        for _ in range(length)
    )


def test_data_module_count():
    # 25 × 25 modules = 625, dont 359 de données : 44 octets + 7 bits de remplissage
    assert int((1 - qr.function_modules()).sum()) == 44 * 8 + 7


@pytest.mark.parametrize("mask", range(8))
@pytest.mark.parametrize("ec_level", ["L", "M", "Q", "H"])
def test_roundtrip(make_qr, ec_level, mask):
    rng = random.Random(f"{ec_level}{mask}")
    message = random_message(rng, ec_level)
    image = make_qr(
        message, ec_level, mask, scale=rng.choice([3, 5, 8]), border=rng.randint(1, 4)
    )
    result = decode_image(image)
    assert result.text == message
    assert result.ec_level == ec_level
    assert result.mask == mask
    assert result.corrected == ()


@pytest.mark.parametrize("ec_level", ["L", "M", "Q", "H"])
def test_maximum_length_message(make_qr, ec_level):
    message = "x" * MAX_LENGTH[ec_level]
    assert decode_image(make_qr(message, ec_level, 0)).text == message


def test_utf8_message(make_qr):
    # « é » occupe deux octets en UTF-8
    message = "Café à Paris"
    assert decode_image(make_qr(message, "M", 1)).text == message


def test_decode_from_file(make_qr, tmp_path):
    path = tmp_path / "qr.png"
    make_qr("Mon beau QR code !", "L", 2).save(path)
    assert decode_image(path).text == "Mon beau QR code !"


def damage(image, first_module, n_modules, scale=5, border=4):
    """Recouvre un carré de n_modules × n_modules modules par un aplat rouge
    (le rouge devient noir à la binarisation)."""
    pixels = np.array(image.convert("RGB"))
    start = (border + first_module) * scale
    size = n_modules * scale
    pixels[start : start + size, start : start + size] = [255, 0, 0]
    return Image.fromarray(pixels)


MESSAGE = "Mon beau QR code !"


def test_damage_within_capacity(make_qr):
    # niveau M : 16 octets de correction, donc 8 octets erronés corrigeables
    image = damage(make_qr(MESSAGE, "M", 3), first_module=10, n_modules=5)
    result = decode_image(image)
    assert result.text == MESSAGE
    assert 0 < len(result.corrected) <= 8


def test_damage_at_the_limit(make_qr):
    image = damage(make_qr(MESSAGE, "M", 3), first_module=10, n_modules=6)
    result = decode_image(image)
    assert result.text == MESSAGE
    assert len(result.corrected) == 8


def test_damage_beyond_capacity(make_qr):
    image = damage(make_qr(MESSAGE, "M", 3), first_module=8, n_modules=8)
    with pytest.raises(ReedSolomonError):
        decode_image(image)


def test_blank_image_is_rejected():
    with pytest.raises(ValueError, match="aucun pixel noir"):
        decode_image(Image.new("L", (100, 100), 255))


def test_not_a_square_is_rejected():
    image = Image.new("L", (200, 100), 255)
    image.paste(0, (10, 10, 190, 60))
    with pytest.raises(ValueError, match="carré"):
        decode_image(image)


def test_modules_without_finder_patterns_are_rejected():
    with pytest.raises(ValueError, match="repérage"):
        qr.decode_modules(np.zeros((25, 25), dtype=int))


def test_wrong_size_is_rejected():
    with pytest.raises(ValueError, match="version 2"):
        qr.decode_modules(np.zeros((21, 21), dtype=int))
