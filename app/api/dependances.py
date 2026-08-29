from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from jwt import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.base_de_donnees import FabriqueSession
from app.core.securite import comparer_temps_constant, decoder_jeton_acces
from app.models import ParticipantProjet, Projet, RoleProjet, Utilisateur


def obtenir_bdd():
    bdd = FabriqueSession()
    try:
        yield bdd
    finally:
        bdd.close()

""" Ici FastAPI s'occupe  d'obtenir l'utilisateur actuellement connecté en vérifiant le jeton d'accès dans les cookies.
Si le jeton est absent ou invalide, elle lève une exception HTTP 401 (Non autorisé) """

def obtenir_utilisateur_courant(
    access_token: str | None = Cookie(default=None), bdd: Session = Depends(obtenir_bdd)
) -> Utilisateur:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentification requise")
    try:
        utilisateur_id = decoder_jeton_acces(access_token)
    except (InvalidTokenError, ValueError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide") from None
    utilisateur = bdd.get(Utilisateur, utilisateur_id)
    if not utilisateur:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide")
    return utilisateur

""" Ici on vérifie le jeton CSRF pour les requêtes non sécurisées (POST, PUT, DELETE).
Si le jeton CSRF est absent ou invalide, elle lève une exception HTTP"""

def verifier_jeton_csrf(
    requete: Request,
    jeton_cookie: str | None = Cookie(default=None, alias="csrf_token"),
    jeton_entete: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> None:
    if requete.method in {"GET", "HEAD", "OPTIONS"}:
        return
    if not jeton_cookie or not jeton_entete or not comparer_temps_constant(jeton_cookie, jeton_entete):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Jeton CSRF invalide")

""" Ici on verifie si l'utilisateur connecté appartient au projet si oui on revoie son role et sa participation 
,si non elle lève une exception HTTP 404"""

def obtenir_participation(projet_id: int, utilisateur: Utilisateur, bdd: Session) -> ParticipantProjet:
    participation = bdd.scalar(select(ParticipantProjet).where(
        ParticipantProjet.projet_id == projet_id,
        ParticipantProjet.utilisateur_id == utilisateur.id,
    ))
    if not participation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projet introuvable")
    return participation

""" Ici on vérifie d'abord la participation et renvoie les informations du  projet."""


def obtenir_projet(projet_id: int, utilisateur: Utilisateur, bdd: Session) -> Projet:
    obtenir_participation(projet_id, utilisateur, bdd)
    projet = bdd.get(Projet, projet_id)
    if not projet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projet introuvable")
    return projet

""" Ici on Vérifie que l'utilisateur connecté participe au projet et possède le rôle administrateur."""

def exiger_administrateur(projet_id: int, utilisateur: Utilisateur, bdd: Session) -> ParticipantProjet:
    participation = obtenir_participation(projet_id, utilisateur, bdd)
    if participation.role != RoleProjet.ADMINISTRATEUR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Droits administrateur requis")
    return participation

""" Ici on vérifie si l'utilisateur connecté est le propriétaire du projet. """

def exiger_proprietaire(projet_id: int, utilisateur: Utilisateur, bdd: Session) -> Projet:
    projet = bdd.scalar(select(Projet).where(Projet.id == projet_id, Projet.proprietaire_id == utilisateur.id))
    if not projet:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Droits du propriétaire requis")
    return projet
