import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.configuration import configuration


gestionnaire_mots_de_passe = PasswordHash.recommended()
ALGORITHME = "HS256"


def hacher_mot_de_passe(mot_de_passe: str) -> str:
    return gestionnaire_mots_de_passe.hash(mot_de_passe)


def verifier_mot_de_passe(mot_de_passe: str, empreinte: str) -> bool:
    return gestionnaire_mots_de_passe.verify(mot_de_passe, empreinte)


def creer_jeton_acces(utilisateur_id: int) -> str:
    maintenant = datetime.now(timezone.utc)
    contenu = {
        "sub": str(utilisateur_id), "iat": maintenant,
        "exp": maintenant + timedelta(minutes=configuration.duree_jeton_minutes),
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(contenu, configuration.secret_jwt, algorithm=ALGORITHME)


def decoder_jeton_acces(jeton: str) -> int:
    contenu = jwt.decode(jeton, configuration.secret_jwt, algorithms=[ALGORITHME])
    return int(contenu["sub"])


def creer_jeton_csrf() -> str:
    return secrets.token_urlsafe(32)


def comparer_temps_constant(gauche: str, droite: str) -> bool:
    return secrets.compare_digest(hashlib.sha256(gauche.encode()).digest(), hashlib.sha256(droite.encode()).digest())

