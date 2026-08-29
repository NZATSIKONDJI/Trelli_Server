from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import RoleProjet, StatutProjet, StatutTache


class ConnexionEntree(BaseModel):
    courriel: EmailStr
    mot_de_passe: str = Field(min_length=10, max_length=128)


class UtilisateurSortie(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    courriel: EmailStr
    nom_affiche: str
    photo: str | None = None


class ProjetEntree(BaseModel):
    titre: str = Field(min_length=1, max_length=150)
    description: str = Field(default="", max_length=5000)
    statut: StatutProjet = StatutProjet.EN_COURS


class ParticipantEntree(BaseModel):
    courriel: EmailStr


class RoleEntree(BaseModel):
    role: RoleProjet


class ParticipantSortie(UtilisateurSortie):
    role: RoleProjet


class TacheEntree(BaseModel):
    titre: str = Field(min_length=1, max_length=150)
    description: str = Field(default="", max_length=5000)
    statut: StatutTache = StatutTache.A_FAIRE
    responsable_id: int | None = None


class StatutEntree(BaseModel):
    statut: StatutTache


class TacheSortie(TacheEntree):
    model_config = ConfigDict(from_attributes=True)
    id: int
    projet_id: int
    createur_id: int | None = None
    responsable: UtilisateurSortie | None = None
    createur: UtilisateurSortie | None = None


class ProjetSortie(ProjetEntree):
    id: int
    proprietaire_id: int
    role_courant: RoleProjet
    participants: list[ParticipantSortie] = []
    taches: list[TacheSortie] = []
