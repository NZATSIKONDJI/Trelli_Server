# Trelli — Installation et test après clonage

Ce guide explique comment installer les outils nécessaires, cloner les deux dépôts Trelli et lancer l’application complète avec Docker Compose.

## 1. Installer les prérequis

### Git

Git est nécessaire pour cloner les deux dépôts. Après son installation, vérifier :

```powershell
git --version
```

### Python

Télécharger et installer Python depuis le site officiel :

<https://www.python.org/downloads/windows/>

Python 3.12 est recommandé pour correspondre à l’image utilisée par le serveur. Pendant l’installation sous Windows, activer l’option permettant d’ajouter Python au `PATH`.

Vérifier ensuite :

```powershell
python --version
python -m pip --version
```

Python n’est pas indispensable pour exécuter les conteneurs, car il est déjà présent dans l’image du serveur. Il est toutefois nécessaire pour lancer directement les tests automatiques hors Docker.

### Docker Desktop

Télécharger et installer Docker Desktop depuis la documentation officielle :

<https://docs.docker.com/desktop/setup/install/windows-install/>

Sous Windows, Docker Desktop utilise généralement WSL 2. La virtualisation matérielle doit être activée dans le BIOS/UEFI. Si nécessaire, installer ou mettre à jour WSL depuis un terminal administrateur :

```powershell
wsl --install
wsl --update
```

Redémarrer l’ordinateur si Windows le demande, ouvrir Docker Desktop et attendre l’indication **Engine running**.

Vérifier ensuite :

```powershell
docker --version
docker compose version
docker info
```

`docker info` doit fonctionner sans erreur avant de continuer.

## 2. Cloner les deux dépôts

Créer un dossier commun afin que les deux dépôts soient placés côte à côte :

```powershell
cd $HOME\Desktop
mkdir TRELLI
cd TRELLI
```

Cloner ensuite les dépôts en conservant exactement les noms indiqués :

```powershell
git clone <https://github.com/NZATSIKONDJI/Trelli_Client.git > trelli-client
git clone <https://github.com/NZATSIKONDJI/Trelli_Server.git> trelli-server
```


L’organisation attendue est :

```text
TRELLI/
├── trelli-client/
└── trelli-server/
    └── docker-compose.yml
```

Le fichier `docker-compose.yml` doit être versionné dans le dépôt serveur. Ses chemins de construction doivent pointer vers :

```yaml
services:
  client:
    build: ../trelli-client

  server:
    build: .
```


## 3. Créer les secrets MySQL

Depuis le dépôt serveur :

```powershell
cd trelli-server
mkdir secrets
```

Créer manuellement les deux fichiers suivants :

```text
secrets/mysql_password.txt
secrets/mysql_root_password.txt
```

Contenu attendu :

- `mysql_password.txt` contient uniquement le mot de passe de `project_user` ;
- `mysql_root_password.txt` contient uniquement un autre mot de passe pour `root`.

Ne pas écrire le nom de l’utilisateur, de guillemets ou de déclaration de variable dans ces fichiers. Chaque fichier contient un seul mot de passe sur une ligne.

Exemple de forme, à remplacer :

```text
MotDePasseProjet_2026
```

Les deux mots de passe doivent être différents. Le dossier `secrets` ne doit jamais être ajouté à Git.

## 4. Configurer le serveur

Copier le modèle de configuration :

```powershell
Copy-Item .env.example .env
```

Ouvrir `.env` et renseigner :

```dotenv
APP_ENV=development
DATABASE_URL=mysql+pymysql://project_user:MOT_DE_PASSE_MYSQL@mysql:3306/project_db
JWT_SECRET=REMPLACER_PAR_UNE_VALEUR_ALEATOIRE_DE_32_CARACTERES_MINIMUM
CLIENT_ORIGIN=http://localhost:8080
COOKIE_SECURE=false
ACCESS_TOKEN_MINUTES=30
DEMO_PASSWORD=MotDePasseDemo_2026
```

Remplacer `MOT_DE_PASSE_MYSQL` par la valeur de `secrets/mysql_password.txt`.

Pour éviter les problèmes d’encodage dans `DATABASE_URL`, utiliser pour le test un mot de passe composé de lettres, chiffres, tirets et tirets bas. Les caractères comme `@`, `:`, `/`, `#` ou `%` doivent sinon être encodés dans l’URL.

Le fichier `.env` ne doit jamais être ajouté à Git.

## 5. Vérifier les fichiers indispensables

Dans `trelli-server` :

