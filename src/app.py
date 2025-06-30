import streamlit as st
from db import session
from models import MenuItem, Order, Table, Inventory, Feedback, User, Reservation, OrderItems, ArchivedOrder, \
    ArchivedOrderItems
from datetime import date
from sqlalchemy import func
from datetime import datetime
from sqlalchemy.exc import IntegrityError

st.set_page_config(page_title="Khata Admin Dashboard", layout="wide")

#---------------------Functions------------------

def menu_management():
    st.header("📋 Menu Management")
    col1, col2 = st.columns([1.2, 2])

    with col1:
        with st.expander("➕ Add New Menu Item", expanded=True):
            with st.form("add_menu_form"):
                name = st.text_input("🍽 Item Name", placeholder="e.g. Chicken Biryani")
                category = st.selectbox("📂 Category", ["Starter", "Main Course", "Drink", "Dessert"])
                price = st.number_input("💵 Price (PKR)", min_value=0.0, format="%.2f")
                availability = st.radio("✅ Available?", ["Yes", "No"], horizontal=True)
                ingredients = st.text_area("🧂 Ingredients", placeholder="e.g. Chicken, Rice, Spices")
                submit_button = st.form_submit_button("Add Item")

                if submit_button:
                    item = MenuItem(name=name, category=category, price=price,
                                    availability=(availability == "Yes"), ingredients=ingredients)
                    session.add(item)
                    session.commit()
                    st.success(f"✅ “{name}” added to the menu!")
                    st.rerun()

    with col2:
        st.subheader("📦 Existing Menu Items")
        items = session.query(MenuItem).order_by(MenuItem.name).all()
        if not items:
            st.info("No menu items found.")
        else:
            for item in items:
                with st.container():
                    row = st.columns([4, 1, 1])
                    with row[0]:
                        st.markdown(f"{item.name}** ({item.category})  \n💰 PKR {item.price:.2f}  \n📋 {item.ingredients}")
                        st.markdown(f"🔘 {'Available' if item.availability else 'Unavailable'}")
                    with row[1]:
                        if st.button("🗑 Delete", key=f"delete_{item.item_id}", use_container_width=True):
                            session.delete(item)
                            session.commit()
                            st.warning(f"🗑 “{item.name}” deleted!")
                            st.rerun()

def place_order():
    st.header("🧾 Place Your Order")

    # Fetch only available menu items
    items = session.query(MenuItem).filter_by(availability=True).all()
    if not items:
        st.info("Sorry, no menu items are currently available.")
        return

    display_names = [f"{item.name} (PKR{item.price:.2f})" for item in items]

    selected = st.multiselect(
        "Select items to order",
        display_names,
        key="cust_select"
    )

    # Quantities and total
    quantities = {}
    total = 0.0
    if selected:
        st.markdown("**Specify quantities for each selected item:**")
        for disp in selected:
            idx = display_names.index(disp)
            item = items[idx]
            qty = st.number_input(
                f"{item.name} quantity",
                min_value=1,
                key=f"qty_{item.item_id}"
            )
            quantities[item.item_id] = qty
            total += float(item.price) * qty

    st.markdown(f"### Total Bill: PKR{total:.2f}")

    # Table number (optional, or required if used)
    table_id = st.number_input("Table Number", min_value=1, key="cust_table")

    if st.button("Place Order", key="place_order_button"):
        if not selected:
            st.error("Please select at least one item.")
            return

        # Here, we assume the user is already logged in, and their ID is available in the session
        # For this example, we'll assume the user has already been created or logged in previously.
        # Replace 'user_id' with the actual ID based on the login system
        user_id = st.session_state.get("user_id")  # should have user_id in the session if the user is logged in

        if not user_id:
            st.error("User not logged in. Please log in first.")
            return

        # Create the order
        order = Order(
            user_id=user_id,
            table_id=table_id,
            total_amount=total,
            status="Pending",
            payment_status="Unpaid"
        )
        session.add(order)
        session.commit()

        # Now add all the OrderItems
        for item_id, qty in quantities.items():
            if qty > 0:
                # Modern API: fetch by primary key
                menu_item = session.get(MenuItem, item_id)
                if menu_item:
                    order_item = OrderItems(
                        order_id=order.order_id,
                        item_id=menu_item.item_id,
                        quantity=qty,
                        total_price=menu_item.price * qty
                    )
                    session.add(order_item)

        # Now commit all the OrderItems in one go
        session.commit()

        # Show summary
        st.success(f"✅ Order #{order.order_id} placed!")
        st.markdown("**Your Order:**")
        for item_id, qty in quantities.items():
            item = next(i for i in items if i.item_id == item_id)
            st.markdown(f"- {item.name} x {qty} = PKR{item.price * qty:.2f}")
        st.markdown(f"**Total:** PKR{total:.2f}")


