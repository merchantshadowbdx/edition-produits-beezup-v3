import json

import pandas as pd
import streamlit as st

import api_services as api
import data_processing as proc


def render(selected_category_path: str):
    """
    Affiche la sélection des attributs.
    Réagit dynamiquement au changement de 'selected_category_path'.
    """

    # Si la catégorie en entrée change, on force le rechargement des attributs
    if st.session_state.get("last_category") != selected_category_path:
        st.session_state.df_all_attributes = None
        st.session_state.df_selected_attributes = None  # On force à re-valider
        st.session_state.last_category = selected_category_path

    # Style CSS
    st.html("<style>.st-key-attributes_container { box-shadow: 0px 2px 20px rgba(0, 0, 0, 0.5); }</style>")

    # Container de sélection des attributs
    with st.container(border=True, gap="medium", key="attributes_container"):
        st.subheader("📝 Sélection des attributs")

        # 1. Extractions si nécessaire
        if st.session_state.df_all_attributes is None:
            with st.spinner(f"Extraction des attributs pour : {selected_category_path}..."):
                try:
                    # Extraction des attributs channel
                    df_chan = api.get_channel_attributes(st.session_state.client, st.session_state.channel_id)

                    # Extraction des attributs catégorie
                    df_cat = api.get_channel_category_attributes(
                        st.session_state.client,
                        st.session_state.catalog_id,
                        selected_category_path
                    )

                    # Fusion des dataframes attributs
                    df_concat = pd.concat([df_chan, df_cat], ignore_index=True)

                    # Normalisation des IDs
                    df_concat["Channel Attribute Id"] = (
                        df_concat["Channel Attribute Id"]
                        .astype(str)
                        .str.lower()
                        .str.strip()
                    )
                    df_concat["Status"] = df_concat["Status"].str.title()
                    df_concat["Type Value"] = df_concat["Type Value"].str.title()

                    # Remplissage des ["Attribute Code"] vides avec l'["Attribute Name"]
                    df_concat["Attribute Code"] = (
                        df_concat["Attribute Code"].fillna(df_concat["Attribute Name"])
                        .astype(str)
                        .str.strip()
                    )

                    # Dédoublonnage et création de la colonne ["Label"]
                    df_clean = proc.dedupe_keep_most_restrictive(df_concat)

                    # Extraction du mapping colonnes
                    mapping_dict = api.get_column_mapping_dict(st.session_state.client, st.session_state.catalog_id)

                    # Ajout de la colonne ["Is Mapped"]
                    df_clean["Is Mapped"] = df_clean["Channel Attribute Id"].apply(
                        lambda x: x in mapping_dict and mapping_dict[x] is not None
                    )

                    # Importation des attributs obligatoires selon le canal de vente
                    with open("required_attributes.json", "r", encoding="utf-8") as f:
                        required_data = json.load(f)

                    # Extraction des attributs obligatoires pour le canal de vente
                    sales_channel = st.session_state.store_name.split("_")[-1]
                    required_attributes = required_data.get(sales_channel, [])
                    required_attributes_clean = [str(a).strip() for a in required_attributes]
                    st.session_state.required_attributes = required_attributes_clean

                    # Modification de ["Source"] pour les attributs obligatoires vers "Obligatory"
                    mask_obl = df_clean["Attribute Code"].isin(required_attributes_clean)
                    df_clean.loc[mask_obl, "Source"] = "Obligatory"

                    # Tri des colonnes du Dataframe
                    desired_order = [
                        "Source",
                        "Channel Category Path",
                        "Label",
                        "Attribute Name",
                        "Attribute Code",
                        "Channel Attribute Id",
                        "Status",
                        "Type Value",
                        "Default Value",
                        "Attribute Value List Code",
                        "Attribute Description",
                        "Is Mapped"
                    ]
                    df_clean = df_clean[desired_order]
                    st.session_state.df_all_attributes = df_clean

                except Exception as e:
                    st.error(f"Erreur lors de l'extraction : {e}")
                    return None

        # 2. Interface de filtrage
        df_attr = st.session_state.df_all_attributes
        col_source, col_status, col_select = st.columns([1, 1, 1.5])

        with col_source:
            st.markdown("**Sources :**")
            # "Obligatory" est géré à part, on ne l'affiche pas dans les filtres.
            available_sources = [s for s in df_attr["Source"].unique() if s != "Obligatory"]
            selected_sources = st.pills(
                "Sources",
                label_visibility="collapsed",
                options=available_sources,
                selection_mode="multi",
                # default=["Cross Categories", "Category"],
                key=f"pills_src_{selected_category_path}"  # Clé dynamique pour éviter les conflits
            )

        with col_status:
            st.markdown("**Statuts :**")
            status_order = {"Required": 0, "Recommended": 1, "Optional": 2}
            available_statuses = sorted(
                df_attr["Status"].dropna().unique(),
                key=lambda s: status_order.get(s, 99)
            )
            selected_statuses = st.pills(
                "Statuts",
                label_visibility="collapsed",
                options=available_statuses,
                selection_mode="multi",
                default=["Required"],
                key=f"pills_stat_{selected_category_path}"
            )

        # 3. Calcul de la sélection finale
        df_obligatory = df_attr[df_attr["Source"] == "Obligatory"]

        # Filtre selon les Pills
        mask = (df_attr["Source"].isin(selected_sources or [])) & \
               (df_attr["Status"].isin(selected_statuses or []))
        df_filtered = df_attr[mask]

        current_selection = pd.concat([df_obligatory, df_filtered]).drop_duplicates(subset=["Label"])

        # Ajout des attributs de la sélection unitaire
        remaining_attr = df_attr[~df_attr["Label"].isin(current_selection["Label"])]

        with col_select:
            st.markdown("**Sélection manuelle :**")
            extra_options = remaining_attr.to_dict(orient="records")
            selected_extra = st.multiselect(
                "Attributs non sélectionnés",
                label_visibility="collapsed",
                options=extra_options,
                format_func=lambda r: f"{r['Attribute Name']} | {r['Source']}",
                key=f"extra_{selected_category_path}"
            )

        # Assemblage final
        if selected_extra:
            df_extra = pd.DataFrame(selected_extra)
            final_selection = pd.concat([current_selection, df_extra]).drop_duplicates(subset=["Label"])
        else:
            final_selection = current_selection

        # 4. Affichage du résumé
        with st.expander(f"Voir le détail des **{len(final_selection)} attributs sélectionnés**"):
            st.dataframe(
                final_selection[["Attribute Name", "Status", "Source"]].sort_values("Attribute Name"),
                hide_index=True,
                width="stretch"
            )

        if st.button(
                label="Valider la sélection",
                type="primary",
                width=200,
                key="attributes_selection",
                icon=":material/check:"
        ):
            st.session_state.df_selected_attributes = final_selection

        if st.session_state.df_selected_attributes is not None:
            return st.session_state.df_selected_attributes

        return None
