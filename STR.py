import streamlit as st
import sqlite3
import pandas as pd
import math
import plotly.express as px
import hashlib

# ---------------------- AUTH SECTION ----------------------

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
        result = conn.execute("SELECT * FROM Users WHERE username='admin'").fetchone()
        if not result:
            conn.execute("INSERT INTO Users (username, password, role) VALUES (?, ?, ?)",
                         ("admin", hash_password("admin123"), "admin"))
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
                st.success(f"✅ Welcome, {username}!")
                st.rerun()
            else:
                st.error("❌ Invalid credentials.")

def logout():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.rerun()

# ---- Init DB & Session ----
init_user_db()
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
    st.stop()

# ---------------------- MAIN DASHBOARD SECTION ----------------------

# ---- Page Setup ----
st.set_page_config(layout="wide", page_title="Lead Manager")
st.markdown(f"<p style='text-align:right;'>👋 Logged in as: <b>{st.session_state.username}</b></p>", unsafe_allow_html=True)
if st.button("🔓 Logout"):
    logout()

st.markdown("""
    <style>
    thead tr th {
        background-color: #f1f5f9 !important;
        color: #1f2937 !important;
        font-size: 15px !important;
        font-weight: 700 !important;
        text-align: left;
        padding: 10px 8px;
        border-bottom: 2px solid #ccc;
    }
    tbody tr:hover {
        background-color: #f0f0f0 !important;
    }
    tbody tr:nth-child(even) {
        background-color: #f9f9f9 !important;
    }
    table {
        border-collapse: collapse;
        border: 1px solid #ddd;
        border-radius: 6px;
        overflow: hidden;
        width: 100% !important;
    }
    td {
        border-bottom: 1px solid #eee !important;
        padding: 6px 8px;
    }
    .dataframe th, .dataframe td {
        font-size: 13px !important;
    }
    .stDataFrameContainer {
        padding: 0 !important;
        border: 1px solid #ccc;
        border-radius: 8px;
    }
    .element-container:has(.stDataFrame) {
        width: 100% !important;
    }
    </style>
""", unsafe_allow_html=True)