def track_orders():
    st.header("📋 Track Orders")

    orders = session.query(Order).order_by(Order.order_time.desc()).all()
    if not orders:
        st.info("No orders found.")
        return

    for o in orders:
        st.markdown(f"### 🧾 Order #{o.order_id}")
        st.markdown(
            f"**👤 Customer:** {o.user.name}  \n"
            f"**🍽️ Table Number:** {o.table_id}  \n"
            f"**⏰ Time:** {o.order_time.strftime('%Y-%m-%d %H:%M:%S')}  \n"
            f"**💳 Payment Status:** {o.payment_status}  \n"
            f"**📦 Order Status:** *{o.status}*  \n"
            f"**💰 Total Amount:** PKR{o.total_amount:.2f}"
        )

        # Show ordered items
        st.markdown("**🧾 Items Ordered:**")
        for item in o.order_items:
            menu_item = session.query(MenuItem).filter_by(item_id=item.item_id).first()
            if menu_item:
                st.markdown(f"- {menu_item.name} x {item.quantity} = PKR{menu_item.price * item.quantity:.2f}")

        st.divider()


# 3. UPDATE ORDER STATUS
def update_order_status():
    st.header("🔄 Update Order Status")

    # Pull only orders that are not yet Completed
    orders = session.query(Order).filter(Order.status != "Completed").all()

    if not orders:
        st.info("All orders are completed!")
        return

    valid_statuses = ["Pending", "In Progress", "Completed"]

    for o in orders:
        cols = st.columns([3, 2, 1])
        with cols[0]:
            st.markdown(f"*Order #{o.order_id}* | Table {o.table_id} | Current: *{o.status}*")
        with cols[1]:
            new_status = st.selectbox(
                f"New status for #{o.order_id}",
                valid_statuses,
                index=valid_statuses.index(o.status),
                key=f"status_{o.order_id}"
            )
        with cols[2]:
            if st.button(f"Update", key=f"btn_{o.order_id}"):
                o.status = new_status
                session.commit()
                st.success(f"Order #{o.order_id} → {new_status}")
                st.rerun()


def admin_order_management():
    st.header("🛒 Order Management")

    # Fetch all orders
    orders = session.query(Order).all()

    for order in orders:
        with st.expander(f"Order {order.order_id} Details"):
            st.write(f"**Order ID**: {order.order_id}")
            st.write(f"**User**: {order.user.name}")
            st.write(f"**Table**: {order.table_id}")
            st.write(f"**Status**: {order.status}")
            st.write(f"**Total Amount**: PKR {order.total_amount:.2f}")
            st.write(f"**Payment Status**: {order.payment_status}")
            st.write(f"**Order Time**: {order.order_time}")

            # Buttons for actions
            col1, col2 = st.columns(2)

            with col1:
                if st.button("Save to Archive", key=f"archive_{order.order_id}"):
                    order.status = "Archived"  # Mark order as archived
                    session.commit()           # Commit status change to trigger
                    session.delete(order)      # Then delete the order
                    session.commit()
                    st.success(f"Order {order.order_id} archived successfully!")

            with col2:
                if st.button("View Order", key=f"view_{order.order_id}"):
                    st.write("**Order Items:**")
                    order_items = session.query(OrderItems).filter(OrderItems.order_id == order.order_id).all()
                    for item in order_items:
                        st.write(f"- Item: {item.menu_item.name}, Quantity: {item.quantity}, Total Price: PKR {item.total_price:.2f}")


