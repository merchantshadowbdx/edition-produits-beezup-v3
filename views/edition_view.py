import streamlit as st


def render():

    # Style CSS
    st.html("<style>.st-key-edition_container { box-shadow: 0px 2px 20px rgba(0, 0, 0, 0.5); }</style>")

    with st.container(border=True, key="edition_container"):
        st.subheader("✏️️ Intégration des données")

        st.write("")
        on = st.toggle("Intégrer plusieurs templates à la fois")
        st.write("")

        if on:
            uploaded_files = st.file_uploader(
                "Sélectionnez le dossier dans lequel se trouvent les templates",
                accept_multiple_files="directory",
                type="xlsx"
            )
        else:
            uploaded_file = st.file_uploader(
                "Sélectionnez le template",
                type="xlsx"
            )
        st.write("")
        if st.button(label="Valider la sélection", type="primary", width=200, icon=":material/check:"):
            pass
