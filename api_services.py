from io import StringIO
from typing import Optional

import pandas as pd
import requests
import streamlit as st
from loguru import logger


def get_user_identity(client) -> dict[str, str]:
    """
    Récupère le prénom et le nom via l'API BeezUP.
    :param client: Le client BeezUP.
    :return: Un dictionnaire contenant le prénom et le nom de l'utilisateur.
    """
    endpoint = "v2/user/customer/account"
    response = client.get(endpoint)

    if not response:
        return {"firstName": "Utilisateur", "lastName": "Inconnu"}

    info = response.get("personalInfo", {})
    first_name = info.get("firstName")
    last_name = info.get("lastName")

    return {"firstName": first_name, "lastName": last_name}


def get_catalog_infos(client, catalog_id: str) -> dict[str, str]:
    """
    Récupère le storeId et le channelId pour un catalogue spécifique.
    :param client: Le client BeezUP.
    :param catalog_id: Le catalogId du catalogue.
    :return: Un dictionnaire avec le storeId et le channelId de la boutique BeezUP.
    """
    endpoint = f"v2/user/channelCatalogs/{catalog_id}"
    response = client.get(endpoint)

    if not response:
        raise RuntimeError("Impossible d'extraire les données du catalogue.")

    store_id = response.get("storeId")
    channel_id = response.get("channelId")

    if not store_id or not channel_id:
        raise ValueError("Données du catalogue incomplètes (IDs manquants).")

    return {"storeId": store_id, "channelId": channel_id}


def get_store_name(client, store_id: str) -> str:
    """
    Récupère le nom de la boutique BeezUP associée à un store_id.
    :param client: Le client BeezUP.
    :param store_id: Le storeId de la boutique BeezUP.
    :return: Un string avec le beezUPStoreName de la boutique BeezUP.
    """
    endpoint = "v2/user/marketplaces/channelCatalogs/"
    params = {"storeId": store_id}
    response = client.get(endpoint, params=params)

    if response is None:
        return "Boutique inconnue"

    catalogs = response.get("marketplaceChannelCatalogs", [])
    store_name = next((c.get("beezUPStoreName") for c in catalogs if c.get("beezUPStoreName")), None)

    if not store_name:
        return "Boutique sans nom"

    return store_name


@st.cache_data(ttl=1800, show_spinner=False)
def get_catalog_categories(_client, store_id: str) -> Optional[pd.DataFrame]:
    """
    Récupère les catégories présentes dans le catalogue vendeur et le nombre de produits dans chacune d'entre elles.
    :param client: Le client BeezUP.
    :param store_id: Le storeId de la boutique BeezUP.
    :return: Un dataframe avec les catégories présentes dans le catalogue de la boutique et le nombre de produits
    (colonnes : Catalog Category, Total Product Count).
    """
    endpoint = f"v2/user/catalogs/{store_id}/categories"
    response = _client.get(endpoint)

    if response is None:
        raise ConnectionError("Impossible d'extraire les catégories du catalogue.")

    categories = response.get("categories", [])
    data = []
    for c in categories:
        category_id = c.get("categoryId")
        path = c.get("categoryPath", [])
        if path and category_id:
            data.append({
                "Catalog Category": path[-1],  # On conserve uniquement le niveau 3.
                "Total Product Count": c.get("totalProductCount", 0)
            })

    if not data:
        raise ValueError("Aucune catégorie trouvée dans le catalogue vendeur.")

    df = pd.DataFrame(data)
    df["Total Product Count"] = pd.to_numeric(df["Total Product Count"], errors="coerce").fillna(0).astype(int)
    logger.info(f"Catégories catalogue extraites : {len(df)} catégories trouvées.")

    return df


@st.cache_data(ttl=1800, show_spinner=False)
def get_category_mapping(_client, catalog_id: str) -> Optional[pd.DataFrame]:
    """
    Récupère le mapping catégorie entre le catalogue vendeur et le canal de vente.
    :param _client: Le client BeezUP.
    :param catalog_id: Le catalogId de la boutique BeezUP.
    :return: Un dataframe avec le mapping catégories (colonnes : Catalog Category, Channel Category Path).
    """
    endpoint = f"v2/user/channelCatalogs/{catalog_id}/categories"
    response = _client.get(endpoint)

    if response is None:
        raise ConnectionError("Impossible d'extraire le mapping catégories.")

    mapping = response.get("channelCatalogCategoryConfigurations", [])

    if not mapping:
        raise ValueError("Aucune catégorie mappée.")

    df = pd.DataFrame([
        {
            "Catalog Category": m.get("catalogCategoryPath", [])[-1],  # On conserve uniquement le niveau 3.
            "Channel Category Path": " > ".join(m.get("channelCategoryPath", []))
        }
        for m in mapping
    ])
    logger.info(f"Mapping catégories extrait : {len(df)} catégories mappées.")

    return df