def view_archived_orders():
    st.header("📦 Archived Orders")

    # Fetch all archived orders
    archived_orders = session.query(ArchivedOrder).all()

    if not archived_orders:
        st.info("No archived orders found.")
        return

    for archived in archived_orders:
        with st.expander(f"Archived Order {archived.order_id} Details"):
            st.write(f"**Order ID**: {archived.order_id}")
            st.write(f"**User**: {archived.user.name if archived.user else 'N/A'}")
            st.write(f"**Table ID**: {archived.table_id}")
            st.write(f"**Status**: {archived.status}")
            st.write(f"**Total Amount**: PKR {archived.total_amount:.2f}")
            st.write(f"**Payment Status**: {archived.payment_status}")
            st.write(f"**Order Time**: {archived.order_time}")
            st.write(f"**Archived At**: {archived.archive_time}")

            st.write("**Order Items:**")
            items = session.query(ArchivedOrderItems).filter_by(order_id=archived.order_id).all()
            if items:
                for item in items:
                    menu_item = session.query(MenuItem).filter_by(item_id=item.menu_item_id).first()
                    item_name = menu_item.name if menu_item else "Unknown Item"
                    st.write(f"- {item_name}: Quantity {item.quantity}, Total PKR {item.total_price:.2f}")
            else:
                st.write("No items found.")

            # Confirmation checkbox
            confirm_key = f"confirm_delete_{archived.order_id}"
            delete_key = f"delete_button_{archived.order_id}"
            confirm = st.checkbox(f"Confirm permanent delete of Order {archived.order_id}", key=confirm_key)

            if confirm:
                if st.button("🗑️ Permanently Delete", key=delete_key):
                    try:
                        session.query(ArchivedOrderItems).filter_by(order_id=archived.order_id).delete()
                        session.query(ArchivedOrder).filter_by(order_id=archived.order_id).delete()
                        session.commit()
                        st.success(f"Archived Order {archived.order_id} permanently deleted.")
                        st.rerun()
                    except Exception as e:
                        session.rollback()
                        st.error(f"Failed to delete archived order {archived.order_id}. Error: {e}")
            else:
                st.warning("⚠️ Please confirm the checkbox to enable deletion.")

def add_reservation():
    st.header("➕ Add New Reservation")

    # Fetch only Customer-role users
    customers = session.query(User).filter_by(role="Customer").all()
    if not customers:
        st.info("No customers found. Please add customers first.")
        return

    # Build a map of customer names → user_ids
    customer_map = {cust.name: cust.user_id for cust in customers}

    # Get list of all tables for validation
    tables = {t.table_id: t for t in session.query(Table).all()}
    if not tables:
        st.info("No tables defined. Please set up tables first.")
        return

    with st.form("add_reservation_form"):
        selected_name = st.selectbox("Customer Name", list(customer_map.keys()))
        table_id       = st.number_input("Table ID", min_value=1, format="%d")
        res_date       = st.date_input("Reservation Date")
        res_time       = st.time_input("Reservation Time")
        status         = st.selectbox("Status", ["Confirmed", "Cancelled", "No-Show"])
        submitted      = st.form_submit_button("Add Reservation")

    if submitted:
        # Check table exists
        table = tables.get(table_id)
        if not table:
            st.error(f"❌ Table {table_id} does not exist.")
            return

        # Check if table is available
        if not table.availability:
            st.error(f"❌ Table {table_id} is already reserved or occupied.")
            return

        # Combine date & time into a single datetime
        reservation_datetime = datetime.combine(res_date, res_time)

        # Create reservation
        new_res = Reservation(
            user_id=customer_map[selected_name],
            table_id=table_id,
            reservation_time=reservation_datetime,
            status=status
        )
        session.add(new_res)

        # Mark table unavailable
        table.availability = False
        session.commit()

        st.success(f"✅ Reservation #{new_res.reservation_id} added for {selected_name} at Table {table_id}!")
        st.rerun()



