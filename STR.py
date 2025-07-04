# Lead Manager App with Multi-User Roles (Admin/User)
import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import plotly.express as px
import math

# ---------------------- CONFIG ----------------------
st.set_page_config(layout="wide", page_title="Lead Manager")

SOURCE_TYPES = [
    "Personal Contacts", "INC Clients in Bcrisp", "OCRA in Bcrisp", "Bankers",
    "Conference /Webinors", "Industry Database", "Social Media",
    "Client Reference", "Board/wellwishers"
]

# ---------------------- STYLING ----------------------
st.markdown("""
    <style>
    html, body, [class*="css"] {
        font-family: 'Segoe UI', sans-serif;
    }
    .stApp {
        background: linear-gradient(135deg, #f5f9ff, #ffffff);
    }
    .stButton>button {
        background-color: #1d4ed8;
        color: white;
    }
    .stSidebar {
        background-color: #e0f2fe;
    }
    .sticky-header {
        position: sticky;
        top: 0;
        z-index: 999;
        background: white;
        padding-top: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------- AUTH ----------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(password, hashed):
    return hash_password(password) == hashed

def init_user_db():
    with sqlite3.connect("leads.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                role TEXT
            )
        """)
        users = conn.execute("SELECT username FROM Users").fetchall()
        usernames = [u[0] for u in users]
        if 'admin' not in usernames:
            conn.execute("INSERT INTO Users (username, password, role) VALUES (?, ?, ?)",
                         ("admin", hash_password("admin123"), "admin"))
        if 'user' not in usernames:
            conn.execute("INSERT INTO Users (username, password, role) VALUES (?, ?, ?)",
                         ("user", hash_password("user123"), "user"))
        conn.commit()