@st.cache_data(ttl=1800, show_spinner=False)
def get_channel_attributes(_client, channel_id: str) -> Optional[pd.DataFrame]:
    """
    Récupère la liste des attributs spécifiques au canal de vente.
    :param _client: Le client BeezUP.
    :param channel_id: Le channelId de la boutique BeezUP.
    :return: Un dataframe avec les attributs spécifiques au canal de vente
    (colonnes : Source, Channel Attribute Id, Attribute Name, Attribute Description, Status, Type Value).
    """
    endpoint = f"v2/user/channels/{channel_id}/columns"
    response = _client.post(endpoint, json=[])

    if response is None:
        raise ConnectionError("Impossible d'extraire les attributs spécifiques au canal de vente.")

    data = []
    for item in response:
        config = item.get("configuration", {})
        attr_id = item.get("channelColumnId")
        status = config.get("columnImportance")
        data.append({
            "Source": "Channel",
            "Channel Attribute Id": attr_id,
            "Attribute Name": item.get("channelColumnName"),
            "Attribute Code": item.get("channelColumnCode"),
            "Attribute Description": item.get("channelColumnDescription"),
            "Status": status,
            "Type Value": config.get("columnDataType")
        })

    df = pd.DataFrame(data)
    logger.info(f"Attributs spécifiques au canal de vente extraits : {len(df)} attributs trouvés.")

    return df


def get_channel_category_attributes(client, catalog_id: str, selected_channel_path: str) -> Optional[pd.DataFrame]:
    """
    Récupère les attributs spécifiques à la catégorie.
    :param client: Le client BeezUP.
    :param catalog_id: Le catalogId de la boutique BeezUP.
    :param selected_channel_path: La catégorie choisie depuis le dataframe get_available_categories.
    :return: Un dataframe avec les attributs spécifiques à la catégorie sélectionnée (colonnes : Source,
    Channel Full Category Path, Channel Attribute Id, Attribute Name, Attribute Description, Status, Type Value,
    Attribute Value List Code, Default Value, Catalog Column Id, Catalogue Column Name).
    """
    endpoint = f"v2/user/channelCatalogs/{catalog_id}/attributes"
    response = client.get(endpoint)

    if response is None:
        raise ConnectionError("Impossible d'extraire les attributs spécifiques à la catégorie.")

    data = []
    for category in response:
        channel_full_category_path = category.get("channelFullCategoryPath")
        if channel_full_category_path == "Cross Categories" or channel_full_category_path == selected_channel_path:
            attributes = category.get("attributes", [])
            for attribute in attributes:
                data.append({
                    "Source": "Cross Categories" if channel_full_category_path == "Cross Categories" else "Category",
                    "Channel Category Path": channel_full_category_path,
                    "Channel Attribute Id": attribute.get("channelAttributeId"),
                    "Attribute Name": attribute.get("attributeName"),
                    "Attribute Code": attribute.get("attributeCode"),
                    "Attribute Description": attribute.get("attributeDescription"),
                    "Status": attribute.get("status"),
                    "Type Value": attribute.get("typeValue"),
                    "Attribute Value List Code": attribute.get("attributeValueListCode"),
                    "Default Value": attribute.get("defaultValue")
                })

    df = pd.DataFrame(data)
    logger.info(f"Attributs spécifiques à la catégorie extraits : {len(df)} attributs trouvés.")

    return df


@st.cache_data(ttl=1800, show_spinner=False)
def get_column_mapping_dict(_client, catalog_id: str) -> dict:
    """
    Récupère le mapping attributs entre le catalogue vendeur et le canal de vente.
    :param client: Le client BeezUP.
    :param catalog_id: Le catalogId de la boutique BeezUP.
    :return: Un dictionnaire avec le mapping attributs (colonnes : Channel Attribute Id, Catalog Column Id).
    """
    endpoint = f"v2/user/channelCatalogs/{catalog_id}"
    response = _client.get(endpoint)

    if not response:
        raise ConnectionError("Impossible d'extraire le mapping attributs.")

    mapping_list = response.get("columnMappings", [])

    if not mapping_list:
        return {}

    data = {
        c.get("channelColumnId").lower().strip(): c.get("catalogColumnId").lower().strip()
        if c.get("catalogColumnId") else None
        for c in mapping_list
        if c.get("channelColumnId")
    }

    mapped_count = len([v for v in data.values() if v is not None])
    logger.info(f"Mapping attributs extrait : {mapped_count}/{len(data)} attributs.")

    return data