# 2. VIEW ALL RESERVATIONS
def view_reservations():
    st.header("📋 All Table Reservations")
    reservations = session.query(Reservation).order_by(Reservation.reservation_time.desc()).all()
    if not reservations:
        st.info("No reservations found.")
        return

    for r in reservations:
        st.markdown(
            f"• *Reservation #{r.reservation_id}*  \n"
            f"User ID: {r.user_id}  \n"
            f"Table: {r.table_id}  \n"
            f"Time: {r.reservation_time}  \n"
            f"Status: {r.status}"
        )
        st.divider()


# 3. TODAY'S BOOKINGS
def todays_bookings():
    st.header("📅 Today's Reservations")
    today = date.today()
    today_res = session.query(Reservation) \
        .filter(func.date(Reservation.reservation_time) == today) \
        .order_by(Reservation.reservation_time) \
        .all()

    if not today_res:
        st.info("No bookings for today.")
        return

    for r in today_res:
        st.markdown(
            f"• *Reservation #{r.reservation_id}*  \n"
            f"User ID: {r.user_id}  \n"
            f"Table: {r.table_id}  \n"
            f"Time: {r.reservation_time.time()}  \n"
            f"Status: {r.status}"
        )
        st.divider()

def inventory():
    st.header("📦 Add Inventory Item")
    with st.form("add_inventory"):
        name = st.text_input("Item Name")
        qty = st.number_input("Quantity", min_value=1)
        expiry = st.date_input("Expiry Date", value=date.today())
        supplier = st.number_input("Supplier ID", min_value=1)
        if st.form_submit_button("Add Item"):
            stock = Inventory(name=name, quantity=qty, expiry_date=expiry, supplier_id=supplier)
            session.add(stock)
            session.commit()
            st.success("Inventory item added!")

    st.subheader("📦 Current Inventory")
    inventory = session.query(Inventory).all()
    for i in inventory:
        st.write(f"{i.name} | Qty: {i.quantity} | Expires: {i.expiry_date}")

def feedback():
    st.header("⭐ Submit Feedback")

    # Get user_id from session
    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("You must be logged in to submit feedback.")
        return

    # Fetch orders placed by the logged-in user
    user_orders = session.query(Order).filter(Order.user_id == user_id).all()
    if not user_orders:
        st.info("You haven't placed any orders yet.")
        return

    order_options = {f"Order #{o.order_id} - ₹{o.total_amount} on {o.order_time.strftime('%Y-%m-%d %H:%M')}": o.order_id for o in user_orders}

    with st.form("add_feedback"):
        order_label = st.selectbox("Select Order", list(order_options.keys()))
        selected_order_id = order_options[order_label]
        rating = st.slider("Rating", 1, 5)
        comments = st.text_area("Comments")

        if st.form_submit_button("Submit Feedback"):
            fb = Feedback(
                user_id=user_id,
                order_id=selected_order_id,
                rating=rating,
                comments=comments
            )
            session.add(fb)
            session.commit()
            st.success("Thanks for your feedback!")

    st.subheader("🗣 Customer Feedback")

    feedbacks = session.query(Feedback).order_by(Feedback.feedback_id.desc()).all()

    if not feedbacks:
        st.info("No feedback has been submitted yet.")
    else:
        for f in feedbacks:
            user = session.query(User).filter(User.user_id == f.user_id).first()
            order = session.query(Order).filter(Order.order_id == f.order_id).first()

            st.markdown("---")
            st.markdown(f"**👤 Customer:** {user.name if user else 'Unknown'}")
            st.markdown(
                f"**🧾 Order ID:** #{f.order_id}  •  💵 Total: PKR{order.total_amount:.2f}  •  🕒 {order.order_time.strftime('%Y-%m-%d %H:%M') if order else 'N/A'}")
            st.markdown(f"**⭐ Rating:** {f.rating}/5")
            st.markdown(f"**💬 Comments:**\n> {f.comments}")


