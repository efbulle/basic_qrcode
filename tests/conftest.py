"""Fabrication d'images de QR codes de test avec deux bibliothèques indépendantes."""

import io

import pytest
import qrcode
import segno
from PIL import Image
from qrcode.constants import (
    ERROR_CORRECT_H,
    ERROR_CORRECT_L,
    ERROR_CORRECT_M,
    ERROR_CORRECT_Q,
)
from qrcode.image.pil import PilImage
from qrcode.util import QRData

QRCODE_LEVELS = {
    "L": ERROR_CORRECT_L,
    "M": ERROR_CORRECT_M,
    "Q": ERROR_CORRECT_Q,
    "H": ERROR_CORRECT_H,
}

# Longueur maximale d'un message en mode octets, version 2, par niveau de correction.
MAX_LENGTH = {"L": 32, "M": 26, "Q": 20, "H": 14}


def make_with_segno(message, ec_level, mask, scale=5, border=4):
    qr = segno.make_qr(
        message, error=ec_level, boost_error=False, version=2, mask=mask, mode="byte"
    )
    buffer = io.BytesIO()
    qr.save(buffer, kind="png", scale=scale, border=border)
    return Image.open(buffer).convert("RGB")


def make_with_qrcode(message, ec_level, mask, scale=5, border=4):
    qr = qrcode.QRCode(
        version=2,
        error_correction=QRCODE_LEVELS[ec_level],
        box_size=scale,
        border=border,
        mask_pattern=mask,
    )
    qr.add_data(QRData(message.encode(), mode=4))
    qr.make(fit=False)
    return qr.make_image(image_factory=PilImage).convert("RGB")


@pytest.fixture(params=[make_with_segno, make_with_qrcode], ids=["segno", "qrcode"])
def make_qr(request):
    return request.param
