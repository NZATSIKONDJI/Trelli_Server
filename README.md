# Trelli — Serveur API

API REST du gestionnaire de projets Trelli. Ce dépôt contient le serveur Python, les règles métier, les autorisations, les modèles de base de données et les tests automatiques.

Le client web Trelli est un dépôt séparé et communique avec cette API par les routes `/api`.

## Technologies

- Python 3.12 ;
- FastAPI 0.116 ;
- Uvicorn ;
- SQLAlchemy 2 comme ORM ;
- Pydantic pour la validation ;
- MySQL 8.4 avec PyMySQL ;
- Argon2id pour les empreintes de mots de passe ;
- JWT pour les sessions ;
- Pytest et SQLite pour les tests isolés ;
- Docker.

## Fonctionnalités

- authentification et déconnexion sécurisées ;
- récupération de l’utilisateur connecté ;
- gestion des projets et de leurs statuts ;
- ajout de participants ;
- gestion des rôles par le propriétaire ;
- gestion des tâches, responsables, créateurs et statuts ;
- contrôle des autorisations dans chaque route ;
- création initiale des tables et petites migrations sans perte ;
- création automatique de deux comptes de démonstration.

## Arborescence

```text
server/
├── app/
│   ├── api/
│   │   ├── authentification.py # connexion, session et déconnexion
│   │   ├── dependances.py      # BDD, utilisateur, CSRF et permissions
│   │   ├── projets.py          # projets, participants et rôles
│   │   └── taches.py           # tâches et autorisations
│   ├── core/
│   │   ├── base_de_donnees.py  # moteur et sessions SQLAlchemy
│   │   ├── configuration.py    # variables d’environnement
│   │   └── securite.py         # mots de passe, JWT et CSRF
│   ├── models/
│   │   └── entites.py          # architecture des tables
│   ├── schemas/
│   │   └── modeles.py          # entrées et sorties Pydantic
│   ├── __init__.py
│   └── main.py                 # application et cycle de démarrage
├── tests/
│   ├── conftest.py
│   └── test_api.py
├── Dockerfile
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

Les fichiers `__init__.py` déclarent les packages Python. Les dossiers `__pycache__` sont générés automatiquement et ne doivent pas être versionnés.

## Règles métier et rôles

### Propriétaire

- devient administrateur lors de la création du projet ;
- peut modifier et supprimer son projet ;
- peut ajouter des participants ;
- est le seul à pouvoir promouvoir ou rétrograder un membre ;
- ne peut jamais perdre son propre rôle administrateur.

### Administrateur délégué

- peut modifier le projet et ajouter des participants ;
- peut créer, modifier, supprimer, attribuer et changer le statut de toutes les tâches ;
- ne peut pas modifier les rôles ;
- ne peut donc ni retirer le rôle du propriétaire ni se rétrograder.

### Participant

- peut consulter toutes les tâches d’un projet auquel il participe ;
- peut créer une tâche ;
- peut modifier, supprimer ou changer le statut d’une tâche dont il est le créateur ;
- possède les mêmes droits sur une tâche qui lui est assignée ;
- ne peut pas agir sur une autre tâche.

Les permissions sont vérifiées côté serveur même si le client masque déjà les commandes interdites.

## Base de données

La base par défaut s’appelle `project_db` et contient quatre tables :

- `utilisateurs` ;
- `projets` ;
- `participants_projet` ;
- `taches`.

Relations :

```text
utilisateurs 1 ─── N projets              via proprietaire_id
utilisateurs 1 ─── N participants_projet  via utilisateur_id
projets      1 ─── N participants_projet  via projet_id
projets      1 ─── N taches               via projet_id
utilisateurs 1 ─── N taches               via responsable_id
utilisateurs 1 ─── N taches               via createur_id
```

Les suppressions appliquent les règles suivantes :

- supprimer un projet supprime ses participations et ses tâches (`CASCADE`) ;
- un propriétaire référencé ne peut pas être supprimé (`RESTRICT`) ;
- supprimer un responsable ou un créateur conserve la tâche et place la référence à `NULL` (`SET NULL`).

Au démarrage, `BaseModele.metadata.create_all()` crée les tables manquantes. `mettre_a_jour_structure()` ajoute sans supprimer les anciennes données les champs introduits après la première version, notamment `photo`, le statut du projet et `createur_id`.

## Configuration

Créer un fichier `.env` dans le dépôt serveur :

```dotenv
APP_ENV=development
DATABASE_URL=mysql+pymysql://project_user:MOT_DE_PASSE@mysql:3306/project_db
JWT_SECRET=remplacer-par-une-valeur-aleatoire-de-32-caracteres-minimum
CLIENT_ORIGIN=http://localhost:8080
COOKIE_SECURE=false
ACCESS_TOKEN_MINUTES=30
DEMO_PASSWORD=remplacer-par-un-mot-de-passe-de-demonstration
```

### Variables

| Variable | Utilité |
|---|---|
| `APP_ENV` | environnement `development` ou `production` |
| `DATABASE_URL` | connexion SQLAlchemy à MySQL |
| `JWT_SECRET` | signature des jetons, minimum 32 caractères |
| `CLIENT_ORIGIN` | origine autorisée par CORS |
| `COOKIE_SECURE` | impose HTTPS aux cookies lorsqu’il vaut `true` |
| `ACCESS_TOKEN_MINUTES` | durée d’une session |
| `DEMO_PASSWORD` | mot de passe initial des comptes de démonstration |

Ne jamais versionner `.env`. Le compte MySQL utilisé dans `DATABASE_URL` doit être limité à `project_db` ; l’application ne doit pas utiliser `root`.

## Comptes de démonstration

Le serveur crée automatiquement ces comptes s’ils n’existent pas :

```text
TrelliKarl@mentor.com
TrelliParticipant@mentor.com
```

Ils utilisent initialement la valeur de `DEMO_PASSWORD`. Seule une empreinte Argon2id est enregistrée. Changer la variable après la création du compte ne remplace pas automatiquement son mot de passe dans une base existante.

## Lancement avec Docker

### Construire l’image

Depuis le dépôt serveur :

```powershell
docker build -t trelli-server .
```

### Réseau partagé

Le serveur doit pouvoir joindre un conteneur MySQL. Avec les valeurs proposées, ce conteneur doit s’appeler `mysql` et appartenir au réseau `trelli` :

```powershell
docker network create trelli
```

Une fois MySQL démarré et sain sur ce réseau :

```powershell
docker run --name server --network trelli `
  --env-file .env `
  --read-only `
  --tmpfs /tmp `
  --security-opt no-new-privileges:true `
  trelli-server
```