```powershell
Test-Path Dockerfile
Test-Path docker-compose.yml
Test-Path .env
Test-Path secrets/mysql_password.txt
Test-Path secrets/mysql_root_password.txt
Test-Path ../trelli-client/Dockerfile
```

Chaque commande doit afficher `True`.

## 6. Vérifier Docker Compose

Toujours depuis `trelli-server` :

```powershell
docker compose config --services
```

Les services attendus sont :

```text
mysql
server
client
phpmyadmin
```

La commande suivante permet de valider toute la configuration :

```powershell
docker compose config --quiet
```

Si elle ne produit aucun message, le fichier Compose est valide.

## 7. Construire et démarrer Trelli

```powershell
docker compose up --build -d
```

Le premier lancement peut durer plusieurs minutes, car Docker doit télécharger les images, installer les dépendances Python et initialiser MySQL.

## 8. Vérifier les conteneurs

```powershell
docker compose ps
```

Les quatre services doivent être démarrés. MySQL et le serveur doivent devenir `healthy` après leur initialisation.

Si leur état est encore `starting`, patienter quelques secondes puis relancer :

```powershell
docker compose ps
```

## 9. Vérifier l’API

Le serveur n’expose pas directement son port `8000`. La vérification passe par Nginx :

```powershell
Invoke-RestMethod http://localhost:8080/api/sante
```

Résultat attendu :

```text
etat
----
ok
```

## 10. Ouvrir l’application

- Trelli : <http://localhost:8080>
- phpMyAdmin : <http://localhost:8081>

Compte propriétaire de démonstration :

```text
Courriel     : TrelliKarl@mentor.com
Mot de passe : valeur de DEMO_PASSWORD dans .env
```

Compte participant :

```text
Courriel     : TrelliParticipant@mentor.com
Mot de passe : valeur de DEMO_PASSWORD dans .env
```

Connexion phpMyAdmin :

```text
Serveur      : mysql
Utilisateur  : project_user
Mot de passe : contenu de secrets/mysql_password.txt
Base         : project_db
```

Le compte `root` n’est pas nécessaire pour tester l’application.

## 11. Scénario de validation fonctionnelle

Avec `TrelliKarl@mentor.com` :

1. se connecter ;
2. créer un projet ;
3. modifier son titre, sa description et son statut ;
4. ajouter `TrelliParticipant@mentor.com` au projet ;
5. créer une tâche et l’assigner au participant ;
6. changer son statut ;
7. vérifier l’onglet « Équipe et rôles » ;
8. promouvoir temporairement le participant administrateur ;
9. vérifier que le propriétaire conserve son rôle ;
10. se déconnecter.

Avec `TrelliParticipant@mentor.com` :

1. se connecter ;
2. vérifier que toutes les tâches du projet sont visibles ;
3. vérifier que l’onglet « Équipe et rôles » est masqué si son rôle est participant ;
4. créer une tâche ;
5. modifier, supprimer ou changer le statut d’une tâche créée ou assignée ;
6. vérifier qu’une autre tâche non assignée ne peut pas être modifiée ;
7. se déconnecter et vérifier que les champs de connexion sont vidés.

Dans phpMyAdmin, vérifier les tables :

```text
utilisateurs
projets
participants_projet
taches
```

## 12. Tests automatiques du serveur

Python doit être installé pour cette étape. Depuis `trelli-server` :

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Les tests utilisent SQLite et ne modifient pas la base MySQL des conteneurs.

## 13. Dépannage

Afficher l’état :

```powershell
docker compose ps
```

Afficher tous les journaux :

```powershell
docker compose logs
```

Afficher les journaux d’un service :

```powershell
docker compose logs server
docker compose logs mysql
docker compose logs client
docker compose logs phpmyadmin
```

Suivre les journaux en direct :

```powershell
docker compose logs -f
```

Si Docker affiche `Virtualization support not detected`, activer la virtualisation dans le BIOS/UEFI et vérifier WSL 2 avant de relancer Docker Desktop.

Si `localhost:8081` ne répond pas, vérifier que le service `phpmyadmin` apparaît dans `docker compose ps`.

Si le serveur ne démarre pas, vérifier en priorité que le mot de passe de `DATABASE_URL` correspond exactement à `secrets/mysql_password.txt`.

## 14. Arrêter l’application

Conserver les données MySQL :

```powershell
docker compose down
```

Relancer ultérieurement :

```powershell
docker compose up -d
```

La commande suivante supprime également le volume MySQL et toutes les données. Elle ne doit être utilisée que pour recommencer avec une base vide :

```powershell
docker compose down -v
```