def sales_report():
    st.header("📈 Sales & Performance Dashboard")

    # --- Manual Refresh Button ---
    if st.button("🔄 Refresh Data"):
        st.rerun()

    # --- Clear All Sales Data Workflow ---
    if "confirm_clear_sales" not in st.session_state:
        st.session_state.confirm_clear_sales = False

    if not st.session_state.confirm_clear_sales:
        if st.button("🗑️ Clear All Sales Data"):
            st.session_state.confirm_clear_sales = True
    else:
        st.warning("⚠️ This will delete ALL orders and line items permanently!")
        if st.button("✅ Confirm Clear All Sales Data"):
            # Delete all order items first
            session.query(OrderItems).delete(synchronize_session=False)
            # Then delete all orders
            session.query(Order).delete(synchronize_session=False)
            session.commit()
            st.success("All sales data has been cleared.")
            # Reset confirmation flag and rerun to show zero metrics
            st.session_state.confirm_clear_sales = False
            st.rerun()
        if st.button("❌ Cancel"):
            st.session_state.confirm_clear_sales = False

    # Ensure we fetch fresh counts
    session.expire_all()

    # --- Overall Metrics ---
    total_sales = session.query(func.sum(Order.total_amount)).scalar() or 0
    total_orders = session.query(func.count(Order.order_id)).scalar() or 0
    st.metric("Total Revenue", f"PKR {total_sales:.2f}")
    st.metric("Total Orders", total_orders)

    # --- Top‐Selling Items ---
    st.subheader("🥇 Top-Selling Menu Items")
    try:
        top_items = (
            session.query(MenuItem.name, func.sum(OrderItems.quantity).label("total_sold"))
            .join(OrderItems, MenuItem.item_id == OrderItems.item_id)
            .group_by(MenuItem.name)
            .order_by(func.sum(OrderItems.quantity).desc())
            .limit(10)
            .all()
        )

        if top_items:
            for name, count in top_items:
                st.write(f"• {name}: {int(count)} sold")
        else:
            st.info("No orders placed yet.")
    except Exception as e:
        st.warning(f"⚠️ Error loading top items: {e}")


def user_management():
    st.subheader("👥 User Management")

    # Track which user (if any) is awaiting confirmation
    if "pending_delete_user" not in st.session_state:
        st.session_state.pending_delete_user = None

    users = session.query(User).all()
    for user in users:
        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(
                f"**🆔 ID:** {user.user_id}  \n"
                f"**👤 Name:** {user.name}  \n"
                f"**🔐 Role:** {user.role}  \n"
                f"**📦 Orders:** {len(user.orders)}"
            )
        with col2:
            # When you click delete, set that user as pending
            if st.button("🗑️", key=f"del_user_{user.user_id}"):
                st.session_state.pending_delete_user = user.user_id

    # Outside the loop: if someone clicked delete, ask confirmation
    pid = st.session_state.pending_delete_user
    if pid is not None:
        user = session.get(User, pid)
        if user:
            st.warning(f"⚠️ Are you sure you want to delete **{user.name}** and all their data?")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Yes, delete", key="confirm_delete"):
                    session.delete(user)
                    session.commit()
                    st.success(f"User **{user.name}** and all their data deleted.")
                    # reset and refresh
                    st.session_state.pending_delete_user = None
                    st.rerun()
            with c2:
                if st.button("❌ Cancel", key="cancel_delete"):
                    st.session_state.pending_delete_user = None
        else:
            # user disappeared, reset
            st.session_state.pending_delete_user = None

    # Finally, the add-user form
    with st.expander("➕ Add New User"):
        with st.form("add_user"):
            name = st.text_input("User Name")
            role = st.selectbox("Role", ["Admin", "Staff", "Receptionist", "Customer"])
            submitted = st.form_submit_button("Add User")
            if submitted:
                new_user = User(name=name, role=role)
                session.add(new_user)
                session.commit()
                st.success(f"User **{name}** added successfully!")
                st.rerun()

def sign_up():
    """Render and handle the sign-up form for new customers."""
    st.header("🆕 Customer Sign Up")
    with st.form("signup_form", clear_on_submit=True):
        name = st.text_input("👤 Name")
        email = st.text_input("📧 Email")
        contact = st.text_input("📱 Contact Number")
        password = st.text_input("🔒 Password", type="password")
        submitted = st.form_submit_button("Sign Up")
        if submitted:
            if not all([name, email, contact, password]):
                st.error("All fields are required.")
            else:
                new_user = User(
                    name=name,
                    role="Customer",
                    contact=contact,
                    email=email,
                    password=password
                )
                session.add(new_user)
                try:
                    session.commit()
                    st.success("Account created! Please log in below.")
                    st.session_state.show_signup = False
                except IntegrityError:
                    session.rollback()
                    st.error("That email is already registered.")
    st.markdown("---")
    if st.button("← Back to Login"):
        st.session_state.show_signup = False

