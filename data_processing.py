import pandas as pd

from logger_utils import get_log_context

logger = get_log_context()


def get_available_categories(df_categories: pd.DataFrame, df_mapping: pd.DataFrame) -> pd.DataFrame:
    """
    Fusion des dataframes get_catalog_categories et get_category_mapping et nettoyage.
    :param df_categories: Le dataframe résultant de l'extraction de get_catalog_categories.
    :param df_mapping: Le dataframe résultant de l'extraction de get_category_mapping.
    :return: Un dataframe avec la liste des "Channel Category Path" et leur nombre de produits correspondants
    (colonnes : Channel Category Path, Total Product Count).
    """
    # On conserve uniquement les catégories présentes dans les deux dataframes.
    df = pd.merge(df_categories, df_mapping, on="Catalog Category", how="inner")

    # On regroupe les catégories "channel" en double en ajoutant leur nombre de produits.
    df_grouped = df.groupby("Channel Category Path")["Total Product Count"].sum().reset_index()

    columns_to_keep = ["Channel Category Path", "Total Product Count"]
    df_result = df_grouped[columns_to_keep]

    return df_result.sort_values(by="Total Product Count", ascending=False).reset_index(drop=True)


def dedupe_keep_most_restrictive(df: pd.DataFrame) -> pd.DataFrame:
    """
    Supprime les doublons d'attributs en conservant la version la plus restrictive
    (Required > Recommended > Optional).
    :param df: Le dataframe avec tous les attributs "Channel" et "Category".
    :return : Un dataframe avec l'ensemble des attributs "Channel" et "Category" nettoyé sans doublon et avec une
    colonne "Label" en tant qu'identifiant unique.
    """
    # 1. Travailler sur une copie pour protéger le DataFrame original
    df_temp = df.copy()

    # 2. Créer la clé unique "Label" en minuscule
    df_temp["Label"] = (
            df_temp["Attribute Name"].astype(str).str.strip() +
            " | " +
            df_temp["Channel Attribute Id"].astype(str).str.strip()
    )

    # 3. Mapping de priorité (plus le chiffre est bas, plus c'est prioritaire)
    rank_map = {
        "Required": 0,
        "Recommended": 1,
        "Optional": 2
    }

    # 4. Normalisation et calcul du rang
    df_temp["_status_rank"] = df_temp["Status"].map(rank_map).fillna(99).astype(int)

    # 5. Dédoublonnage stratégique
    df_dedup = (
        df_temp.sort_values(by=["Label", "_status_rank"], ascending=[True, True])
        .drop_duplicates(subset=["Label"], keep="first")
        .drop(columns=["_status_rank"])
        .reset_index(drop=True)
    )

    return df_dedup


def merge_export_data(df_ids: pd.DataFrame, df_values: pd.DataFrame) -> pd.DataFrame:
    """
    Fusionne les IDs produits avec les valeurs d'attributs via le SKU.
    """
    # Vérification du contenu des dataframes
    if df_ids.empty or df_values.empty:
        raise ValueError("Données insuffisantes pour effectuer la fusion (un des tableaux est vide).")

    # Si "Product Id" se trouve également dans df_values, on supprime la colonne pour éviter les doublons.
    if "Product Id" in df_values.columns:
        df_values = df_values.drop(columns=["Product Id"])

    # Fusion des dataframes
    df_merged = pd.merge(df_ids, df_values, on="sku", how="inner")

    if df_merged.empty:
        raise ValueError("La fusion n'a retourné aucun résultat. Vérifiez que les SKUs correspondent.")

    return df_merged


def filter_export_columns(df_merged: pd.DataFrame, attribute_codes: list) -> pd.DataFrame:
    """
    Filtre les colonnes et assure la présence du pivot de fusion (sku).
    """
    # 1. On définit les colonnes techniques de base dont on a TOUJOURS besoin pour la suite
    # (même si l'utilisateur ne les a pas cochées, on les garde pour l'instant).
    base_cols = ["Product Id", "sku"]

    # 2. On combine avec les attributs choisis par l'utilisateur.
    cols_to_extract = list(dict.fromkeys(base_cols + attribute_codes))

    # 3. On ne garde que ce qui existe réellement dans le DataFrame.
    available_cols = [c for c in cols_to_extract if c in df_merged.columns]

    return df_merged.reindex(columns=available_cols).copy()