def get_product_ids(_client, catalog_id: str, selected_channel_path: str, skus_list: list = None) -> Optional[
    pd.DataFrame]:
    """
    Récupère les "productId" et les "productSku" présents dans le catalogue vendeur.
    """
    endpoint = f"v2/user/channelCatalogs/{catalog_id}/products"
    data = []
    page_number = 1

    while True:
        payload = {
            "pageNumber": page_number,
            "pageSize": 1000,
            "criteria": {
                "logic": "cumulative",
                "exist": True,
                "uncategorized": False,
                "excluded": False,
                "disabled": False
            },
            "channelCategoryFilter": {"categoryPath": selected_channel_path.split(" > ")}
        }
        if skus_list:
            payload["productFilters"] = {"channelSkus": skus_list}

        response = _client.post(endpoint, json=payload)

        if response is None:
            raise ConnectionError("Impossible d'extraire les produits du catalogue.")

        product_infos = response.get("productInfos", [])
        for product in product_infos:
            data.append({
                "Product Id": product.get("productId"),
                "sku": product.get("productSku")
            })

        pagination_result = response.get("paginationResult", {})
        page_count = pagination_result.get("pageCount", 1)

        if page_number >= page_count:
            break
        page_number += 1

    if not data:
        raise ValueError("Aucun produit présent dans le catalogue pour cette catégorie.")

    df = pd.DataFrame(data)
    logger.info(f"{len(df)} produits extraits.")

    return df


@st.cache_data(ttl=1800, show_spinner=False)
def download_export_file(catalog_id: str) -> Optional[pd.DataFrame]:
    """
    Télécharge le fichier exporté vers le canal de vente.
    """
    url = f"https://export2.beezup.com/v2/user/channelCatalogs/export/X/X/{catalog_id}"
    # Note : On utilise requests directement ici, car domaine différent
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    if not response.content:
        raise ValueError("Le fichier d'export BeezUP est vide.")

    encoding = response.encoding if response.encoding else response.apparent_encoding
    csv_text = response.content.decode(encoding or "utf-8")
    df = pd.read_csv(StringIO(csv_text), sep=None, engine="python")
    logger.info(f"Export téléchargé : {len(df)} produits trouvés.")

    return df


def get_attribute_values(client, catalog_id: str, attribute_id: str) -> list[dict] | None:
    """
    Récupère la liste de valeurs bornées pour un attribut.
    :param client: Le client BeezUP.
    :param catalog_id: Le catalogId de la boutique BeezUP.
    :param attribute_id: Le Channel Attribute Id de l'attribut.
    :return: Une liste de dictionnaire avec le code attribut et son nom (label).
    """
    endpoint = f"v2/user/channelCatalogs/{catalog_id}/attributes/{attribute_id}/mapping"
    response = client.get(endpoint)

    if response is None:
        raise ConnectionError("Impossible d'extraire les listes de valeurs bornées.")

    logger.info("Listes de valeurs bornées extraites.")

    return response.get("channelAttributeValuesWithMapping", [])


def build_dropdown_dataframe(client, catalog_id: str, df_selected_attributes: pd.DataFrame) -> pd.DataFrame:
    """
    Récupère les listes de valeurs bornées des attributs concernés et les stocke dans un dataframe.
    :param client: Le client BeezUP.
    :param catalog_id: Le catalogId de la boutique BeezUP.
    :param df_selected_attributes: Le dataframe des attributs sélectionnés.
    :return: Un dataframe avec toutes les listes de valeurs bornées.
    """
    # On filtre pour ne garder que les attributs qui ont une liste de valeurs
    df_list_attributes = df_selected_attributes[df_selected_attributes["Attribute Value List Code"].notnull()]
    value_dict = {}

    for _, row in df_list_attributes.iterrows():
        attribute_id = row["Channel Attribute Id"]
        column_name = row["Label"]

        # On appelle la fonction locale
        mapped_values = get_attribute_values(client, catalog_id, attribute_id)

        if mapped_values:
            # On stocke la liste formatée "code | label".
            value_dict[column_name] = [
                f"{v.get('code')} | {v.get('label')}"
                for v in mapped_values
                if v.get("code") is not None
            ]

    # On transforme le dictionnaire en DataFrame (Series gère les longueurs différentes).
    df = pd.DataFrame({k: pd.Series(v, dtype="string") for k, v in value_dict.items()})
    logger.info("Dataframe des listes de valeurs bornées généré.")

    return df

