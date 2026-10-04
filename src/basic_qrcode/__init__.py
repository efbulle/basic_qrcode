"""Décodage pédagogique d'un QR code (version 2, mode octets) : de l'image au texte."""

from .qr import DecodedQR, decode_image, decode_modules
from .reed_solomon import ReedSolomonError

__all__ = ["DecodedQR", "ReedSolomonError", "decode_image", "decode_modules"]
