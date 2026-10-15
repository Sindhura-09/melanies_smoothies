
import streamlit as st
from snowflake.snowpark.context import get_active_session
from snowflake.snowpark.functions import col

# Connect to the active Snowflake session
session = get_active_session()

# Page configuration
st.set_page_config(
    page_title="Customize Your Smoothie",
    page_icon="🥤",
    layout="centered"
)

# App heading
st.title("🥤 Customize Your Smoothie! 🥤")
st.write("Choose the fruits you want in your custom Smoothie!")

# Customer name
name_on_order = st.text_input("Name on Smoothie:")

st.write("The name on your Smoothie will be:", name_on_order)

# Load fruit options from Snowflake
fruit_df = (
    session.table("SMOOTHIES.PUBLIC.FRUIT_OPTIONS")
    .select(col("FRUIT_NAME"))
)

# Convert Snowflake results to a Python list
fruit_rows = fruit_df.collect()
fruit_options = [row["FRUIT_NAME"] for row in fruit_rows]

# Fruit selection
ingredients_list = st.multiselect(
    "Choose up to 5 ingredients:",
    options=fruit_options,
    max_selections=5,
    placeholder="Choose an option"
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
            # Insert the selected ingredients into the Orders table
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

        except Exception as e:
            st.error(f"Unable to place your order: {e}")
 
