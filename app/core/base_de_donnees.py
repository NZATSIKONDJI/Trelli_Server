from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.configuration import configuration


class BaseModele(DeclarativeBase):
    pass


arguments_connexion = {"check_same_thread": False} if configuration.url_bdd.startswith("sqlite") else {}
moteur = create_engine(configuration.url_bdd, pool_pre_ping=True, connect_args=arguments_connexion)
FabriqueSession = sessionmaker(bind=moteur, autoflush=False, expire_on_commit=False)

