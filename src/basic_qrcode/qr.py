"""Décodage d'une image de QR code, dans un cas particulier seulement.

Cas géré : version 2 (25×25 modules), mode « octets » (byte), un seul bloc de
correction d'erreur (c'est le cas des quatre niveaux L, M, Q, H en version 2).

Les étapes sont des fonctions séparées pour pouvoir être montrées une à une dans les
notebooks. Dans les tableaux de modules, 1 = module noir et 0 = module blanc
(c'est l'inverse de la convention des niveaux de gris d'une image).

Limites volontaires : un seul des deux exemplaires de l'information de format est lu, et
ses 10 bits de correction (code BCH) ne sont pas exploités.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from .reed_solomon import rs_decode

VERSION = 2
SIZE = 4 * VERSION + 17  # 25 modules de côté
N_CODEWORDS = 44  # octets au total (données + correction) en version 2

# Les deux premiers bits (après démasquage) de l'information de format donnent le niveau.
EC_LEVELS = {0b01: "L", 0b00: "M", 0b11: "Q", 0b10: "H"}
# Octets de correction d'erreur en version 2 (source : qrcode.com/en/about/version.html).
EC_CODEWORDS = {"L": 10, "M": 16, "Q": 22, "H": 28}
FORMAT_XOR_MASK = 0b101010000010010

# Motifs de masque : un module de coordonnées (i, j) est inversé si la fonction est vraie.
MASK_FUNCTIONS = {
    0: lambda i, j: (i + j) % 2 == 0,
    1: lambda i, j: i % 2 == 0,
    2: lambda i, j: j % 3 == 0,
    3: lambda i, j: (i + j) % 3 == 0,
    4: lambda i, j: (i // 2 + j // 3) % 2 == 0,
    5: lambda i, j: (i * j) % 2 + (i * j) % 3 == 0,
    6: lambda i, j: ((i * j) % 2 + (i * j) % 3) % 2 == 0,
    7: lambda i, j: ((i * j) % 3 + (i + j) % 2) % 2 == 0,
}

BYTE_MODE = 0b0100


@dataclass(frozen=True)
class DecodedQR:
    data: bytes
    ec_level: str
    mask: int
    corrected: tuple  # indices des octets (codewords) corrigés par Reed-Solomon

    @property
    def text(self):
        """Le message en texte (UTF-8 si possible, sinon ISO-8859-1, l'encodage par défaut
        de la norme)."""
        try:
            return self.data.decode("utf-8")
        except UnicodeDecodeError:
            return self.data.decode("latin-1")


# --- 1. de l'image au tableau de modules ---------------------------------------------------


def image_to_modules(image):
    """Convertit une image (chemin ou image PIL) en tableau 25×25 de 0/1 (1 = noir).

    L'image est passée en niveaux de gris puis binarisée au seuil 128. Le QR code est
    cadré par la boîte englobante des pixels noirs (la zone de silence blanche autour
    n'a pas d'importance) puis découpé en 25×25 blocs ; chaque module prend la couleur
    majoritaire de son bloc.
    """
    if not isinstance(image, Image.Image):
        image = Image.open(Path(image))
    gray = np.array(image.convert("L"))
    dark = gray < 128

    ys, xs = np.nonzero(dark)
    if len(ys) == 0:
        raise ValueError("aucun pixel noir dans l'image")
    crop = dark[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]
    height, width = crop.shape
    if abs(height - width) > 1 or min(height, width) < SIZE:
        raise ValueError(
            f"la zone noire ({width}×{height} pixels) n'est pas un QR code carré"
        )

    # Bornes des blocs, valables aussi si la taille d'un module n'est pas entière.
    bounds_y = np.round(np.linspace(0, height, SIZE + 1)).astype(int)
    bounds_x = np.round(np.linspace(0, width, SIZE + 1)).astype(int)
    modules = np.zeros((SIZE, SIZE), dtype=int)
    for i in range(SIZE):
        for j in range(SIZE):
            block = crop[bounds_y[i] : bounds_y[i + 1], bounds_x[j] : bounds_x[j + 1]]
            modules[i, j] = int(block.mean() > 0.5)
    return modules


def check_finder_patterns(modules):
    """Vérifie les trois motifs de repérage (carré noir 7×7, anneau blanc, carré noir 3×3)."""
    pattern = np.zeros((7, 7), dtype=int)
    pattern[0, :] = pattern[-1, :] = pattern[:, 0] = pattern[:, -1] = 1
    pattern[2:5, 2:5] = 1
    corners = [(0, 0), (0, SIZE - 7), (SIZE - 7, 0)]
    for r, c in corners:
        if not np.array_equal(modules[r : r + 7, c : c + 7], pattern):
            raise ValueError(f"motif de repérage absent ou abîmé en ({r}, {c})")


# --- 2. information de format et masque ----------------------------------------------------


def read_format(modules):
    """Niveau de correction (« L », « M », « Q » ou « H ») et numéro de masque (0 à 7)."""
    bits = (
        modules[8, :6].tolist()
        + modules[8, 7:9].tolist()
        + [modules[7, 8]]
        + modules[:6, 8][::-1].tolist()
    )
    value = int("".join(str(b) for b in bits), 2) ^ FORMAT_XOR_MASK
    return EC_LEVELS[value >> 13], (value >> 10) & 0b111


def mask_matrix(mask):
    func = MASK_FUNCTIONS[mask]
    return np.array([[int(func(i, j)) for j in range(SIZE)] for i in range(SIZE)])


def unmask(modules, mask):
    return modules ^ mask_matrix(mask)


# --- 3. lecture des octets -----------------------------------------------------------------


def is_function_module(row, col):
    """Vrai pour les modules qui ne portent pas de données (version 2 uniquement)."""
    # motifs de repérage et leurs séparateurs
    if (
        (row <= 7 and col <= 7)
        or (row <= 7 and col >= SIZE - 8)
        or (row >= SIZE - 8 and col <= 7)
    ):
        return True
    # motifs de synchronisation
    if row == 6 or col == 6:
        return True
    # motif d'alignement (5×5, centré en (18, 18) en version 2)
    if 16 <= row <= 20 and 16 <= col <= 20:
        return True
    # information de format (les deux exemplaires) et module noir fixe
    return bool(
        (row < 9 and col == 8)
        or (row == 8 and col < 9)
        or (row == 8 and col > SIZE - 9)
        or (row > SIZE - 9 and col == 8)
    )


def function_modules():
    """Tableau 25×25 : 1 pour les modules de fonction, 0 pour les modules de données."""
    return np.array(
        [[int(is_function_module(i, j)) for j in range(SIZE)] for i in range(SIZE)]
    )


def read_data_bits(modules):
    """Parcourt le QR code en zigzag, par bandes de deux colonnes en partant du coin
    inférieur droit (montante, puis descendante, etc.), en sautant les modules de fonction
    et la colonne de synchronisation."""
    bits = []
    upward = True
    col = SIZE - 1
    while col >= 0:
        if col == 6:  # colonne de synchronisation : on la saute
            col -= 1
        rows = range(SIZE - 1, -1, -1) if upward else range(SIZE)
        for row in rows:
            for c in (col, col - 1):  # d'abord la colonne de droite de la bande
                if not is_function_module(row, c):
                    bits.append(int(modules[row, c]))
        upward = not upward
        col -= 2
    return bits


def bits_to_codewords(bits):
    """Regroupe les bits par 8. Les 7 derniers bits de la version 2 sont du remplissage."""
    return [
        int("".join(map(str, bits[8 * k : 8 * k + 8])), 2) for k in range(N_CODEWORDS)
    ]


# --- 4. contenu du message -----------------------------------------------------------------


def parse_byte_mode(data_codewords):
    """Extrait le message : 4 bits de mode, 8 bits de longueur, puis un octet par caractère."""
    bits = "".join(f"{b:08b}" for b in data_codewords)
    mode = int(bits[:4], 2)
    if mode != BYTE_MODE:
        raise ValueError(f"mode {mode:04b} non géré (seul le mode octets 0100 l'est)")
    length = int(bits[4:12], 2)
    if 12 + 8 * length > len(bits):
        raise ValueError(f"longueur annoncée ({length}) incompatible avec la capacité")
    return bytes(int(bits[12 + 8 * k : 20 + 8 * k], 2) for k in range(length))


# --- tout enchaîner ------------------------------------------------------------------------


def decode_modules(modules):
    """Décode un tableau 25×25 de modules (1 = noir)."""
    modules = np.asarray(modules)
    if modules.shape != (SIZE, SIZE):
        raise ValueError(
            f"tableau {modules.shape} : seule la version 2 (25×25) est gérée"
        )
    check_finder_patterns(modules)
    ec_level, mask = read_format(modules)
    codewords = bits_to_codewords(read_data_bits(unmask(modules, mask)))
    corrected, positions = rs_decode(codewords, EC_CODEWORDS[ec_level])
    data = parse_byte_mode(corrected[: N_CODEWORDS - EC_CODEWORDS[ec_level]])
    return DecodedQR(data, ec_level, mask, tuple(positions))


def decode_image(image):
    """Décode une image (chemin ou image PIL) contenant un QR code version 2, mode octets."""
    return decode_modules(image_to_modules(image))
