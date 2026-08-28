import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_de_donnees import BaseModele


class StatutTache(str, enum.Enum):
    A_FAIRE = "a_faire"
    EN_COURS = "en_cours"
    TERMINEE = "terminee"


class RoleProjet(str, enum.Enum):
    ADMINISTRATEUR = "administrateur"
    PARTICIPANT = "participant"


class StatutProjet(str, enum.Enum):
    PLANIFIE = "planifie"
    EN_COURS = "en_cours"
    EN_PAUSE = "en_pause"
    TERMINE = "termine"


class Utilisateur(BaseModele):
    __tablename__ = "utilisateurs"

    id: Mapped[int] = mapped_column(primary_key=True)
    courriel: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    nom_affiche: Mapped[str] = mapped_column(String(100))
    empreinte_mot_de_passe: Mapped[str] = mapped_column(String(255))
    photo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ParticipantProjet(BaseModele):
    __tablename__ = "participants_projet"
    __table_args__ = (UniqueConstraint("projet_id", "utilisateur_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    projet_id: Mapped[int] = mapped_column(ForeignKey("projets.id", ondelete="CASCADE"))
    utilisateur_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id", ondelete="CASCADE"))
    role: Mapped[RoleProjet] = mapped_column(Enum(RoleProjet), default=RoleProjet.PARTICIPANT)
    utilisateur: Mapped[Utilisateur] = relationship()


class Projet(BaseModele):
    __tablename__ = "projets"

    id: Mapped[int] = mapped_column(primary_key=True)
    titre: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(Text, default="")
    statut: Mapped[StatutProjet] = mapped_column(Enum(StatutProjet), default=StatutProjet.EN_COURS)
    proprietaire_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id", ondelete="RESTRICT"), index=True)
    cree_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    proprietaire: Mapped[Utilisateur] = relationship()
    participants: Mapped[list[ParticipantProjet]] = relationship(cascade="all, delete-orphan")
    taches: Mapped[list["Tache"]] = relationship(cascade="all, delete-orphan")


class Tache(BaseModele):
    __tablename__ = "taches"

    id: Mapped[int] = mapped_column(primary_key=True)
    titre: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(Text, default="")
    statut: Mapped[StatutTache] = mapped_column(Enum(StatutTache), default=StatutTache.A_FAIRE)
    projet_id: Mapped[int] = mapped_column(ForeignKey("projets.id", ondelete="CASCADE"), index=True)
    responsable_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id", ondelete="SET NULL"), nullable=True)
    createur_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id", ondelete="SET NULL"), nullable=True, index=True)
    responsable: Mapped[Utilisateur | None] = relationship(foreign_keys=[responsable_id])
    createur: Mapped[Utilisateur | None] = relationship(foreign_keys=[createur_id])