def login():
    st.title("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        with sqlite3.connect("leads.db") as conn:
            user = pd.read_sql("SELECT * FROM Users WHERE username=?", conn, params=(username,))
            if not user.empty and check_password(password, user['password'][0]):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = user['role'][0]
                st.rerun()
            else:
                st.error("❌ Invalid credentials.")

def logout():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.rerun()

# ---------------------- INIT ----------------------
init_user_db()
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if not st.session_state.logged_in:
    login()
    st.stop()

# ---------------------- HEADER ----------------------
st.markdown("""
<div class="sticky-header">
    <h1 style="color:#1e3a8a;">📘 Lead Manager</h1>
    <p style='text-align:right;'>👋 Logged in as: <b>{}</b> ({})</p>
</div>
""".format(st.session_state.username, st.session_state.role), unsafe_allow_html=True)

if st.button("🔓 Logout"):
    logout()

# ---------------------- SIDEBAR ----------------------
with st.sidebar:
    show_filters = st.checkbox("📂 Show Filters", value=True)
    if show_filters:
        st.markdown("### 🔍 Filters")
        try:
            with sqlite3.connect("leads.db") as conn:
                conn.execute("""CREATE TABLE IF NOT EXISTS LeadSources (
                    OrganizationName TEXT, ContactPersonName TEXT, ContactDetails TEXT,
                    Address TEXT, Email TEXT, SourceType TEXT)""")
                org_names = [row[0] for row in conn.execute("SELECT DISTINCT OrganizationName FROM LeadSources")]
        except:
            org_names = []

        st.selectbox("Organization", ["All"] + org_names, key="org_name")
        st.multiselect("Source Type", SOURCE_TYPES, key="source_types")
        st.text_input("Search Org/Contact", key="search")
        if st.button("Reset Filters"):
            st.session_state.org_name = "All"
            st.session_state.source_types = []
            st.session_state.search = ""

    # Only Admins can add leads
    if st.session_state.role == 'admin':
        if st.checkbox("➕ Add New Lead"):
            with st.form("add_lead_form"):
                org = st.text_input("Organization")
                contact = st.text_input("Contact Person")
                phone = st.text_input("Contact Details")
                email = st.text_input("Email")
                addr = st.text_area("Address")
                source = st.selectbox("Source Type", SOURCE_TYPES)
                if st.form_submit_button("✅ Submit Lead") and org:
                    with sqlite3.connect("leads.db") as conn:
                        conn.execute("""
                            INSERT INTO LeadSources 
                            (OrganizationName, ContactPersonName, ContactDetails, Address, Email, SourceType)
                            VALUES (?, ?, ?, ?, ?, ?)""", (org, contact, phone, addr, email, source))
                        st.success(f"Lead '{org}' added successfully!")

    # Admin: Create user
    if st.session_state.role == 'admin':
        with st.expander("➕ Create New User"):
            new_user = st.text_input("New Username")
            new_pass = st.text_input("Password", type="password")
            new_role = st.selectbox("Role", ["user", "admin"])
            if st.button("Create User"):
                try:
                    with sqlite3.connect("leads.db") as conn:
                        conn.execute("INSERT INTO Users (username, password, role) VALUES (?, ?, ?)",
                                     (new_user, hash_password(new_pass), new_role))
                        st.success("User created!")
                except sqlite3.IntegrityError:
                    st.warning("Username already exists.")

# ---------------------- FILTER DATA ----------------------
filters, params = [], []
if st.session_state.get("org_name") and st.session_state.org_name != "All":
    filters.append("OrganizationName = ?")
    params.append(st.session_state.org_name)
if st.session_state.get("source_types"):
    filters.append(f"SourceType IN ({','.join(['?']*len(st.session_state.source_types))})")
    params.extend(st.session_state.source_types)
where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

# ---------------------- LOAD DATA ----------------------
try:
    with sqlite3.connect("leads.db") as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM LeadSources {where_clause}", params).fetchone()[0]
        df = pd.read_sql(f"""
            SELECT OrganizationName, ContactPersonName, ContactDetails, Address, Email, SourceType
            FROM LeadSources {where_clause}
        """, conn, params=params)
except Exception as e:
    st.error(f"DB Error: {e}")
    df = pd.DataFrame()

if st.session_state.get("search"):
    q = st.session_state.search.lower()
    df = df[df["OrganizationName"].str.lower().str.contains(q) | df["ContactPersonName"].str.lower().str.contains(q)]

# ---------------------- DISPLAY DATA ----------------------
if not df.empty:
    df.index += 1
    st.markdown(f"<p>🎯 <b>{len(df)}</b> filtered lead(s)</p>", unsafe_allow_html=True)
    st.dataframe(df, use_container_width=True)

    # Dashboard
    st.markdown("### 📊 Lead Dashboard Analytics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Leads", len(df))
    col2.metric("Unique Orgs", df.OrganizationName.nunique())
    col3.metric("Top Source", df.SourceType.value_counts().idxmax())

    with st.expander("📘 Source Type Pie"):
        st.plotly_chart(px.pie(df, names="SourceType", title="Source Distribution", hole=0.4), use_container_width=True)

    with st.expander("🏢 Leads by Org"):
        org_counts = df.OrganizationName.value_counts().reset_index()
        org_counts.columns = ["Org", "Count"]
        st.plotly_chart(px.bar(org_counts, x="Org", y="Count", text="Count"), use_container_width=True)
else:
    st.warning("No data found.")

# ---------------------- ADMIN USER MANAGEMENT ----------------------
if st.session_state.role == 'admin':
    st.markdown("## 👥 Manage Users")
    with sqlite3.connect("leads.db") as conn:
        users_df = pd.read_sql("SELECT id, username, role FROM Users", conn)
    st.dataframe(users_df)
    del_user = st.text_input("Enter username to delete")
    if st.button("Delete User") and del_user != "admin":
        with sqlite3.connect("leads.db") as conn:
            conn.execute("DELETE FROM Users WHERE username = ? AND username != 'admin'", (del_user,))
            st.success(f"User '{del_user}' deleted.")
