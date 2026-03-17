# app.py
import streamlit as st

import session_manager as sm
from logger_utils import setup_logging, get_log_context
from views import settings_view, login_view, category_view, attributes_view, export_view, edition_view

# Configuration de la page
st.set_page_config(page_title="ShadBeez \u22EE \u0190dition \u00FEroduits v\u01B7", layout="wide", page_icon="🐝")

# Initialisation du logger
if "logger_initialized" not in st.session_state:
    setup_logging()
    st.session_state.logger_initialized = True

logger = get_log_context()
logger.info("Application démarrée ou rafraîchie")


def main():
    # Initialisation des session_state
    sm.init_session_state()

    # Vérification de la connexion
    if not st.session_state.authenticated:
        login_view.render()
        return

    # Sidebar
    with st.sidebar:
        st.title("🌚 Gestion de session")
        name = st.session_state.user_info.get("firstName", "l'ami")
        st.markdown(f"*\u201FHey :orange[{name}] \u203C \nComment y va çui-ci \u2047\u201D*", unsafe_allow_html=True)

        st.space("xxsmall")

        # Style CSS bouton Réinitialiser
        st.html("<style>.st-key-reset { box-shadow: 0px 2px 20px rgba(0, 0, 0, 0.5); }</style>")
        if st.button("Réinitialiser", type="secondary", width="stretch", key="reset", icon=":material/refresh:"):
            sm.reset_to_new_template()
            st.rerun()

        st.space("xxsmall")

        # Style CSS bouton Changer de boutique
        st.html("<style>.st-key-switch{ box-shadow: 0px 2px 20px rgba(0, 0, 0, 0.5); }</style>")
        if st.button("Changer de boutique", type="secondary", width="stretch", key="switch",
                     icon=":material/swap_horiz:"):
            sm.reset_to_new_catalog()
            st.rerun()

        st.space("xxsmall")

        # Style CSS bouton Déconnexion
        st.html("<style>.st-key-logout { box-shadow: 0px 2px 20px rgba(0, 0, 0, 0.5); }</style>")
        if st.button("Déconnexion", type="secondary", width="stretch", key="logout", icon=":material/logout:"):
            st.session_state.clear()
            st.rerun()

        st.space("small")
        st.caption("Fait avec 💕 par ShadBeez")

    # Mise en page avec onglets
    tab1, tab2 = st.tabs(["G\u00C9N\u00C9RER UN TEMPLATE", "\u00C9DITER DES PRODUITS"])

    with tab1:
        st.space("small")

        # Sélection de la boutique
        settings_view.render()

        if st.session_state.catalog_id:
            st.space("small")

            # Sélection de la catégorie
            category_data = category_view.render()

            if category_data:
                full_path_str, sku_list = category_data
                st.space("small")

                # Sélection des attributs
                df_attr = attributes_view.render(full_path_str)

                # Aperçu du template
                if df_attr is not None:
                    st.space("small")
                    export_view.render(full_path_str, sku_list, df_attr)

    with tab2:
        st.space("small")
        edition_view.render()


if __name__ == "__main__":
    main()

