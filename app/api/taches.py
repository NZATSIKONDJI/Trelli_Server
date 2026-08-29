from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependances import obtenir_bdd, obtenir_participation, obtenir_utilisateur_courant, verifier_jeton_csrf
from app.models import ParticipantProjet, Tache, Utilisateur
from app.schemas.modeles import StatutEntree, TacheEntree, TacheSortie


routeur = APIRouter(prefix="/projets/{projet_id}/taches", tags=["taches"], dependencies=[Depends(verifier_jeton_csrf)])

"""Ici on vérifie que le responsable choisi participe au projet. Aucun contrôle n’est
nécessaire si la tâche n’a pas de responsable ; sinon, une erreur HTTP 422
est renvoyée lorsque l’utilisateur choisi ne participe pas au projet."""

def verifier_responsable(projet_id: int, responsable_id: int | None, bdd: Session) -> None:
    if responsable_id is None:
        return
    participation = bdd.scalar(select(ParticipantProjet).where(ParticipantProjet.projet_id == projet_id, ParticipantProjet.utilisateur_id == responsable_id))
    if not participation:
        raise HTTPException(status_code=422, detail="Le responsable doit participer au projet")

"""Ici on récupère une tâche appartenant au projet indiqué. Renvoie une erreur HTTP 404
si la tâche n’existe pas ou si elle appartient à un autre projet."""

def obtenir_tache(tache_id: int, projet_id: int, bdd: Session) -> Tache:
    tache = bdd.scalar(select(Tache).where(Tache.id == tache_id, Tache.projet_id == projet_id))
    if not tache:
        raise HTTPException(status_code=404, detail="Tâche introuvable")
    return tache

"""Ici on vérifie que l’utilisateur peut agir sur la tâche : il doit être administrateur
du projet, responsable de la tâche ou créateur de celle-ci. Sinon, une erreur
HTTP 403 est renvoyée."""

def exiger_droit_sur_tache(projet_id: int, tache: Tache, utilisateur: Utilisateur, bdd: Session) -> None:
    participation = obtenir_participation(projet_id, utilisateur, bdd)
    autorise = (
        participation.role.value == "administrateur"
        or tache.responsable_id == utilisateur.id
        or tache.createur_id == utilisateur.id
    )
    if not autorise:
        raise HTTPException(
            status_code=403,
            detail="Cette action est réservée à un administrateur, au responsable ou au créateur de la tâche",
        )

"""Ici on renvoie toutes les tâches du projet, de la plus récente à la plus ancienne,
après avoir vérifié que l’utilisateur connecté participe au projet."""

@routeur.get("", response_model=list[TacheSortie])
def lister_taches(projet_id: int, utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant), bdd: Session = Depends(obtenir_bdd)):
    obtenir_participation(projet_id, utilisateur, bdd)
    return bdd.scalars(select(Tache).where(Tache.projet_id == projet_id).order_by(Tache.id.desc())).all()

"""Ici on crée une tâche dans le projet après avoir vérifié que l’utilisateur y participe
et que le responsable choisi en est membre, puis enregistre l’utilisateurconnecté comme créateur de la tâche."""

@routeur.post("", response_model=TacheSortie, status_code=status.HTTP_201_CREATED)
def creer_tache(projet_id: int, donnees: TacheEntree, utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant), bdd: Session = Depends(obtenir_bdd)):
    obtenir_participation(projet_id, utilisateur, bdd)
    verifier_responsable(projet_id, donnees.responsable_id, bdd)
    tache = Tache(projet_id=projet_id, createur_id=utilisateur.id, **donnees.model_dump())
    bdd.add(tache); bdd.commit(); bdd.refresh(tache)
    return tache

"""Ici on modifie une tâche après avoir vérifié les droits de l’utilisateur et que le
responsable choisi participe au projet, puis renvoie la tâche actualisée."""

@routeur.put("/{tache_id}", response_model=TacheSortie)
def modifier_tache(projet_id: int, tache_id: int, donnees: TacheEntree, utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant), bdd: Session = Depends(obtenir_bdd)):
    tache = obtenir_tache(tache_id, projet_id, bdd)
    exiger_droit_sur_tache(projet_id, tache, utilisateur, bdd)
    verifier_responsable(projet_id, donnees.responsable_id, bdd)
    for champ, valeur in donnees.model_dump().items():
        setattr(tache, champ, valeur)
    bdd.commit(); bdd.refresh(tache)
    return tache

"""Ici on modifie uniquement le statut d’une tâche après avoir vérifié que l’utilisateur
connecté possède les droits nécessaires, puis renvoie la tâche actualisée."""

@routeur.patch("/{tache_id}/statut", response_model=TacheSortie)
def modifier_statut(projet_id: int, tache_id: int, donnees: StatutEntree, utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant), bdd: Session = Depends(obtenir_bdd)):
    tache = obtenir_tache(tache_id, projet_id, bdd)
    exiger_droit_sur_tache(projet_id, tache, utilisateur, bdd)
    tache.statut = donnees.statut; bdd.commit(); bdd.refresh(tache)
    return tache

"""Ici on supprime définitivement une tâche après avoir vérifié que l’utilisateur
connecté possède les droits nécessaires, puis renvoie une réponse HTTP 204."""

@routeur.delete("/{tache_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_tache(projet_id: int, tache_id: int, utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant), bdd: Session = Depends(obtenir_bdd)):
    tache = obtenir_tache(tache_id, projet_id, bdd)
    exiger_droit_sur_tache(projet_id, tache, utilisateur, bdd)
    bdd.delete(tache); bdd.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

