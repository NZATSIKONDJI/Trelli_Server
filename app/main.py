from contextlib import asynccontextmanager
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import OperationalError

from app.api import authentification, projets, taches
from app.core.configuration import configuration
from app.core.base_de_donnees import BaseModele, FabriqueSession, moteur
from app.core.securite import hacher_mot_de_passe
from app.models import Utilisateur

"""Ici on crée les comptes de démonstration au démarrage s’ils n’existent pas encore,
en enregistrant une empreinte sécurisée de leur mot de passe. Si un compte
existe déjà, ajoute seulement sa photo lorsqu’elle est absente."""

def creer_utilisateurs_demonstration() -> None:
    with FabriqueSession() as bdd:
        comptes = (
            ("trellikarl@mentor.com", "Karl Chef", "images/membres/compte-demo.png"),
            ("trelliparticipant@mentor.com", "Participant", "images/membres/participant-demo.png"),
        )
        for courriel, nom, photo in comptes:
            utilisateur = bdd.scalar(select(Utilisateur).where(Utilisateur.courriel == courriel))
            if utilisateur:
                utilisateur.photo = utilisateur.photo or photo
            else:
                bdd.add(Utilisateur(
                    courriel=courriel, nom_affiche=nom, photo=photo,
                    empreinte_mot_de_passe=hacher_mot_de_passe(configuration.mot_de_passe_demo),
                ))
        bdd.commit()

"""Ici on met à jour la structure d’une base MySQL existante sans supprimer ses données.
Ajoute les colonnes photo, statut et createur_id lorsqu’elles sont absentes,
ainsi que l’index et la clé étrangère associés au créateur d’une tâche."""
  
def mettre_a_jour_structure() -> None:
   
    if moteur.dialect.name != "mysql":
        return
    inspecteur = inspect(moteur)
    colonnes_utilisateurs = {colonne["name"] for colonne in inspecteur.get_columns("utilisateurs")}
    colonnes_projets = {colonne["name"] for colonne in inspecteur.get_columns("projets")}
    colonnes_taches = {colonne["name"] for colonne in inspecteur.get_columns("taches")}
    with moteur.begin() as connexion:
        if "photo" not in colonnes_utilisateurs:
            connexion.execute(text("ALTER TABLE utilisateurs ADD COLUMN photo VARCHAR(255) NULL"))
        if "statut" not in colonnes_projets:
            connexion.execute(text(
                "ALTER TABLE projets ADD COLUMN statut "
                "ENUM('PLANIFIE','EN_COURS','EN_PAUSE','TERMINE') NOT NULL DEFAULT 'EN_COURS'"
            ))
        if "createur_id" not in colonnes_taches:
            connexion.execute(text("ALTER TABLE taches ADD COLUMN createur_id INT NULL"))
            connexion.execute(text("CREATE INDEX ix_taches_createur_id ON taches (createur_id)"))
            connexion.execute(text(
                "ALTER TABLE taches ADD CONSTRAINT fk_taches_createur "
                "FOREIGN KEY (createur_id) REFERENCES utilisateurs(id) ON DELETE SET NULL"
            ))


"""Ici on attend que la base de données soit accessible en effectuant jusqu’à 30
tentatives espacées de deux secondes. Si toutes les connexions échouent,
la dernière erreur rencontrée est renvoyée."""

def attendre_base_de_donnees(tentatives: int = 30, delai_secondes: int = 2) -> None:
    derniere_erreur: OperationalError | None = None
    for _ in range(tentatives):
        try:
            with moteur.connect():
                return
        except OperationalError as erreur:
            derniere_erreur = erreur
            time.sleep(delai_secondes)
    if derniere_erreur:
        raise derniere_erreur

"""Ici on initialise l’application au démarrage : attend MySQL, crée les tables
manquantes, met à jour leur structure et crée les comptes de démonstration.
Configure ensuite FastAPI et autorise uniquement le client déclaré à
communiquer avec l’API grâce au middleware CORS.
"""

@asynccontextmanager
async def cycle_de_vie(_: FastAPI):
    attendre_base_de_donnees()
    BaseModele.metadata.create_all(bind=moteur)
    mettre_a_jour_structure()
    creer_utilisateurs_demonstration()
    yield


application = FastAPI(title="API Trelli", version="1.0.0", lifespan=cycle_de_vie, docs_url="/docs" if configuration.environnement != "production" else None)
application.add_middleware(
    CORSMiddleware,
    allow_origins=[configuration.origine_client],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)

"""Ici on ajoute des en-têtes de sécurité à chaque réponse HTTP afin d’empêcher
l’interprétation incorrecte des fichiers, l’intégration dans une iframe,
la transmission du référent, l’accès aux fonctions sensibles du navigateur
et la mise en cache des données."""

@application.middleware("http")
async def ajouter_entetes_securite(requete: Request, appeler_suivant):
    reponse = await appeler_suivant(requete)
    reponse.headers["X-Content-Type-Options"] = "nosniff"
    reponse.headers["X-Frame-Options"] = "DENY"
    reponse.headers["Referrer-Policy"] = "no-referrer"
    reponse.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    reponse.headers["Cache-Control"] = "no-store"
    return reponse

"""Ici on intercepte les erreurs imprévues afin de renvoyer une réponse HTTP 500
générique, sans révéler au client les détails techniques du serveur."""

@application.exception_handler(Exception)
async def erreur_non_geree(_: Request, __: Exception):
    return JSONResponse(status_code=500, content={"detail": "Erreur interne du serveur"})

"""Ici on indique que l’API fonctionne correctement en renvoyant l’état « ok ».
Cette route est notamment utilisée par Docker pour vérifier la santé du serveur."""

@application.get("/api/sante", tags=["sante"])
def sante():
    return {"etat": "ok"}


application.include_router(authentification.routeur, prefix="/api")
application.include_router(projets.routeur, prefix="/api")
application.include_router(taches.routeur, prefix="/api")
