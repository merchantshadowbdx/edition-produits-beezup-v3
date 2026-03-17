# views/login_view.py
import streamlit as st

import api_services as api
from beezup_client import BeezUPClient
from logger_utils import get_log_context


def render():
    """Affiche l'interface de connexion BeezUP."""

    logger = get_log_context()

    # Style CSS
    st.html("<style>.st-key-login_container { box-shadow: 0px 2px 20px rgba(0, 0, 0, 0.5); } </style>")

    # On crée trois colonnes pour centrer la boîte de connexion.
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        # Tentative de centrage en milieu de page
        st.space("medium")

        with st.container(key="login_container"):
            with st.form(key="login_form"):
                st.subheader(":honeybee: :grey[ShadBeez \u22EE] :orange[\u0190dition \u00FEroduits v\u01B7]")
                st.space("xxsmall")

                email = st.text_input("Email")
                password = st.text_input("Mot de passe", type="password")
                st.space("xxsmall")
                submit_button = st.form_submit_button("Connexion", type="primary", width=200, key="login",
                                                      icon=":material/login:")

                if submit_button:
                    logger.info(f"Tentative de connexion : {email}")

                    if not email or not password:
                        st.warning("Veuillez remplir tous les champs.")
                        return

                    with st.spinner("Authentification en cours..."):
                        client = BeezUPClient(email, password)
                        if client.authenticate():
                            st.session_state.client = client
                            st.session_state.user_info = api.get_user_identity(client)
                            st.session_state.authenticated = True

                            logger = get_log_context()
                            logger.success(f"Connexion réussie : {st.session_state.user_info["firstName"]}")

                            st.rerun()
                        else:
                            logger.warning(f"Échec de connexion : Identifiants invalides pour {email}")
                            st.error("Échec de la connexion. Vérifiez vos identifiants.")

