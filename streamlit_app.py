
import streamlit as st
import requests
import pandas as pd
from urllib.parse import quote

# Page configuration
st.set_page_config(
    page_title="Customize Your Smoothie",
    page_icon="🥤",
    layout="centered"
)

# Connect to Snowflake
@st.cache_resource
def get_session():
    conn = st.connection("snowflake")
    return conn.session()


# App heading
st.title("🥤 Customize Your Smoothie! 🥤")
st.write("Choose the fruits you want in your custom Smoothie!")

# Customer name
name_on_order = st.text_input("Name on Smoothie:")
st.write("The name on your Smoothie will be:", name_on_order)


# Load fruit options from Snowflake
try:
    session = get_session()

    fruit_rows = (
        session.table("SMOOTHIES.PUBLIC.FRUIT_OPTIONS")
        .select("FRUIT_NAME", "SEARCH_ON")
        .collect()
    )

    # Create a Pandas DataFrame
    pd_df = pd.DataFrame(
        [row.as_dict() for row in fruit_rows]
    )

    # Check that the required columns exist
    if not {"FRUIT_NAME", "SEARCH_ON"}.issubset(pd_df.columns):
        st.error("FRUIT_NAME or SEARCH_ON column is missing.")
        st.stop()

    # Values displayed in the multiselect
    fruit_options = pd_df["FRUIT_NAME"].tolist()

except Exception as e:
    st.error(
        "Could not load fruit options. "
        "Check your Snowflake connection and confirm "
        "that SEARCH_ON exists in FRUIT_OPTIONS."
    )
    st.exception(e)
    st.stop()


# Fruit selection
ingredients_list = st.multiselect(
    "Choose up to 5 ingredients:",
    options=fruit_options,
    max_selections=5,
    placeholder="Choose an option"
)


# Display ingredients and SmoothieFroot nutrition information
if ingredients_list:

    ingredients_string = " ".join(ingredients_list)

    for fruit_chosen in ingredients_list:

        # Find the API search value for the selected fruit
        try:
            search_on = pd_df.loc[
                pd_df["FRUIT_NAME"] == fruit_chosen,
                "SEARCH_ON"
            ].iloc[0]

            st.write(
                "The search value for ",
                fruit_chosen,
                " is ",
                search_on,
                "."
            )

        except (IndexError, KeyError):
            st.warning(
                f"No SEARCH_ON value found for {fruit_chosen}."
            )
            continue

        # Check that SEARCH_ON has a value
        if pd.isna(search_on) or not str(search_on).strip():
            st.warning(
                f"SEARCH_ON is empty for {fruit_chosen}. "
                "Update this value in Snowflake."
            )
            continue

        # Get nutrition information from the API
        try:
            api_fruit = quote(str(search_on).strip().lower(), safe="")

            api_url = (
                "https://my.smoothiefroot.com/api/fruit/"
                + api_fruit
            )

            smoothiefroot_response = requests.get(
                api_url,
                timeout=10
            )

            smoothiefroot_response.raise_for_status()

            smoothie_data = smoothiefroot_response.json()

            # Display nutrition information
            st.subheader(
                f"🍓 SmoothieFroot Nutrition Information: "
                f"{fruit_chosen}"
            )

            st.dataframe(
                data=smoothie_data,
                use_container_width=True
            )

        except requests.RequestException as e:
            st.warning(
                f"Unable to retrieve nutrition information "
                f"for {fruit_chosen}."
            )
            st.caption(str(e))

        except ValueError:
            st.warning(
                "The API did not return valid JSON data."
            )


# Submit order
if st.button("Submit Order", type="primary"):

    if not name_on_order.strip():
        st.warning("Please enter your name.")

    elif not ingredients_list:
        st.warning("Please choose at least one fruit.")

    else:
        ingredients_string = " ".join(ingredients_list)

        try:
            insert_sql = """
                INSERT INTO SMOOTHIES.PUBLIC.ORDERS (INGREDIENTS)
                VALUES (?)
            """

            session.sql(
                insert_sql,
                params=[ingredients_string]
            ).collect()

            st.success(
                f"Thank you, {name_on_order.strip()}! "
                "Your smoothie order has been placed! 🥤"
            )

            st.write(
                "Selected ingredients:",
                ", ".join(ingredients_list)
            )

        except Exception as e:
            st.error("Unable to place your order.")
            st.exception(e)