def log_in():
    """Render and handle the login form."""
    st.header("🔐 Customer Login")
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("📧 Email", placeholder="you@example.com")
        password = st.text_input("🔒 Password", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Login")
        if submitted:
            user = session.query(User).filter_by(email=email, password=password).first()
            if user:
                st.session_state.logged_in = True
                st.session_state.user_role = user.role
                st.session_state.user_name = user.name
                st.session_state.user_id = user.user_id
                st.success(f"Welcome, {user.name} ({user.role})!")
                st.rerun()
            else:
                st.error("❌ Invalid email or password")
    st.markdown("---")
    if st.button("Create an account"):
        st.session_state.show_signup = True


# -------------------- LOGIN --------------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.user_name = ""
    st.session_state.user_id = None
    st.session_state.show_signup = False

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center;'>🍽 Khata Management System</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: grey;'>Please sign in or sign up to continue</p>", unsafe_allow_html=True)
    if st.session_state.show_signup:
        sign_up()
    else:
        log_in()
    st.stop()

col1, col2 = st.columns([10, 1])
with col2:
    if st.button("Sign Out", key="signout"):
        st.session_state.clear()
        st.rerun()


# -------------------- SIDEBAR --------------------
role = st.session_state.user_role
name = st.session_state.user_name

st.sidebar.markdown(f"### 👤 {name} ({role})")

# Define role-specific menus
if role == "Admin":
    menu_options = ["Track Orders", "Order Management", "Archived Orders", "Menu Management", "Reservations", "Sales Report", "Inventory", "User Management", "Feedback"]
elif role == "Receptionist":
    menu_options = ["Place Order", "Track Orders", "Add Reservation", "View Reservations", "Today's Bookings"]
elif role == "Staff":
    menu_options = ["Track Orders", "Update Order Status", "View Reservations"]
elif role == "Customer":
    menu_options = ["Place Order", "Track My Orders", "Give Feedback"]
else:
    menu_options = []

menu = st.sidebar.radio("📁 Select Section", menu_options)
st.markdown(f"### Hello, {name} ({role})")

# -------------------- ADMIN PANEL --------------------
if role == "Admin":
    if menu == "Track Orders":
        st.header("🧾 All Orders")
        track_orders()

    elif menu == "Order Management":
        admin_order_management()

    elif menu == "Archived Orders":
        view_archived_orders()

    elif menu == "Menu Management":
        # Calls your modular menu management function
        menu_management()

    elif menu == "Reservations":
        # Calls your modular menu management function
        view_reservations()

    elif menu == "Inventory":
        # Calls your modular inventory function
        inventory()

    elif menu == "User Management":
        # Calls your modular user management function
        user_management()

    elif menu == "Sales Report":
        # Calls your modular sales report function
        sales_report()

    elif menu == "Feedback":
        # Calls your modular feedback function
        feedback()


# -------------------- RECEPTIONIST PANEL --------------------
elif role == "Receptionist":
    if menu == "Place Order":
        place_order()

    elif menu == "Track Orders":
        track_orders()

    elif menu == "Add Reservation":
        add_reservation()

    elif menu == "View Reservations":
        view_reservations()

    elif menu == "Today's Bookings":
        todays_bookings()

# -------------------- STAFF PANEL --------------------
elif role == "Staff":
    if menu == "Track Orders":
        track_orders()

    elif menu == "Update Order Status":
        update_order_status()

    elif menu == "View Reservations":
        view_reservations()

# -------------------- CUSTOMER PANEL --------------------
elif role == "Customer":
    if menu == "Place Order":
        # Uses your place_order() function, which already reads session_state.user_id
        place_order()

    elif menu == "Track My Orders":
        # A variant of track_orders() that filters by current user
        track_orders()

    elif menu == "Give Feedback":
        # Uses your customer_feedback() function
        feedback()
