# basic_qrcode

Décodage d'un QR code **de l'image au texte**, écrit pour comprendre : lecture des modules, information de format, masque, parcours des octets, puis correction d'erreur Reed-Solomon, le tout en Python simple (NumPy et Pillow, sans bibliothèque de QR code ni de Reed-Solomon).

```python
from basic_qrcode import decode_image

resultat = decode_image("images/basic_qrcode.png")
resultat.text  # 'Mon beau QR code !'
resultat.ec_level  # 'L'
resultat.mask  # 2
resultat.corrected  # () : indices des octets corrigés par Reed-Solomon
```

## Ce que fait (et ne fait pas) le projet

Cas traité : **version 2 uniquement** (25×25 modules), **mode octets**, les quatre niveaux de correction (L, M, Q, H) et les huit masques, à partir d'une image nette, droite et non déformée.

Volontairement non traités : les autres versions et modes (numérique, alphanumérique, kanji), la correction des 10 bits de l'information de format (code BCH ; un seul des deux exemplaires est lu), les effacements Reed-Solomon, les images en perspective ou pivotées. Pour lire de vrais QR codes, utilisez plutôt ZXing, OpenCV ou pyzbar.

L'intérêt est pédagogique :

- les notebooks détaillent chaque étape, de l'image jusqu'au texte ;
- l'étude des dégradations (`erreurs_et_limites.ipynb`) montre concrètement la limite de correction : au niveau M, 8 octets erronés sont corrigés, pas un de plus, et un carré de seulement 6×6 modules suffit à abîmer 8 octets.

## Contenu du dépôt

| Chemin | Rôle |
|---|---|
| `src/basic_qrcode/gf256.py` | arithmétique du corps GF(2⁸) et des polynômes |
| `src/basic_qrcode/reed_solomon.py` | octets de parité, syndromes, Berlekamp-Massey, Chien, Forney |
| `src/basic_qrcode/qr.py` | de l'image aux octets, puis au message |
| `notebooks/decodage.ipynb` | le décodage expliqué pas à pas |
| `notebooks/erreurs_et_limites.ipynb` | QR codes abîmés et limites de la correction |
| `tests/` | tests (aller-retour avec deux générateurs de QR codes, Reed-Solomon, dégradations) |
| `images/` | images produites par les notebooks |

## Installation et tests

Avec [uv](https://docs.astral.sh/uv/) :

```bash
uv sync
uv run pytest
```

Sans uv : `pip install -e .` puis `pip install pytest segno "qrcode[pil]" reedsolo`.

Les tests fabriquent des QR codes avec [segno](https://segno.readthedocs.io/) et [qrcode](https://github.com/lincolnloop/python-qrcode) (tous niveaux, tous masques, plusieurs tailles de module), vérifient que le décodage redonne le message, comparent les octets de parité et la correction à [reedsolo](https://github.com/tomerfiliba-org/reedsolomon), et contrôlent le comportement en cas de dégradation. Ces bibliothèques ne servent que pour les tests et les notebooks : elles ne sont pas redistribuées ici.

Les notebooks s'ouvrent depuis le dossier `notebooks/` (les chemins vers `images/` sont relatifs). Le second compare aussi avec OpenCV si celui-ci est installé.

## Crédits et licences

**Ce projet s'inspire fortement de** [« Reed–Solomon codes for coders »](https://en.wikiversity.org/wiki/Reed%E2%80%93Solomon_codes_for_coders), page de Wikiversity écrite par ses contributeurs (liste des auteurs : [historique de la page](https://en.wikiversity.org/w/index.php?title=Reed%E2%80%93Solomon_codes_for_coders&action=history)), publiée sous licence Creative Commons Attribution-ShareAlike (CC BY-SA ; la version exacte est indiquée en bas de la page).

- *Ce qui en vient :* le fil de l'exposé (structure d'un QR code, information de format, masque, lecture des octets, corps fini, polynôme générateur, syndromes, localisateur d'erreurs de Berlekamp-Massey, formule de Forney) et les idées qui s'y trouvent.
- *Ce qui a été modifié ou ajouté :* traduction et réécriture en français ; cas de la version 2 au lieu de la version 1 ; lecture à partir d'une **image** (binarisation, cadrage, découpage en modules) ; décodeur Reed-Solomon et codage de la parité réécrits à partir des formules classiques ; tests ; étude des dégradations. Le code du dossier `src/` n'est pas une copie du code de la page.

Autres sources :

- Tableaux des versions et des capacités : [qrcode.com](https://www.qrcode.com/en/about/version.html) (DENSO WAVE) ; la norme est ISO/IEC 18004.
- Algorithme de Berlekamp-Massey : [cp-blog](https://mzhang2021.github.io/cp-blog/berlekamp-massey/) et [ramrsbd](https://github.com/littlefs-project/ramrsbd) (littlefs), qui m'ont aidé à le comprendre.
- QR Code est une marque déposée de DENSO WAVE INCORPORATED.

Le code de ce dépôt est distribué sous licence MIT (fichier `LICENSE`).