Le conteneur porte volontairement le nom `server` afin que le Nginx du dépôt client puisse le trouver sur le réseau Docker.

Dans l’environnement complet actuel, le `docker-compose.yml` d’orchestration lance automatiquement le client, le serveur, MySQL et phpMyAdmin :

```powershell
docker compose up --build -d
```

## Lancement local pour le développement

Créer et activer un environnement virtuel :

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

Configurer `.env`, rendre MySQL accessible via `DATABASE_URL`, puis lancer :

```powershell
uvicorn app.main:application --reload --host 127.0.0.1 --port 8000
```

En environnement de développement, la documentation interactive est disponible sur <http://127.0.0.1:8000/docs>.

## Routes API

### Santé

- `GET /api/sante`

### Authentification

- `POST /api/authentification/connexion`
- `GET /api/authentification/moi`
- `POST /api/authentification/deconnexion`

### Projets et participants

- `GET /api/projets`
- `POST /api/projets`
- `PUT /api/projets/{projet_id}`
- `DELETE /api/projets/{projet_id}`
- `POST /api/projets/{projet_id}/participants`
- `PUT /api/projets/{projet_id}/participants/{participant_id}/role`

### Tâches

- `GET /api/projets/{projet_id}/taches`
- `POST /api/projets/{projet_id}/taches`
- `PUT /api/projets/{projet_id}/taches/{tache_id}`
- `PATCH /api/projets/{projet_id}/taches/{tache_id}/statut`
- `DELETE /api/projets/{projet_id}/taches/{tache_id}`

Codes courants : `200` succès, `201` création, `204` suppression, `401` non connecté, `403` interdit, `404` ressource inaccessible et `422` données invalides.

## Tests

Les tests utilisent SQLite dans un fichier isolé et n’écrivent pas dans MySQL :

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Ils vérifient l’authentification, le CSRF, les rôles et les autorisations d’un participant sur les tâches assignées ou créées.

## Sécurité

- mots de passe hachés avec Argon2id ;
- JWT signé avec expiration et identifiant unique ;
- JWT stocké dans un cookie `HttpOnly` ;
- cookies `SameSite=Strict` et `Secure` en production ;
- comparaison du jeton CSRF en temps constant ;
- validation Pydantic des entrées et sorties ;
- requêtes paramétrées SQLAlchemy contre les injections SQL ;
- réponses sans empreinte de mot de passe ;
- contrôle d’appartenance au projet avant les opérations ;
- messages `404` utilisés dans certains cas pour ne pas révéler un projet privé ;
- en-têtes de sécurité HTTP ;
- conteneur exécuté avec un utilisateur non privilégié ;
- système de fichiers en lecture seule dans l’orchestration Docker.

## Production

- utiliser une valeur `JWT_SECRET` longue et aléatoire ;
- définir `APP_ENV=production` et `COOKIE_SECURE=true` ;
- placer l’API derrière le Nginx du client et un reverse proxy HTTPS ;
- ne pas publier directement MySQL ou Uvicorn sur Internet ;
- désactiver phpMyAdmin ;
- sauvegarder et chiffrer le volume MySQL ;
- renouveler les secrets avant le déploiement ;
- conserver uniquement l’origine exacte du client dans `CLIENT_ORIGIN`.