# ---- Dark Mode Styling ----
if st.session_state.get("dark_mode"):
    st.markdown("""
    <style>
    .stApp { background-color: #1e1e1e !important; color: white !important; }
    div[data-testid="stSidebar"] { background-color: #2c2c2c !important; color: white !important; }
    .stSelectbox div[data-baseweb="select"], .stTextInput input, .stTextArea textarea {
        background-color: #333 !important; color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ---- Title ----
st.markdown("""
<style>
.title-container { margin-top: -30px; margin-bottom: 0px; padding-top: 0px; }
.title-container h1 { margin: 0; font-size: 40px; }
</style>
<div class="title-container" style='display: flex; justify-content: center; align-items: center; gap: 10px;'>
    <img src="https://cdn-icons-png.flaticon.com/512/3048/3048390.png" width="40">
    <h1>Lead Manager</h1>
</div>
""", unsafe_allow_html=True)

# ---- Session Defaults ----
for key, default in {
    "dark_mode": False,
    "page": 1,
    "org_name": "All",
    "source_types": []
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ---- Sidebar ----
st.sidebar.markdown("<h2 style='color:#4B4B4B; font-weight:600;'> 🏢 Brick Work </h2>", unsafe_allow_html=True)
if st.sidebar.checkbox("🌚 Dark Mode", value=st.session_state.dark_mode):
    st.session_state.dark_mode = True
else:
    st.session_state.dark_mode = False

st.sidebar.markdown("### 🔍 Search & Filters")

# ---- Load Org Names from SQLite ----
try:
    with sqlite3.connect("leads.db") as conn:
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS LeadSources (OrganizationName TEXT, ContactPersonName TEXT, ContactDetails TEXT, Address TEXT, Email TEXT, SourceType TEXT)")
        cursor.execute("SELECT DISTINCT OrganizationName FROM LeadSources ORDER BY OrganizationName")
        org_names = [row[0] for row in cursor.fetchall()]
except Exception:
    org_names = []
    st.sidebar.error("❌ Could not load organizations.")

default_index = 0 if st.session_state.org_name == "All" else (["All"] + org_names).index(st.session_state.org_name)
st.sidebar.selectbox("Organization Name", ["All"] + org_names, index=default_index, key="org_name")

st.sidebar.multiselect(
    "Source Types",
    ["Personal Contacts", "INC Clients in Bcrisp", "OCRA in Bcrisp", "Bankers",
     "Conference /Webinors", "Industry Database", "Social Media",
     "Client Reference", "Board/wellwishers"],
    key="source_types"
)

st.sidebar.button("🔄 Reset Filters", on_click=lambda: st.session_state.update({
    "org_name": "All", "source_types": [], "page": 1
}))

# ---- Add New Lead ----
if st.sidebar.checkbox("➕ Add New Lead"):
    with st.form("add_lead_form"):
        st.markdown("### ➕ Add New Lead")
        org = st.text_input("Organization")
        contact = st.text_input("Contact Person")
        phone = st.text_input("Contact Details")
        email = st.text_input("Email")
        addr = st.text_area("Address")
        source = st.selectbox("Source Type", [
            "Personal Contacts", "INC Clients in Bcrisp", "OCRA in Bcrisp", "Bankers",
            "Conference /Webinors", "Industry Database", "Social Media",
            "Client Reference", "Board/wellwishers"])
        if st.form_submit_button("✅ Submit Lead") and org:
            try:
                with sqlite3.connect("leads.db") as conn:
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO LeadSources 
                        (OrganizationName, ContactPersonName, ContactDetails, Address, Email, SourceType)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (org, contact, phone, addr, email, source))
                    conn.commit()
                    st.success(f"✅ Lead '{org}' added successfully!")
            except Exception as e:
                st.error(f"❌ Insert Error: {e}")

# ---- Filter Query ----
filters, params = [], []
if st.session_state.org_name != "All":
    filters.append("OrganizationName = ?")
    params.append(st.session_state.org_name)
if st.session_state.source_types:
    filters.append(f"SourceType IN ({','.join(['?'] * len(st.session_state.source_types))})")
    params.extend(st.session_state.source_types)
where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

# ---- Pagination ----
page, per_page = st.session_state.page, 10000
offset = (page - 1) * per_page

# ---- Data Fetch ----
data, total_count = [], 0
try:
    with sqlite3.connect("leads.db") as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM LeadSources {where_clause}", params)
        total_count = cur.fetchone()[0]
        cur.execute(f"""
            SELECT OrganizationName, ContactPersonName, ContactDetails, Address, Email, SourceType
            FROM LeadSources {where_clause}
            ORDER BY OrganizationName LIMIT ? OFFSET ?
        """, (*params, per_page, offset))
        data = cur.fetchall()
except Exception as e:
    st.error(f"❌ Database Error: {e}")

# ---- Display Table ----
if data:
    st.markdown(f"<p style='font-size:14px;'>🎯 {total_count} lead(s) match the applied filters</p>", unsafe_allow_html=True)

    def get_source_type_icon(source_type):
        mapping = {
            "Personal Contacts": "👤 Personal Contacts",
            "INC Clients in Bcrisp": "🏢 INC Clients in Bcrisp",
            "OCRA in Bcrisp": "📘 OCRA in Bcrisp",
            "Bankers": "🏦 Bankers",
            "Conference /Webinors": "🎤 Conference /Webinors",
            "Industry Database": "📊 Industry Database",
            "Social Media": "📱 Social Media",
            "Client Reference": "📞 Client Reference",
            "Board/wellwishers": "🎓 Board/wellwishers"
        }
        return mapping.get(source_type, f"❓ {source_type}")

    df = pd.DataFrame(data, columns=["Organization", "Contact Person", "Contact", "Address", "Email", "Source Type"])
    df["Source Type"] = df["Source Type"].apply(get_source_type_icon)
    df.index += 1
    df.columns = ["🏢 Organization", "👤 Contact Person", "📞 Contact", "📍 Address", "✉️ Email", "📘 Source Type"]
    st.dataframe(df, use_container_width=True)

    # ---- Dashboard ----
    st.markdown("### 📊 Lead Dashboard Analytics")
    df_viz = pd.DataFrame(data, columns=["Organization", "Contact Person", "Contact", "Address", "Email", "Source Type"])
    total = len(df_viz)
    unique_orgs = df_viz["Organization"].nunique()
    top_src = df_viz["Source Type"].value_counts().idxmax()

    col1, col2, col3 = st.columns(3)
    col1.metric("🧾 Total Leads", total)
    col2.metric("🏢 Unique Organizations", unique_orgs)
    col3.metric("🔥 Top Source", top_src)

    pie = px.pie(df_viz, names="Source Type", title="Source Distribution", hole=0.4)
    org_counts = df_viz["Organization"].value_counts().reset_index()
    org_counts.columns = ["Organization", "Count"]
    bar = px.bar(org_counts, x="Organization", y="Count", text="Count", title="Leads by Organization")
    bar.update_traces(textposition="outside")
    bar.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')

    col4, col5 = st.columns(2)
    col4.plotly_chart(pie, use_container_width=True)
    col5.plotly_chart(bar, use_container_width=True)
else:
    st.warning("No data found.")

# ---- Pagination Footer ----
pages = max(1, math.ceil(total_count / per_page))
st.caption(f"Page {page} of {pages} — {total_count} total results")
prev, _, next = st.columns([1, 2, 1])
if page > 1 and prev.button("⬅ Previous"):
    st.session_state.page -= 1
    st.rerun()
if page < pages and next.button("Next ➡"):
    st.session_state.page += 1
    st.rerun()
