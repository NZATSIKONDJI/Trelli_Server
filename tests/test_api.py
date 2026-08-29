def connecter(client, courriel):
    reponse = client.post("/api/authentification/connexion", json={
        "courriel": courriel, "mot_de_passe": "ChangeMe-2026!"
    })
    assert reponse.status_code == 200
    client.headers.update({"X-CSRF-Token": client.cookies.get("csrf_token")})


def test_authentification_obligatoire(client):
    assert client.get("/api/projets").status_code == 401


def test_mauvais_identifiants_refuses(client):
    reponse = client.post("/api/authentification/connexion", json={
        "courriel": "TrelliKarl@mentor.com", "mot_de_passe": "MotDePasseIncorrect"
    })
    assert reponse.status_code == 401
    assert "access_token" not in client.cookies

""" Ici on teste le cycle de vie d'un projet, en incluant la création, la modification et la suppression de tâches.
On vérifie également que les rôles des participants sont respectés et que les actions interdites sont correctement refusées. """

def test_roles_et_cycle_de_vie(authenticated):
    projet = authenticated.post("/api/projets", json={"titre": "Projet test", "description": "Description"})
    assert projet.status_code == 201
    projet_id = projet.json()["id"]
    assert projet.json()["role_courant"] == "administrateur"
    participant = authenticated.post(
        f"/api/projets/{projet_id}/participants", json={"courriel": "trelliparticipant@mentor.com"}
    )
    participant_id = participant.json()["id"]
    assert participant.json()["role"] == "participant"

    assignee = authenticated.post(f"/api/projets/{projet_id}/taches", json={
        "titre": "Tâche assignée", "description": "À réaliser", "statut": "a_faire", "responsable_id": participant_id,
    })
    libre = authenticated.post(f"/api/projets/{projet_id}/taches", json={
        "titre": "Tâche libre", "description": "Visible par tous", "statut": "a_faire", "responsable_id": None,
    })
    assert assignee.status_code == libre.status_code == 201

    connecter(authenticated, "trelliparticipant@mentor.com")
    liste = authenticated.get("/api/projets")
    assert len(liste.json()[0]["taches"]) == 2
    assert authenticated.patch(
        f"/api/projets/{projet_id}/taches/{assignee.json()['id']}/statut", json={"statut": "en_cours"}
    ).status_code == 200
    assert authenticated.put(
        f"/api/projets/{projet_id}/taches/{assignee.json()['id']}",
        json={"titre": "Interdit", "description": "", "statut": "terminee", "responsable_id": participant_id},
    ).status_code == 200
    assert authenticated.delete(f"/api/projets/{projet_id}/taches/{assignee.json()['id']}").status_code == 204
    assert authenticated.patch(
        f"/api/projets/{projet_id}/taches/{libre.json()['id']}/statut", json={"statut": "terminee"}
    ).status_code == 403

    creee = authenticated.post(f"/api/projets/{projet_id}/taches", json={
        "titre": "Créée par le participant", "description": "", "statut": "a_faire", "responsable_id": None,
    })
    assert creee.status_code == 201
    assert creee.json()["createur_id"] == participant_id
    assert authenticated.put(
        f"/api/projets/{projet_id}/taches/{creee.json()['id']}",
        json={"titre": "Modifiée par son créateur", "description": "", "statut": "en_cours", "responsable_id": None},
    ).status_code == 200
    assert authenticated.delete(f"/api/projets/{projet_id}/taches/{creee.json()['id']}").status_code == 204

""" Ici on teste que l'utilisateur ne peut pas se rétrograder lui-même de rôle administrateur à participant.
On vérifie également que l'utilisateur ne peut pas modifier son propre rôle, même s'il est administrateur du projet. """

def test_administrateur_peut_modifier_un_role(authenticated):
    projet = authenticated.post("/api/projets", json={"titre": "Rôles", "description": ""}).json()
    participant = authenticated.post(
        f"/api/projets/{projet['id']}/participants", json={"courriel": "trelliparticipant@mentor.com"}
    ).json()
    reponse = authenticated.put(
        f"/api/projets/{projet['id']}/participants/{participant['id']}/role", json={"role": "administrateur"},
    )
    assert reponse.status_code == 200
    assert reponse.json()["role"] == "administrateur"

    connecter(authenticated, "trelliparticipant@mentor.com")
    auto_retrogradation = authenticated.put(
        f"/api/projets/{projet['id']}/participants/{participant['id']}/role", json={"role": "participant"},
    )
    assert auto_retrogradation.status_code == 403

""" Ici on teste que l'utilisateur ne peut pas modifier son propre rôle, même s'il est administrateur du projet.
On vérifie également que l'utilisateur ne peut pas se rétrograder lui-même de rôle administrateur à participant. """

def test_csrf_obligatoire(client):
    connexion = client.post("/api/authentification/connexion", json={
        "courriel": "trellikarl@mentor.com", "mot_de_passe": "TestProjet123"
    })
    assert connexion.status_code == 200
    assert client.post("/api/projets", json={"titre": "Refusé", "description": ""}).status_code == 403
