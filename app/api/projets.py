from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependances import exiger_administrateur, exiger_proprietaire, obtenir_bdd, obtenir_participation, obtenir_utilisateur_courant, verifier_jeton_csrf
from app.models import ParticipantProjet, Projet, RoleProjet, Utilisateur
from app.schemas.modeles import ParticipantEntree, ParticipantSortie, ProjetEntree, ProjetSortie, RoleEntree


routeur = APIRouter(prefix="/projets", tags=["projets"], dependencies=[Depends(verifier_jeton_csrf)])

"""Ici on récupère un projet avec ses participants, les informations de leurs
utilisateurs et ses tâches afin de limiter le nombre de requêtes SQL."""

def charger_projet(projet_id: int, bdd: Session) -> Projet:
    return bdd.scalar(select(Projet).where(Projet.id == projet_id).options(
        selectinload(Projet.participants).selectinload(ParticipantProjet.utilisateur),
        selectinload(Projet.taches),
    ))

"""Ici on convertit un projet SQLAlchemy en modèle de sortie pour l’API, en ajoutant
les participants, les tâches et le rôle de l’utilisateur connecté."""

def convertir_projet(projet: Projet, utilisateur_id: int) -> ProjetSortie:
    participation_courante = next(p for p in projet.participants if p.utilisateur_id == utilisateur_id)
    participants = [ParticipantSortie(
        id=p.utilisateur.id, courriel=p.utilisateur.courriel,
        nom_affiche=p.utilisateur.nom_affiche, photo=p.utilisateur.photo, role=p.role,
    ) for p in projet.participants]
    return ProjetSortie(
        id=projet.id, titre=projet.titre, description=projet.description, statut=projet.statut,
        proprietaire_id=projet.proprietaire_id, role_courant=participation_courante.role,
        participants=participants, taches=projet.taches,
    )

""" Ici on renvoie tous les projets auxquels l’utilisateur connecté participe, avec
leurs participants et leurs tâches, classés du plus récent au plus ancien."""

@routeur.get("", response_model=list[ProjetSortie])
def lister_projets(utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant), bdd: Session = Depends(obtenir_bdd)):
    ids = select(ParticipantProjet.projet_id).where(ParticipantProjet.utilisateur_id == utilisateur.id)
    projets = bdd.scalars(select(Projet).where(Projet.id.in_(ids)).options(
        selectinload(Projet.participants).selectinload(ParticipantProjet.utilisateur),
        selectinload(Projet.taches),
    ).order_by(Projet.id.desc())).all()
    return [convertir_projet(projet, utilisateur.id) for projet in projets]

""" Ici on crée un projet, désigne l’utilisateur connecté comme propriétaire et
administrateur, puis renvoie le nouveau projet avec ses informations."""

@routeur.post("", response_model=ProjetSortie, status_code=status.HTTP_201_CREATED)
def creer_projet(donnees: ProjetEntree, utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant), bdd: Session = Depends(obtenir_bdd)):
    projet = Projet(titre=donnees.titre.strip(), description=donnees.description.strip(), statut=donnees.statut, proprietaire_id=utilisateur.id)
    bdd.add(projet); bdd.flush()
    bdd.add(ParticipantProjet(projet_id=projet.id, utilisateur_id=utilisateur.id, role=RoleProjet.ADMINISTRATEUR))
    bdd.commit()
    return convertir_projet(charger_projet(projet.id, bdd), utilisateur.id)

"""Ici on modifie le titre, la description et le statut d’un projet si l’utilisateur
connecté possède le rôle administrateur, puis renvoie le projet actualisé."""

@routeur.put("/{projet_id}", response_model=ProjetSortie)
def modifier_projet(projet_id: int, donnees: ProjetEntree, utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant), bdd: Session = Depends(obtenir_bdd)):
    exiger_administrateur(projet_id, utilisateur, bdd)
    projet = bdd.get(Projet, projet_id)
    projet.titre, projet.description, projet.statut = donnees.titre.strip(), donnees.description.strip(), donnees.statut
    bdd.commit()
    return convertir_projet(charger_projet(projet_id, bdd), utilisateur.id)

"""Ici on supprime définitivement un projet si l’utilisateur connecté en est le
propriétaire, puis renvoie une réponse HTTP 204 sans contenu."""

@routeur.delete("/{projet_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_projet(projet_id: int, utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant), bdd: Session = Depends(obtenir_bdd)):
    projet = exiger_proprietaire(projet_id, utilisateur, bdd)
    bdd.delete(projet); bdd.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

"""Ici on ajoute un utilisateur existant comme participant d’un projet si l’utilisateur
connecté est administrateur, puis renvoie les informations du participant."""

@routeur.post("/{projet_id}/participants", response_model=ParticipantSortie, status_code=status.HTTP_201_CREATED)
def ajouter_participant(projet_id: int, donnees: ParticipantEntree, utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant), bdd: Session = Depends(obtenir_bdd)):
    exiger_administrateur(projet_id, utilisateur, bdd)
    personne = bdd.scalar(select(Utilisateur).where(Utilisateur.courriel == donnees.courriel.lower()))
    if not personne:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    participation = bdd.scalar(select(ParticipantProjet).where(ParticipantProjet.projet_id == projet_id, ParticipantProjet.utilisateur_id == personne.id))
    if not participation:
        participation = ParticipantProjet(projet_id=projet_id, utilisateur_id=personne.id, role=RoleProjet.PARTICIPANT)
        bdd.add(participation); bdd.commit()
    return ParticipantSortie(id=personne.id, courriel=personne.courriel, nom_affiche=personne.nom_affiche, photo=personne.photo, role=participation.role)

"""Ici on modifie le rôle d’un participant si l’utilisateur connecté est le propriétaire
du projet, tout en empêchant le propriétaire de perdre son rôle administrateur."""

@routeur.put("/{projet_id}/participants/{participant_id}/role", response_model=ParticipantSortie)
def modifier_role(projet_id: int, participant_id: int, donnees: RoleEntree, utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant), bdd: Session = Depends(obtenir_bdd)):
    projet = exiger_proprietaire(projet_id, utilisateur, bdd)
    if participant_id == projet.proprietaire_id and donnees.role != RoleProjet.ADMINISTRATEUR:
        raise HTTPException(status_code=422, detail="Le propriétaire doit rester administrateur")
    participation = bdd.scalar(select(ParticipantProjet).where(ParticipantProjet.projet_id == projet_id, ParticipantProjet.utilisateur_id == participant_id))
    if not participation:
        raise HTTPException(status_code=404, detail="Participant introuvable")
    participation.role = donnees.role; bdd.commit()
    personne = participation.utilisateur
    return ParticipantSortie(id=personne.id, courriel=personne.courriel, nom_affiche=personne.nom_affiche, photo=personne.photo, role=participation.role)
