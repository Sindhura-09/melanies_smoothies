import streamlit as st
import requests

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
        .select("FRUIT_NAME")
        .collect()
    )

    fruit_options = [row["FRUIT_NAME"] for row in fruit_rows]

except Exception as e:
    st.error(
        "Could not load fruit options. "
        "Please check your Snowflake connection and credentials."
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
    ingredients_string = ""

    for fruit_chosen in ingredients_list:
        ingredients_string += fruit_chosen + " "

        # Get nutrition information from the API
        try:
            smoothiefroot_response = requests.get(
                "https://my.smoothiefroot.com/api/fruit/watermelon",
                timeout=10
            )

            smoothiefroot_response.raise_for_status()

            smoothie_data = smoothiefroot_response.json()

            # Display API response as a DataFrame
            st.subheader(
                f"🍉 SmoothieFroot Nutrition Information: {fruit_chosen}"
            )

            st_df = st.dataframe(
                data=smoothie_data,
                use_container_width=True
            )

        except requests.RequestException:
            st.warning(
                f"Unable to retrieve nutrition information for "
                f"{fruit_chosen}."
            )

        except ValueError:
            st.warning("The API did not return valid JSON data.")


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
