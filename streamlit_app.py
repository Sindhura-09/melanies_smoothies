
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

# Order status
order_filled = st.checkbox("Mark this order as FILLED", value=False)


# Load fruit options from Snowflake
try:
    session = get_session()

    fruit_rows = (
        session.table("SMOOTHIES.PUBLIC.FRUIT_OPTIONS")
        .select("FRUIT_NAME", "SEARCH_ON")
        .collect()
    )

    # Create Pandas DataFrame
    pd_df = pd.DataFrame(
        [row.as_dict() for row in fruit_rows]
    )

    if not {"FRUIT_NAME", "SEARCH_ON"}.issubset(pd_df.columns):
        st.error("FRUIT_NAME or SEARCH_ON column is missing.")
        st.stop()

    fruit_options = pd_df["FRUIT_NAME"].tolist()

except Exception as e:
    st.error("Could not load fruit options from Snowflake.")
    st.exception(e)
    st.stop()


# Fruit selection
ingredients_list = st.multiselect(
    "Choose up to 5 ingredients:",
    options=fruit_options,
    max_selections=5,
    placeholder="Choose an option"
)


# Display API nutrition information using SEARCH_ON
if ingredients_list:

    for fruit_chosen in ingredients_list:

        # Find the API search value for the selected fruit
        matching_rows = pd_df.loc[
            pd_df["FRUIT_NAME"] == fruit_chosen,
            "SEARCH_ON"
        ]

        if matching_rows.empty:
            st.warning(f"No SEARCH_ON value found for {fruit_chosen}.")
            continue

        search_on = matching_rows.iloc[0]

        st.write(
            f"The search value for {fruit_chosen} is {search_on}."
        )

        if pd.isna(search_on) or not str(search_on).strip():
            st.warning(
                f"SEARCH_ON is empty for {fruit_chosen}. "
                "Update it in Snowflake."
            )
            continue

        try:
            api_fruit = quote(
                str(search_on).strip().lower(),
                safe=""
            )

            api_url = (
                "https://my.smoothiefroot.com/api/fruit/"
                + api_fruit
            )

            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            smoothie_data = response.json()

            st.subheader(
                f"🍓 Nutrition Information: {fruit_chosen}"
            )

            if isinstance(smoothie_data, (dict, list)):
                st.dataframe(
                    pd.json_normalize(smoothie_data)
                    if isinstance(smoothie_data, dict)
                    else pd.DataFrame(smoothie_data),
                    use_container_width=True
                )
            else:
                st.write(smoothie_data)

        except requests.RequestException as e:
            st.warning(
                f"Unable to retrieve nutrition information "
                f"for {fruit_chosen}."
            )
            st.caption(str(e))

        except ValueError:
            st.warning("The API did not return valid JSON data.")


# Submit order
if st.button("Submit Order", type="primary"):

    if not name_on_order.strip():
        st.warning("Please enter your name.")

    elif not ingredients_list:
        st.warning("Please choose at least one fruit.")

    else:
        # Preserve the exact order of selected fruits
        ingredients_string = " ".join(ingredients_list)

        try:
            insert_sql = """
                INSERT INTO SMOOTHIES.PUBLIC.ORDERS
                    (NAME_ON_ORDER, INGREDIENTS, ORDER_FILLED)
                VALUES (?, ?, ?)
            """

            session.sql(
                insert_sql,
                params=[
                    name_on_order.strip(),
                    ingredients_string,
                    order_filled
                ]
            ).collect()

            st.success(
                f"Thank you, {name_on_order.strip()}! "
                "Your smoothie order has been placed! 🥤"
            )

            st.write("Selected ingredients:", ingredients_string)
            st.write(
                "Order status:",
                "FILLED" if order_filled else "NOT FILLED"
            )

        except Exception as e:
            st.error(
                "Unable to place the order. "
                "Check the column names in your ORDERS table."
            )
            st.exception(e)
