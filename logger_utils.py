# logger_utils.py
import sys

import streamlit as st
from loguru import logger


def setup_logging():
    """Initialise le logger avec un fichier et la console."""
    # On retire la config par défaut pour éviter les doublons
    logger.remove()

    # On ajoute des valeurs par défaut pour que {extra[user]} existe toujours
    logger.configure(extra={"user": "System", "store": "Global"})

    # Formatage : Date | Niveau | User | Store | Message
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{extra[user]}</cyan> @ <magenta>{extra[store]}</magenta> | "
        "<level>{message}</level>"
    )

    logger.add(sys.stdout, format=log_format, level="INFO")
    logger.add("log.txt", format=log_format, level="DEBUG", rotation="10 MB", compression="zip")


def get_log_context():
    """Récupère le contexte utilisateur actuel depuis le session_state."""
    user_info = st.session_state.get("user_info", {})

    if not user_info:
        user_name = "Guest"
    else:
        user_name = user_info.get("firstName", "Guest")

    store_name = st.session_state.get("store_name")
    if not store_name:
        store_name = "NoStore"

    # On retourne un logger "enrichi" avec ces informations
    return logger.bind(user=user_name, store=store_name)