def format_final_template(df_merged, df_selected_attributes, catalog_id, selected_path, code_to_label, obl_codes):
    """
    Orchestre le tri, l'insertion des IDs et le renommage des colonnes.
    """
    df = df_merged.copy()

    # --- SECURITÉ : On cherche le nom réel de la colonne Product Id ---
    # On cherche une colonne qui contient "product" et "id" sans se soucier de la casse
    product_id_col = next((c for c in df.columns if "product" in c.lower() and "id" in c.lower()), None)

    if product_id_col is None:
        # Si on ne trouve vraiment rien, on logue les colonnes présentes pour débugger
        logger.error(f"Colonnes disponibles : {list(df.columns)}")
        raise KeyError("La colonne 'Product Id' est introuvable dans le DataFrame fusionné.")

    # --- 1. Insertion des colonnes "Catalog Id" et "Channel Category Path" après "Product Id" ---
    idx = df.columns.get_loc("Product Id")
    df.insert(loc=idx + 1, column="Catalog Id", value=catalog_id)
    df.insert(loc=idx + 2, column="Channel Category Path", value=selected_path)

    # --- 2. Logique de tri des colonnes par importance ---
    def get_sorted_codes(status):
        subset = df_selected_attributes[df_selected_attributes["Status"] == status]
        return subset.sort_values(by="Attribute Name")["Attribute Code"].tolist()

    req_codes_all = get_sorted_codes("Required")
    rec_codes_all = get_sorted_codes("Recommended")
    opt_codes_all = get_sorted_codes("Optional")

    # Nettoyage des doublons/priorités
    req_codes = [c for c in req_codes_all if c not in obl_codes]
    rec_codes = [c for c in rec_codes_all if c not in obl_codes and c not in req_codes]
    opt_codes = [c for c in opt_codes_all if c not in obl_codes and c not in req_codes and c not in rec_codes]

    # --- 3. Reconstruction de l'ordre des colonnes dans le template ---
    first_cols = ["Product Id", "Catalog Id", "Channel Category Path", "sku"]
    ordered_attribute_cols = obl_codes + req_codes + rec_codes + opt_codes

    # On s'assure que les colonnes obligatoires existent sinon on crée une colonne vide.
    for code in obl_codes:
        if code not in df.columns:
            df[code] = pd.NA

    desired_order = first_cols + ordered_attribute_cols
    # existing_desired = [c for c in desired_order if c in df.columns]
    # remaining_cols = [c for c in df.columns if c not in existing_desired]

    # df = df[existing_desired + remaining_cols].copy()

    df = df.reindex(columns=desired_order)
    df = df.fillna("")
    
    # --- 4. Renommage final ---
    # On prépare le dictionnaire de renommage (Codes -> Labels).
    rename_dict = {**code_to_label, "sku": "SKU"}
    return df.rename(columns=rename_dict)


def normalize_export_data(df_template, df_list_of_values):
    """
    Nettoyage et normalisation des types de données selon la structure fixe.
    """
    df = df_template.copy()

    # --- Vérification et suppression des éventuelles colonnes en doubles ---
    if df.columns.duplicated().any():
        cols_doubles = df.columns[df.columns.duplicated()].unique().tolist()
        logger.warning(f"Colonnes dupliquées trouvées : {cols_doubles}")
        df = df.loc[:, ~df.columns.duplicated()]

    # --- Nettoyage et normalisation des types de données
    for i, col in enumerate(df.columns):
        if i == 4:  # EAN : On s'assure qu'il est en string, sans .0, et complété à 13 caractères
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(r"\.0$", "", regex=True)
                .replace(["nan", "None", "<NA>"], "")
                .str.zfill(13)
            )
            # On remplace les "0000000000nan" par du vrai vide si la cellule était vide
            df.loc[df[col].str.contains("nan|None"), col] = ""
            continue  # On passe à la colonne suivante

        # DEBUG : Vérification de la présence de colonnes en double
        # if i == 0:  # On ne le fait qu'une fois au début de la boucle
        #     logger.info(f"Vérification finale des colonnes : {df.columns.tolist()}")
        #     if df.columns.duplicated().any():
        #         logger.error(f"DOUBLONS CRITIQUES DETECTÉS : {df.columns[df.columns.duplicated()]}")

        # Pour toutes les autres colonnes : conversion numérique normale
        converted_col = pd.to_numeric(df[col], errors="coerce")
        if not converted_col.isna().all():
            df[col] = converted_col

    # Harmonisation globale (sauf EAN qui est déjà en string)
    df = df.convert_dtypes()

    # On récupère les noms des colonnes qui ont une liste déroulante
    cols_with_list = df_list_of_values.columns
    for col in cols_with_list:
        if col in df.columns:
            # On force en string propre AVANT le mapping
            df[col] = df[col].astype(str).replace(["<NA>", "nan", "None"], "")

    return df


def map_codes_to_labels(df_template: pd.DataFrame, df_list_of_values: pd.DataFrame) -> pd.DataFrame:
    """
    Remplace les codes bruts par le format 'code | label' dans df_template en se basant sur les correspondances
    trouvées dans df_list_of_values.
    """
    df_mapped = df_template.copy()

    # On boucle sur les colonnes qui ont un menu déroulant (présentes dans df_list_of_values).
    for col in df_list_of_values.columns:
        if col in df_mapped.columns:
            # On crée un dictionnaire de mapping {"code" : "code | label"}
            # On split sur le pipe pour retrouver le code d'origine.
            mapping_dict = {
                str(val).split(" | ")[0]: val
                for val in df_list_of_values[col].dropna()
            }

            # On remplace les valeurs dans le template (ex : "M" devient "M | Male")
            df_mapped[col] = df_mapped[col].astype(str).replace(mapping_dict)

            # Nettoyage des "nan" et valeurs vides
            df_mapped[col] = df_mapped[col].replace({"nan": "", "None": ""})

    return df_mapped
