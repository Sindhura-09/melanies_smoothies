
import streamlit as st
import requests
import pandas as pd
from urllib.parse import quote

st.set_page_config(
    page_title="Customize Your Smoothie",
    page_icon="🥤",
    layout="centered"
)

@st.cache_resource
def get_session():
    return st.connection("snowflake").session()


st.title("🥤 Customize Your Smoothie! 🥤")
st.write("Choose the fruits you want in your custom Smoothie!")

name_on_order = st.text_input("Name on Smoothie:")
st.write("The name on your Smoothie will be:", name_on_order)

order_filled = st.checkbox("Mark this order as FILLED", value=False)

# Load fruit names and API search values
try:
    session = get_session()

    fruit_rows = (
        session.table("SMOOTHIES.PUBLIC.FRUIT_OPTIONS")
        .select("FRUIT_NAME", "SEARCH_ON")
        .collect()
    )

    pd_df = pd.DataFrame([row.as_dict() for row in fruit_rows])

    fruit_options = pd_df["FRUIT_NAME"].tolist()

except Exception as e:
    st.error("Unable to load fruit options from Snowflake.")
    st.exception(e)
    st.stop()


# Fruit multiselect
ingredients_list = st.multiselect(
    "Choose up to 5 ingredients:",
    options=fruit_options,
    max_selections=5,
    placeholder="Choose an option"
)


# Look up SEARCH_ON and call the nutrition API
for fruit_chosen in ingredients_list:
    matching_rows = pd_df.loc[
        pd_df["FRUIT_NAME"] == fruit_chosen,
        "SEARCH_ON"
    ]

    if matching_rows.empty:
        st.warning(f"No SEARCH_ON value for {fruit_chosen}.")
        continue

    search_on = matching_rows.iloc[0]

    if pd.isna(search_on) or not str(search_on).strip():
        st.warning(f"SEARCH_ON is empty for {fruit_chosen}.")
        continue

    st.write(f"The search value for {fruit_chosen} is {search_on}.")

    api_fruit = quote(str(search_on).strip().lower(), safe="")
    api_url = f"https://my.smoothiefroot.com/api/fruit/{api_fruit}"

    try:
        response = requests.get(api_url, timeout=15)
        response.raise_for_status()
        data = response.json()

        st.subheader(f"🍓 Nutrition Information: {fruit_chosen}")

        if isinstance(data, dict):
            st.dataframe(
                pd.json_normalize(data),
                use_container_width=True
            )
        elif isinstance(data, list):
            st.dataframe(
                pd.DataFrame(data),
                use_container_width=True
            )
        else:
            st.write(data)

    except requests.RequestException as e:
        st.warning(f"API request failed for {fruit_chosen}.")
        st.caption(str(e))

    except ValueError:
        st.warning("The API did not return valid JSON.")


# Submit the order
if st.button("Submit Order", type="primary"):

    if not name_on_order.strip():
        st.warning("Please enter your name.")

    elif not ingredients_list:
        st.warning("Please select at least one fruit.")

    else:
        # Keep selected ingredients in their selected order
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

            st.write("Ingredients:", ingredients_string)
            st.write(
                "Status:",
                "FILLED" if order_filled else "NOT FILLED"
            )

        except Exception as e:
            st.error("Unable to place the order.")
            st.exception(e)
