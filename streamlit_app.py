
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
st.write("Create smoothie orders and manage their status.")

# --------------------------------------------------
# SNOWFLAKE CONNECTION
# --------------------------------------------------
try:
    session = st.connection("snowflake").session()
except Exception as e:
    st.error("Could not connect to Snowflake.")
    st.code(str(e))
    st.stop()

ORDERS_TABLE = "SMOOTHIES.PUBLIC.ORDERS"
FRUIT_TABLE = "SMOOTHIES.PUBLIC.FRUIT_OPTIONS"


# --------------------------------------------------
# HELPER: SAVE OR UPDATE AN ORDER
# --------------------------------------------------
def save_workshop_order(name, ingredients, filled):
    # Check whether this exact order already exists.
    result = session.sql(
        f"""
        SELECT COUNT(*) AS CNT
        FROM {ORDERS_TABLE}
        WHERE NAME_ON_ORDER = ?
          AND INGREDIENTS = ?
        """,
        params=[name, ingredients]
    ).collect()

    count = result[0]["CNT"]

    if count > 0:
        # Update the existing order instead of duplicating it.
        session.sql(
            f"""
            UPDATE {ORDERS_TABLE}
            SET ORDER_FILLED = ?
            WHERE NAME_ON_ORDER = ?
              AND INGREDIENTS = ?
            """,
            params=[filled, name, ingredients]
        ).collect()
        return "updated"

    # Insert a new order using the three confirmed table columns.
    order_df = session.create_dataframe(
        [(name, ingredients, filled)],
        schema=[
            "NAME_ON_ORDER",
            "INGREDIENTS",
            "ORDER_FILLED"
        ]
    )

    order_df.write.save_as_table(
        ORDERS_TABLE,
        mode="append",
        column_order="name"
    )

    return "created"


# --------------------------------------------------
# WORKSHOP REQUIRED ORDERS
# --------------------------------------------------
st.header("📝 Required Workshop Orders")

st.write(
    "Click the button below to create the three required orders "
    "with the correct fruit order and filled status."
)

workshop_orders = [
    (
        "Kevin",
        "Apples, Lime, Ximenia",
        False
    ),
    (
        "Divya",
        "Dragon Fruit, Guava, Figs, Jackfruit, Blueberries",
        True
    ),
    (
        "Xi",
        "Vanilla Fruit, Nectarine",
        True
    )
]

with st.expander("View the three required orders", expanded=True):
    st.dataframe(
        pd.DataFrame(
            workshop_orders,
            columns=[
                "NAME_ON_ORDER",
                "INGREDIENTS",
                "ORDER_FILLED"
            ]
        ),
        use_container_width=True,
        hide_index=True
    )

if st.button(
    "✅ Create 3 Workshop Orders",
    type="primary",
    use_container_width=True
):
    try:
        for name, ingredients, filled in workshop_orders:
            action = save_workshop_order(
                name,
                ingredients,
                filled
            )

            st.write(
                f"{name}: order {action}; "
                f"ORDER_FILLED = {filled}"
            )

        st.success("All three workshop orders have been saved.")
        st.rerun()

    except Exception as e:
        st.error("Could not save the workshop orders.")
        st.code(str(e))


# --------------------------------------------------
# LOAD FRUIT OPTIONS
# --------------------------------------------------
st.divider()
st.header("🍓 Create a Custom Order")

try:
    fruit_df = session.sql(
        f"""
        SELECT FRUIT_NAME, SEARCH_ON
        FROM {FRUIT_TABLE}
        ORDER BY FRUIT_NAME
        """
    ).to_pandas()

    fruit_df = fruit_df.dropna(subset=["FRUIT_NAME"])
    fruit_df["FRUIT_NAME"] = fruit_df["FRUIT_NAME"].astype(str)

except Exception as e:
    st.error("Could not load fruit options.")
    st.code(str(e))
    fruit_df = pd.DataFrame(columns=["FRUIT_NAME", "SEARCH_ON"])

