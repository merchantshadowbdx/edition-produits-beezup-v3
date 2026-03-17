import pandas as pd
from xlsxwriter.utility import xl_col_to_name


def _get_excel_formats(workbook):
    """Définit et retourne les formats utilisés pour le template."""
    return {
        "fixed": workbook.add_format(
            {"bg_color": "#EAEDF6", "font_color": "#313A4A", "bold": True, "align": "left", "valign": "vcenter"}),
        "required": workbook.add_format(
            {"bg_color": "#F2BBC0", "font_color": "#66141B", "bold": True, "align": "left", "valign": "vcenter"}),
        "recommended": workbook.add_format(
            {"bg_color": "#FFEBDB", "font_color": "#8B4711", "bold": True, "align": "left", "valign": "vcenter"}),
        "optional": workbook.add_format(
            {"bg_color": "#DBFAEC", "font_color": "#0B5E41", "bold": True, "align": "left", "valign": "vcenter"})
    }


def _apply_template_styling(ws, df_template, df_datainfo, df_list_of_values, formats):
    """Applique le masquage, les couleurs de header et les dropdowns sur l'onglet Template."""
    attr_info_map = {row["Label"]: str(row.get("Status", "")).strip().lower() for _, row in df_datainfo.iterrows()}

    fixed_cols = ["Product Id", "Catalog Id", "Channel Category Path", "SKU"]
    cols_to_hide = ["Product Id", "Catalog Id"]

    for col_idx, col_name in enumerate(df_template.columns):
        # --- 1. Gestion de la colonne (Largeur et Masquage) ---
        is_hidden = col_name in cols_to_hide
        width = 20 if col_name in fixed_cols else 25

        # Note : On utilise None pour le format pour éviter l'AttributeError sur le dictionnaire d'options
        ws.set_column(col_idx, col_idx, width, None, {"hidden": True} if is_hidden else None)

        # --- 2. Gestion du Header (Couleurs) ---
        if col_name in fixed_cols:
            ws.write(0, col_idx, col_name, formats["fixed"])
        elif col_name in attr_info_map:
            status = attr_info_map[col_name]
            if status in formats:
                ws.write(0, col_idx, col_name, formats[status])

            # --- 3. Menus déroulants ---
            if col_name in df_list_of_values.columns:
                col_values = df_list_of_values[col_name].dropna()
                if not col_values.empty:
                    list_col_letter = xl_col_to_name(df_list_of_values.columns.get_loc(col_name))
                    dropdown_range = f"ListOfValues!${list_col_letter}$2:${list_col_letter}${len(col_values) + 1}"

                    ws.data_validation(1, col_idx, len(df_template) + 100, col_idx, {
                        "validate": "list",
                        "source": dropdown_range,
                        "error_title": "Valeur non valide",
                        "error_message": "Veuillez choisir une valeur dans la liste."
                    })


def build_and_export_excel(df_template, df_datainfo, df_list_of_values, output_file):
    """Exporte et met en forme le fichier Excel final."""

    def add_styled_table(ws, df, name, style):
        # Sécurité : On s'assure que le tableau contient au moins une ligne de données
        last_row = max(len(df), 1)
        ws.add_table(0, 0, last_row, len(df.columns) - 1, {
            "name": name,
            "style": style,
            "columns": [{"header": col} for col in df.columns]
        })

    engine_kwargs = {"options": {"nan_inf_to_errors": True}}

    with pd.ExcelWriter(output_file, engine="xlsxwriter", engine_kwargs=engine_kwargs) as writer:
        # Étape 1 : Écriture des données
        df_template.to_excel(writer, sheet_name="Template", index=False)
        df_datainfo.to_excel(writer, sheet_name="DataInfo", index=False)
        df_list_of_values.to_excel(writer, sheet_name="ListOfValues", index=False)

        # Étape 2 : Initialisation
        workbook = writer.book
        ws_template = writer.sheets["Template"]
        formats = _get_excel_formats(workbook)

        # Ajout des tableaux natifs Excel
        add_styled_table(ws_template, df_template, "TemplateTable", "Table Style Medium 2")
        add_styled_table(writer.sheets["DataInfo"], df_datainfo, "DataInfoTable", "Table Style Medium 3")
        add_styled_table(writer.sheets["ListOfValues"], df_list_of_values, "ListOfValuesTable", "Table Style Medium 5")

        # Étape 3 : Mise en forme métier
        ws_template.freeze_panes(1, 0)
        _apply_template_styling(ws_template, df_template, df_datainfo, df_list_of_values, formats)
