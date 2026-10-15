
import streamlit as st
import pandas as pd
import requests
from urllib.parse import quote

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------
st.set_page_config(
    page_title="Melanie's Smoothie Shop",
    page_icon="🥤",
    layout="wide"
)

st.title("🥤 Melanie's Smoothie Shop")
st.subheader("Create your own smoothie!")
st.write("Select your favourite fruits and place your order.")

# --------------------------------------------------
# SNOWFLAKE CONNECTION
# --------------------------------------------------
try:
    conn = st.connection("snowflake")
    session = conn.session()
except Exception as e:
    st.error("Could not connect to Snowflake.")
    st.code(str(e))
    st.stop()

# --------------------------------------------------
# LOAD FRUIT OPTIONS
# --------------------------------------------------
try:
    fruit_df = session.sql("""
        SELECT FRUIT_NAME, SEARCH_ON
        FROM SMOOTHIES.PUBLIC.FRUIT_OPTIONS
        ORDER BY FRUIT_NAME
    """).to_pandas()

    # Remove rows that do not contain a fruit name.
    fruit_df = fruit_df.dropna(subset=["FRUIT_NAME"])
    fruit_df["FRUIT_NAME"] = fruit_df["FRUIT_NAME"].astype(str)

except Exception as e:
    st.error("Could not load the fruit options from Snowflake.")
    st.code(str(e))
    st.stop()

if fruit_df.empty:
    st.warning("No fruits are available. Check FRUIT_OPTIONS in Snowflake.")
    st.stop()

# --------------------------------------------------
# CUSTOMER ORDER FORM
# --------------------------------------------------
st.divider()
st.header("🍓 Build Your Smoothie")

customer_name = st.text_input(
    "Enter your name",
    placeholder="Enter your name here"
)

fruit_options = fruit_df["FRUIT_NAME"].tolist()

selected_fruits = st.multiselect(
    "Choose your fruits",
    options=fruit_options,
    help="Choose one or more fruits for your smoothie."
)

# --------------------------------------------------
# CHECK FRUIT API
# --------------------------------------------------
if st.button("🔍 Check Selected Fruits", use_container_width=True):

    if not selected_fruits:
        st.warning("Please select at least one fruit.")
    else:
        for fruit in selected_fruits:

            matching_rows = fruit_df[
                fruit_df["FRUIT_NAME"] == fruit
            ]

            if matching_rows.empty:
                st.warning(f"No API mapping found for {fruit}.")
                continue

            search_value = matching_rows.iloc[0]["SEARCH_ON"]

            if pd.isna(search_value) or not str(search_value).strip():
                st.warning(f"SEARCH_ON is empty for {fruit}.")
                continue

            api_fruit = str(search_value).strip().lower()
            api_url = (
                "https://my.smoothiefroot.com/api/fruit/"
                + quote(api_fruit, safe="")
            )

            try:
                response = requests.get(api_url, timeout=15)

                if response.status_code == 200:
                    st.success(f"✅ {fruit} is available in the fruit API.")
                    try:
                        st.json(response.json())
                    except ValueError:
                        st.write(response.text)

                elif response.status_code == 404:
                    st.error(
                        f"{fruit} was not found in the fruit API. "
                        f"Check its SEARCH_ON value in Snowflake."
                    )
                else:
                    st.warning(
                        f"API returned status {response.status_code} "
                        f"for {fruit}."
                    )

            except requests.RequestException as e:
                st.error(f"Could not check {fruit}: {e}")

# --------------------------------------------------
# PLACE ORDER
# --------------------------------------------------
st.divider()
st.header("🛒 Place Your Order")

if st.button("✅ Place Smoothie Order", use_container_width=True):

    if not customer_name.strip():
        st.warning("Please enter your name.")
    elif not selected_fruits:
        st.warning("Please select at least one fruit.")
    else:
        ingredients = ", ".join(selected_fruits)

        try:
            # Use Snowpark DataFrame insertion to safely handle
            # names and ingredient text.
            order_data = session.create_dataframe(
                [(customer_name.strip(), ingredients, False)],
                schema=[
                    "NAME_ON_ORDER",
                    "INGREDIENTS",
                    "ORDER_FILLED"
                ]
            )

            order_data.write.save_as_table(
                "SMOOTHIES.PUBLIC.ORDERS",
                mode="append",
                column_order="name"
            )

            st.success(
                f"🎉 Order placed successfully for {customer_name.strip()}!"
            )
            st.write("**Selected fruits:**", ingredients)
            st.info("Your order has been marked as not yet filled.")

        except Exception as e:
            st.error("Unable to save your order to Snowflake.")
            st.code(str(e))

# --------------------------------------------------
# DISPLAY ORDER HISTORY
# --------------------------------------------------
st.divider()
st.header("📋 Order History")

try:
    orders_df = session.sql("""
        SELECT
            NAME_ON_ORDER,
            INGREDIENTS,
            ORDER_FILLED
        FROM SMOOTHIES.PUBLIC.ORDERS
    """).to_pandas()

    if not orders_df.empty:
        # Display a readable status column.
        orders_df["STATUS"] = orders_df["ORDER_FILLED"].apply(
            lambda value: "✅ Filled" if value is True else "⏳ Pending"
        )

        st.dataframe(
            orders_df,
            use_container_width=True,
            hide_index=True
        )

        st.caption(f"Total orders: {len(orders_df)}")

        filled_count = (
            orders_df["ORDER_FILLED"].fillna(False).astype(bool).sum()
        )
        pending_count = len(orders_df) - filled_count

        col1, col2 = st.columns(2)

        with col1:
            st.metric("✅ Filled Orders", int(filled_count))

        with col2:
            st.metric("⏳ Pending Orders", int(pending_count))

    else:
        st.info("No orders have been placed yet.")

except Exception as e:
    st.error("Could not load the order history.")
    st.code(str(e))

# --------------------------------------------------
# FOOTER
# --------------------------------------------------
st.divider()
st.caption("Melanie's Smoothie Shop | Powered by Streamlit and Snowflake")