if not fruit_df.empty:
    customer_name = st.text_input(
        "Customer name",
        key="custom_customer"
    )

    selected_fruits = st.multiselect(
        "Choose fruits in the order you want them saved",
        options=fruit_df["FRUIT_NAME"].tolist(),
        key="custom_fruits"
    )

    order_filled = st.checkbox(
        "Mark this order as filled",
        value=False
    )

    if st.button("Place Custom Order", use_container_width=True):
        if not customer_name.strip():
            st.warning("Please enter the customer's name.")
        elif not selected_fruits:
            st.warning("Please select at least one fruit.")
        else:
            ingredients = ", ".join(selected_fruits)

            try:
                save_workshop_order(
                    customer_name.strip(),
                    ingredients,
                    order_filled
                )

                st.success(
                    f"Order saved for {customer_name.strip()}!"
                )
                st.write("**Selected fruits:**", ingredients)
                st.write(
                    "**Status:**",
                    "Filled" if order_filled else "Pending"
                )
                st.rerun()

            except Exception as e:
                st.error("Could not save the custom order.")
                st.code(str(e))

    # --------------------------------------------------
    # OPTIONAL FRUIT API CHECK
    # --------------------------------------------------
    st.subheader("🔍 Check Fruit API")

    api_fruit = st.selectbox(
        "Choose a fruit to check",
        options=fruit_df["FRUIT_NAME"].tolist()
    )

    if st.button("Check Fruit Availability"):
        row = fruit_df[
            fruit_df["FRUIT_NAME"] == api_fruit
        ].iloc[0]

        search_value = row["SEARCH_ON"]

        if pd.isna(search_value) or not str(search_value).strip():
            st.warning(f"SEARCH_ON is missing for {api_fruit}.")
        else:
            url = (
                "https://my.smoothiefroot.com/api/fruit/"
                + quote(str(search_value).strip().lower(), safe="")
            )

            try:
                response = requests.get(url, timeout=15)

                if response.status_code == 200:
                    st.success(f"{api_fruit} is available in the API.")
                    try:
                        st.json(response.json())
                    except ValueError:
                        st.write(response.text)
                elif response.status_code == 404:
                    st.error(
                        f"{api_fruit} was not found. "
                        "Check its SEARCH_ON mapping in Snowflake."
                    )
                else:
                    st.warning(
                        f"API returned status {response.status_code}."
                    )

            except requests.RequestException as e:
                st.error(f"API request failed: {e}")


# --------------------------------------------------
# ORDER HISTORY
# --------------------------------------------------
st.divider()
st.header("📋 Order History")

if st.button("🔄 Refresh Order History"):
    st.rerun()

try:
    orders_df = session.sql(
        f"""
        SELECT
            NAME_ON_ORDER,
            INGREDIENTS,
            ORDER_FILLED
        FROM {ORDERS_TABLE}
        ORDER BY NAME_ON_ORDER
        """
    ).to_pandas()

    if orders_df.empty:
        st.info("No orders found.")
    else:
        orders_df["STATUS"] = orders_df["ORDER_FILLED"].apply(
            lambda value: (
                "Filled" if value is True else "Pending"
            )
        )

        st.dataframe(
            orders_df,
            use_container_width=True,
            hide_index=True
        )

        total = len(orders_df)
        filled_count = (
            orders_df["ORDER_FILLED"]
            .fillna(False)
            .astype(bool)
            .sum()
        )
        pending_count = total - int(filled_count)

        col1, col2, col3 = st.columns(3)

        col1.metric("Total Orders", total)
        col2.metric("Filled Orders", int(filled_count))
        col3.metric("Pending Orders", pending_count)

except Exception as e:
    st.error("Could not load order history.")
    st.code(str(e))


# --------------------------------------------------
# FOOTER
# --------------------------------------------------
st.divider()
st.caption("Melanie's Smoothie Shop | Powered by Snowflake and Streamlit")
