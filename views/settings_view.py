# views/settings_view.py
import streamlit as st

import api_services as api
from logger_utils import get_log_context

def render():
    """Gère la saisie du Catalog ID et affiche les infos de la boutique."""

    logger = get_log_context()

    # Style CSS
    st.html("<style>.st-key-settings_container { box-shadow: 0px 2px 20px rgba(0, 0, 0, 0.5); }</style>")

    # Container de sélection de la boutique
    with st.container(border=True, gap="medium", key="settings_container"):
        st.subheader("🛍️ Sélection de la boutique")

        # Cas 1 : Le Catalog ID n'est pas encore renseigné
        if not st.session_state.get("catalog_id"):
            catalog_input = st.text_input("Saisissez le Channel Catalog ID :", key="input_catalog_id")

            if st.button("Valider", type="primary", width=200, key="store_selection", icon=":material/check:"):
                if catalog_input:
                    logger.info("Chargement du catalogue vendeur.")
                    with st.spinner("Chargement du catalogue vendeur..."):
                        try:
                            infos = api.get_catalog_infos(st.session_state.client, catalog_input)

                            # Stockage dans session_state
                            st.session_state.catalog_id = catalog_input
                            st.session_state.store_id = infos["storeId"]
                            st.session_state.channel_id = infos["channelId"]
                            st.session_state.store_name = api.get_store_name(st.session_state.client, infos["storeId"])

                            logger = get_log_context()
                            logger.success(f"Chargement du catalogue de {st.session_state.store_name} réussi.")

                            st.rerun()

                        except Exception as e:
                            logger.warning(f"Échec lors du chargement du catalogue | Erreur {type(e).__name__}.")
                            st.warning(f"Channel Catalog ID invalide ou erreur API.")

                else:
                    st.warning("Veuillez entrer un ID.")

        # Cas 2 : Le catalogue est déjà chargé (Mode "Résumé")
        else:
            st.write(f"Boutique BeezUP sélectionnée : :orange[{st.session_state.store_name}]")

