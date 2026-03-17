import io
import re
import time

import streamlit as st

import api_services as api
import data_processing as proc
import excel_utils as excel
from logger_utils import get_log_context


def render(selected_path, skus_list, df_selected_attributes):
    """
    Affiche l'aperçu et gère la génération finale du fichier Excel.
    """
    logger = get_log_context()

    # Style CSS
    st.html("<style>.st-key-export_container { box-shadow: 0px 2px 20px rgba(0, 0, 0, 0.5); }</style>")

    with st.container(border=True, key="export_container", gap="medium"):
        st.subheader("🔎 Création du template")

        # - On vérifie si on a déjà un export prêt pour CE chemin précis.
        # - On crée une clé unique pour l'état actuel.
        # - Si la clé est différente, on vide l'ancien export pour forcer le nouveau calcul.
        current_state_key = f"{selected_path}_{len(skus_list)}_{len(df_selected_attributes)}"
        if st.session_state.get("last_export_key") != current_state_key:
            st.session_state.final_excel_data = None
            st.session_state.df_preview_head = None

        # Si l'export n'est pas encore fait, on initialise la barre de progression.
        if st.session_state.get("final_excel_data") is None:
            progress_bar = st.progress(0)
            status_text = st.empty()
            client = st.session_state.client
            catalog_id = st.session_state.catalog_id

            try:
                with st.spinner("Construction du template..."):
                    # --- ETAPE 1 : Extraction des product ids ---
                    logger.info(f"Extraction des produits pour la catégorie : {selected_path}.")
                    status_text.text("Extraction des produits...")
                    df_ids = api.get_product_ids(client, catalog_id, selected_path, skus_list=skus_list)
                    progress_bar.progress(10)

                    # --- ETAPE 2 : Téléchargement du fichier d'export BeezUP ---
                    logger.info("Téléchargement des valeurs d'attributs.")
                    status_text.text("Téléchargement des valeurs d'attributs...")
                    df_values = api.download_export_file(catalog_id)
                    progress_bar.progress(20)

                    # --- ÉTAPE 3 : Fusion des données ---
                    logger.info("Fusion des dataframes df_ids et df_values.")
                    status_text.text("Traitement des données...")
                    df_merged = proc.merge_export_data(df_ids, df_values)
                    logger.info(f"Fusion réussie : {len(df_merged)} lignes générées.")
                    progress_bar.progress(30)

                    # --- ETAPE 4 : Filtrage des colonnes sélectionnées ---
                    logger.info("Filtrage des attributs sélectionnés.")
                    status_text.text("Filtrage des attributs sélectionnées...")

                    # On récupère la liste des codes depuis le DataFrame des attributs
                    selected_codes = df_selected_attributes["Attribute Code"].tolist()
                    selected_codes = [c for c in selected_codes if c.lower() != "sku"]
                    df_merged_filtered = proc.filter_export_columns(df_merged, selected_codes)
                    logger.info(f"Colonnes filtrées : {len(df_merged_filtered.columns)} colonnes conservées.")
                    progress_bar.progress(40)

                    # --- ÉTAPE 5 : Formatage du template ---
                    logger.info("Formatage du template.")
                    status_text.text("Formatage final du fichier...")

                    # On crée un dictionnaire pour le renommage final des colonnes.
                    code_to_label = dict(zip(df_selected_attributes["Attribute Code"], df_selected_attributes["Label"]))

                    # Récupération des attributs obligatoires
                    obl_codes = st.session_state.get("required_attributes", [])

                    df_template = proc.format_final_template(
                        df_merged_filtered,
                        df_selected_attributes,
                        catalog_id,
                        selected_path,
                        code_to_label,
                        obl_codes
                    )

                    logger.info("Formatage et renommage des colonnes terminés.")
                    progress_bar.progress(50)

                    # --- ÉTAPE 6 : Extraction des listes bornées
                    status_text.text("Récupération des listes déroulantes...")
                    logger.info("Extraction des listes déroulantes.")
                    df_list_of_values = api.build_dropdown_dataframe(client, catalog_id, df_selected_attributes)
                    logger.info("Extraction des listes déroulantes terminées.")
                    progress_bar.progress(60)

                    # --- ÉTAPE 7 : Normalisation des types de données ---
                    logger.info("Normalisation des types de données.")
                    status_text.text("Normalisation des données du template...")
                    df_template = proc.normalize_export_data(df_template, df_list_of_values)
                    logger.info("Normalisation terminée.")
                    progress_bar.progress(70)

                    # --- ÉTAPE 8 : Renommage des valeurs d'attributs des listes bornées en "code | label" ---
                    status_text.text("Normalisation des attributs des listes bornées.")
                    logger.info("Renommage des valeurs d'attributs des listes bornées.")
                    df_template = proc.map_codes_to_labels(df_template, df_list_of_values)
                    progress_bar.progress(80)

                    # --- ÉTAPE 9 : Mise en mémoire du template et construction du fichier Excel ---
                    status_text.text("Création du fichier Excel...")
                    logger.info("Création du fichier Excel")
                    output = io.BytesIO()
                    excel.build_and_export_excel(df_template, df_selected_attributes, df_list_of_values, output)
                    progress_bar.progress(90)

                    # Sauvegarde du résultat dans le session_state
                    st.session_state.final_excel_data = output.getvalue()
                    st.session_state.df_preview_head = df_template.iloc[:, 3:].head(20)
                    st.session_state.last_export_key = current_state_key
                    st.session_state.total_count = len(df_template)

                    progress_bar.progress(100)
                    status_text.text("Template généré avec succès !")
                    logger.success("Template généré.")

                    time.sleep(1)

                    progress_bar.empty()
                    status_text.empty()

            # except Exception as e:
            #     logger.error(f"Échec de la génération : {e}.")
            #     st.error(f"Une erreur technique est survenue : {e}")
            #     return

            except ValueError as e:
                # Erreur de logique ou de données (ex: "Fichier vide")
                logger.warning(f"Données invalides : {e}")
                st.warning(f"Problème avec les données : {e}")
                return

            except Exception as e:
                # L'erreur critique inattendue (le crash pur)
                logger.critical(f"ERREUR CRITIQUE : {type(e).__name__} - {e}")
                st.error(f"Une erreur technique est survenue : {e}")
                return

            finally:
                # Ce bloc s'exécute TOUJOURS, qu'il y ait eu une erreur ou non.
                if "progress_bar" in locals():
                    progress_bar.empty()
                if "status_text" in locals():
                    status_text.empty()

        if st.session_state.get("df_preview_head") is not None:
            st.dataframe(st.session_state.df_preview_head, width="stretch", hide_index=False)

            # Création du nom du fichier
            last_level = selected_path.split(" > ")[-1]
            clean_name = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "", last_level)
            count = st.session_state.get("total_count", 0)

            st.download_button(
                label="Télécharger le template",
                data=st.session_state.final_excel_data,
                file_name=f"{st.session_state.store_name}_{clean_name} [{count} produits].xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                width="content",
                icon=":material/download:"
            )
