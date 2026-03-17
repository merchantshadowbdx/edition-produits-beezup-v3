from typing import Any
from urllib.parse import urljoin

import requests
from loguru import logger
from requests.exceptions import HTTPError, Timeout

logger = logger.bind(user="System", store="API")


class BeezUPClient:
    def __init__(self, login, password):
        self.base_url = "https://api.beezup.com"
        self.session = requests.Session()
        self.login = login
        self.password = password
        self.token = None

    def _build_url(self, endpoint):
        """Fusionne proprement la base URL et endpoint."""
        path = endpoint.lstrip('/')
        return urljoin(self.base_url + '/', path)

    def authenticate(self):
        """Récupère le token et l'injecte dans la session."""
        logger.info("Tentative d'authentification auprès de BeezUP...")
        url = self._build_url("V2/public/security/login")
        payload = {"login": self.login, "password": self.password}

        data = self._request("POST", url, json=payload)

        if data and "credentials" in data:
            credentials = data["credentials"]
            self.token = next((c.get("primaryToken") for c in credentials if c.get("primaryToken")), None)

            if self.token:
                # Configuration de la session pour les appels futurs
                self.session.headers.update({
                    "Content-Type": "application/json",
                    "Ocp-Apim-Subscription-Key": self.token
                })
                logger.success("Authentification réussie.")
                return True

        logger.error("Impossible de récupérer le Primary Token.")
        return False

    def _request(self, method, url, **kwargs) -> Any:
        """Méthode privée qui centralise les appels HTTP et la gestion d'erreurs."""
        try:
            kwargs.setdefault("timeout", 30)
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json() if response.text else True

        except Timeout:
            logger.error(f"Timeout sur {method}.")
            raise
        except HTTPError as e:
            status = e.response.status_code
            logger.error(f"Erreur API BeezUP | Statut : {status}.")
            raise
        except Exception as e:
            logger.critical(f"Erreur inattendue | {type(e).__name__}.")
            raise

    # Méthodes publiques simplifiées
    def get(self, endpoint, params=None):
        url = self._build_url(endpoint)
        return self._request("GET", url, params=params)

    def post(self, endpoint, data=None, json=None):
        url = self._build_url(endpoint)
        return self._request("POST", url, data=data, json=json)

    def put(self, endpoint, data=None, json=None):
        url = self._build_url(endpoint)
        return self._request("PUT", url, data=data, json=json)

