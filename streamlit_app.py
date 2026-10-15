
import streamlit as st
from snowflake.snowpark.context import get_active_session
from snowflake.snowpark.functions import col

# Connect to Snowflake
session = get_active_session()

# App title
st.title("MY PARENTS NEW HEALTHY DINNER")
st.write("Choose your favorite fruits for a healthy dinner smoothie!")

# Customer name
name_on_order = st.text_input("Name on order:")

st.write("The name on your order will be:", name_on_order)

# Read fruit options from Snowflake
my_dataframe = session.table(
    "SMOOTHIES.PUBLIC.FRUIT_OPTIONS"
).select(col("FRUIT_NAME"))

st.dataframe(my_dataframe, use_container_width=True)

# Get fruit names for the multiselect
fruit_rows = my_dataframe.collect()
fruit_options = [row["FRUIT_NAME"] for row in fruit_rows]

ingredients_list = st.multiselect(
    "Choose up to 5 ingredients:",
    options=fruit_options,
    max_selections=5
)

# Submit order
if st.button("Submit Order"):
    if not name_on_order.strip():
        st.warning("Please enter your name.")
    elif not ingredients_list:
        st.warning("Please select at least one ingredient.")
    else:
        ingredients_string = " ".join(ingredients_list)

        # Insert order into Snowflake
        my_insert_stmt = """
            INSERT INTO SMOOTHIES.PUBLIC.ORDERS
                (INGREDIENTS, NAME)
            VALUES (?, ?)
        """

        session.sql(
            my_insert_stmt,
            params=[ingredients_string, name_on_order.strip()]
        ).collect()

        st.success("Your order has been placed!", icon="✅")
