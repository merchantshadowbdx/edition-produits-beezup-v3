import streamlit as st

import api_services as api
import data_processing as proc
from logger_utils import get_log_context


def render():
    """Affiche la sélection des catégories avec cascade dynamique et filtrage SKU."""

    logger = get_log_context()

    # Style CSS
    st.html("<style>.st-key-category_container { box-shadow: 0px 2px 20px rgba(0, 0, 0, 0.5); }</style>")

    # Container de sélection de la catégorie
    with st.container(border=True, gap="medium", key="category_container"):
        st.subheader("🔖 Sélection de la catégorie")

        # 1. Chargement des catégories si nécessaire
        current_catalog = st.session_state.get("catalog_id")
        last_catalog = st.session_state.get("last_catalog_id")

        if st.session_state.get("df_available_categories") is None or current_catalog != last_catalog:
            client = st.session_state.client
            catalog_id = st.session_state.catalog_id
            store_id = st.session_state.store_id

            with st.spinner("Chargement des catégories mappées..."):
                try:
                    # Extraction des dataframes nécessaires
                    df_cat = api.get_catalog_categories(client, store_id)
                    df_map = api.get_category_mapping(client, catalog_id)

                    # Fusion pour obtenir la liste des catégories mappées ayant au moins un produit
                    st.session_state.df_available_categories = proc.get_available_categories(df_cat, df_map)
                    st.session_state.last_catalog_id = current_catalog

                    logger.info("Extraction des catégories réussi.")

                except Exception as e:
                    st.error(f"Erreur lors du chargement des catégories: {e}")
                    return

        # 2. Interface de sélection de la catégorie
        df_categories = st.session_state.df_available_categories

        if df_categories.empty:
            st.warning("Aucune catégorie disponible ou mappée.")
            return

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Hiérarchie de la catégorie :**")
            # Transformation du chemin "A > B > C" en liste [A, B, C] pour la cascade
            paths_list = df_categories["Channel Category Path"].str.split(" > ").tolist()

            selected_path = []
            level = 0
            while True:
                candidates = [
                    path[level] for path in paths_list
                    if len(path) > level and path[:level] == selected_path
                ]
                options = sorted(set(candidates))
                if not options:
                    break

                key = f"cat_lvl_{level}_{st.session_state.catalog_id}"
                # Comportement dynamique : selectbox désactivée si un seul choix
                choice = st.selectbox(
                    f"Niveau {level + 1}",
                    options=options,
                    index=0,
                    key=key,
                    disabled=(len(options) == 1)
                )
                selected_path.append(choice)
                level += 1

        with col2:
            st.markdown("**Filtrage par SKUs (optionnel) :**")
            raw_skus = st.text_area(
                "Saisissez une liste de SKUs (un par ligne)",
                key=f"skus_list_{st.session_state.catalog_id}"
            )
            skus_list = [sku.strip() for sku in raw_skus.splitlines() if sku.strip()]

        # Vérification du nombre de produits de la catégorie
        full_path_str = " > ".join(selected_path)
        row = df_categories[df_categories["Channel Category Path"] == full_path_str]

        if not row.empty:
            count = int(row.iloc[0]["Total Product Count"])
            is_limit_exceeded = count > 1000
            badge_color = "green" if not is_limit_exceeded else "red"

            st.markdown(f"**Sélection :** {full_path_str} :{badge_color}-badge[{count} produits]")

            if is_limit_exceeded and not skus_list:
                st.warning(
                    """⚠️ Vous vous apprêtez à traiter un grand volume de produits. 
                    Afin de réduire l'impact sur BeezUP, indiquez une liste de SKUs à traiter.""")
                validate_disabled = True
            else:
                validate_disabled = False
        else:
            st.info("Veuillez sélectionner une catégorie valide.")
            validate_disabled = True

        if st.button(
                "Valider la catégorie",
                disabled=validate_disabled,
                type="primary",
                width=200,
                key="category_selection",
                icon=":material/check:"
        ):
            st.session_state.selected_category = full_path_str
            st.session_state.selected_skus = skus_list

        if st.session_state.get("selected_category"):
            return st.session_state.selected_category, st.session_state.get("selected_skus", [])

        return None

