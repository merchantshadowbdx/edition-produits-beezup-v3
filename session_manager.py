# session_manager.py
import streamlit as st


def get_defaults():
    """Centralisation des valeurs par défaut pour éviter la répétition"""

    return {
        "logger_initialized": False,
        "authenticated": False,
        "client": None,
        "user_info": {},
        "catalog_id": None,
        "last_catalog_id": None,
        "store_name": "NoStore",
        "store_id": None,
        "channel_id": None,
        "df_available_categories": None,
        "selected_category": None,
        "selected_skus": [],
        "required_attributes": [],
        "df_all_attributes": None,
        "df_selected_attributes": None,
        "last_category": None,
        "final_excel_data": None,
        "df_preview_head": None,
        "last_export_key": None,
        "total_count": None
    }


def init_session_state():
    """Initialisation des clés manquantes au démarrage"""

    defaults = get_defaults()
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_to_new_template():
    """Réinitialisation des sélections utilisateurs tout en restant sur la boutique sélectionnée"""

    defaults = get_defaults()
    keep_keys = ["authenticated", "client", "user_info", "catalog_id", "last_catalog_id",
                 "store_name", "store_id", "channel_id"]

    for key, value in defaults.items():
        if key not in keep_keys:
            st.session_state[key] = value


def reset_to_new_catalog():
    """Réinitialisation de tous les paramètres tout en restant connecté"""
    st.cache_data.clear()

    defaults = get_defaults()
    keep_keys = ["authenticated", "client", "user_info"]

    for key, value in defaults.items():
        if key not in keep_keys:
            st.session_state[key] = value

