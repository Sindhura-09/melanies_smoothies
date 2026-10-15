
import streamlit as st

# Page configuration must come first
st.set_page_config(
    page_title="Customize Your Smoothie",
    page_icon="🥤",
    layout="centered"
)

# Connect to Snowflake on Streamlit Community Cloud
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

# Connect and load fruit options
try:
    session = get_session()

    fruit_rows = (
        session.table("SMOOTHIES.PUBLIC.FRUIT_OPTIONS")
        .select("FRUIT_NAME")
        .collect()
    )

    fruit_options = [row["FRUIT_NAME"] for row in fruit_rows]

except Exception as e:
    st.error("Could not load fruit options. Check your Snowflake connection.")
    st.exception(e)
    st.stop()

# Fruit dropdown
ingredients_list = st.multiselect(
    "Choose up to 5 ingredients:",
    options=fruit_options,
    max_selections=5,
    placeholder="Choose an option"
)

# Submit button
if st.button("Submit Order"):
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

            st.success("Your smoothie order has been placed! 🥤")

        except Exception as e:
            st.error("Unable to place your order.")
            st.exception(e)
