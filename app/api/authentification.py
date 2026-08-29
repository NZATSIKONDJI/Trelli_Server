from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependances import obtenir_bdd, obtenir_utilisateur_courant, verifier_jeton_csrf
from app.core.configuration import configuration
from app.core.securite import creer_jeton_acces, creer_jeton_csrf, verifier_mot_de_passe
from app.models import Utilisateur
from app.schemas.modeles import ConnexionEntree, UtilisateurSortie


routeur = APIRouter(prefix="/authentification", tags=["authentification"])


""" Ici on vérifie le courriel et le mot de passe de l'utilisateur ,si les identifiants sont valides, crée un jeton d'accès JWT et
un jeton CSRF, les enregistre dans des cookies sécurisés, puis renvoie les informations publiques de l'utilisateur.
Une erreur HTTP 401 est renvoyée si les identifiants sont incorrects."""

@routeur.post("/connexion", response_model=UtilisateurSortie)
def connecter(donnees: ConnexionEntree, reponse: Response, bdd: Session = Depends(obtenir_bdd)):
    utilisateur = bdd.scalar(select(Utilisateur).where(Utilisateur.courriel == donnees.courriel.lower()))
    if not utilisateur or not verifier_mot_de_passe(donnees.mot_de_passe, utilisateur.empreinte_mot_de_passe):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants incorrects")
    jeton = creer_jeton_acces(utilisateur.id)
    jeton_csrf = creer_jeton_csrf()
    duree = configuration.duree_jeton_minutes * 60
    reponse.set_cookie("access_token", jeton, httponly=True, secure=configuration.cookie_securise, samesite="strict", max_age=duree, path="/")
    reponse.set_cookie("csrf_token", jeton_csrf, httponly=False, secure=configuration.cookie_securise, samesite="strict", max_age=duree, path="/")
    return utilisateur

""" Ici on renvoie les informations de l’utilisateur actuellement connecté.
Lève une erreur HTTP 401 si la session est absente ou invalide."""

@routeur.get("/moi", response_model=UtilisateurSortie)
def moi(utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant)):
    return utilisateur

"""Et enfin on supprime les cookies de session pour déconnecter l’utilisateur."""

@routeur.post("/deconnexion", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verifier_jeton_csrf)])
def deconnecter(reponse: Response):
    reponse.delete_cookie("access_token", path="/")
    reponse.delete_cookie("csrf_token", path="/")
