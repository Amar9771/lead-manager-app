import streamlit as st
import sqlite3
import pandas as pd
import math
import plotly.express as px
import hashlib

# ---------------------- CONFIG & CONSTANTS ----------------------
st.set_page_config(layout="wide", page_title="Lead Manager")

SOURCE_TYPES = [
    "Personal Contacts", "INC Clients in Bcrisp", "OCRA in Bcrisp", "Bankers",
    "Conference /Webinors", "Industry Database", "Social Media",
    "Client Reference", "Board/wellwishers"
]

# ---------------------- STYLING ----------------------
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #f5f9ff, #ffffff);
        font-family: "Segoe UI", sans-serif;
    }
    h1, h2, h3 {
        color: #1e3a8a !important;
    }
    .stButton>button {
        background-color: #1d4ed8;
        color: white;
        border-radius: 6px;
        padding: 6px 16px;
    }
    .stButton>button:hover {
        background-color: #2563eb;
    }
    .stTextInput>div>input, .stTextArea>div>textarea {
        border-radius: 8px;
        border: 1px solid #ccc;
        padding: 8px;
    }
    .stSidebar {
        background-color: #e0f2fe;
        padding: 16px;
        border-right: 1px solid #cbd5e1;
    }
    </style>
""", unsafe_allow_html=True)

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

# ---------------------- MAIN DASHBOARD ----------------------
st.markdown(f"<p style='text-align:right;'>👋 Logged in as: <b>{st.session_state.username}</b></p>", unsafe_allow_html=True)
if st.button("🔓 Logout"):
    logout()

# ---- Session Defaults ----
for key, default in {
    "dark_mode": False,
    "page": 1,
    "org_name": "All",
    "source_types": [],
    "search": ""
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ---- Dark Mode Option ----
if st.sidebar.checkbox("🌚 Dark Mode", value=st.session_state.dark_mode):
    st.session_state.dark_mode = True
    st.toast("🌙 Dark Mode Enabled")
else:
    st.session_state.dark_mode = False
    st.toast("🌞 Light Mode Enabled")

if st.session_state.dark_mode:
    st.markdown("""
    <style>
    .stApp { background-color: #1e1e1e !important; color: white !important; }
    div[data-testid="stSidebar"] { background-color: #2c2c2c !important; color: white !important; }
    .stTextInput input, .stSelectbox div[data-baseweb="select"] { background-color: #333; color: white; }
    </style>
    """, unsafe_allow_html=True)

# ---- Title ----
st.markdown("""
<div style='display: flex; justify-content: center; align-items: center; gap: 10px; margin-top: -30px;'>
    <img src="https://cdn-icons-png.flaticon.com/512/3048/3048390.png" width="40">
    <h1>Lead Manager</h1>
</div>
""", unsafe_allow_html=True)

# ---- Sidebar Filters ----
st.sidebar.markdown("### 🔍 Filters")
try:
    with sqlite3.connect("leads.db") as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS LeadSources (
            OrganizationName TEXT, ContactPersonName TEXT, ContactDetails TEXT,
            Address TEXT, Email TEXT, SourceType TEXT)""")
        org_names = [row[0] for row in conn.execute("SELECT DISTINCT OrganizationName FROM LeadSources ORDER BY OrganizationName")]
except Exception:
    org_names = []
    st.sidebar.error("❌ Could not load organizations.")

org_list = ["All"] + org_names
default_index = org_list.index(st.session_state.org_name) if st.session_state.org_name in org_list else 0
st.sidebar.selectbox("Organization", org_list, index=default_index, key="org_name")

st.sidebar.multiselect("Source Type", SOURCE_TYPES, key="source_types")
st.sidebar.text_input("🔎 Search Org/Contact", key="search")
st.sidebar.button("🔄 Reset Filters", on_click=lambda: st.session_state.update({
    "org_name": "All", "source_types": [], "page": 1, "search": ""
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
        source = st.selectbox("Source Type", SOURCE_TYPES)
        if st.form_submit_button("✅ Submit Lead") and org:
            try:
                with sqlite3.connect("leads.db") as conn:
                    conn.execute("""
                        INSERT INTO LeadSources 
                        (OrganizationName, ContactPersonName, ContactDetails, Address, Email, SourceType)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (org, contact, phone, addr, email, source))
                    conn.commit()
                    st.success(f"✅ Lead '{org}' added successfully!")
            except Exception as e:
                st.error(f"❌ Insert Error: {e}")

# ---- Query & Filters ----
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

# ---- Fetch Data ----
try:
    with sqlite3.connect("leads.db") as conn:
        cur = conn.cursor()
        total_count = cur.execute(f"SELECT COUNT(*) FROM LeadSources {where_clause}", params).fetchone()[0]
        cur.execute(f"""
            SELECT OrganizationName, ContactPersonName, ContactDetails, Address, Email, SourceType
            FROM LeadSources {where_clause}
            ORDER BY OrganizationName LIMIT ? OFFSET ?
        """, (*params, per_page, offset))
        data = cur.fetchall()
except Exception as e:
    data = []
    st.error(f"❌ Database Error: {e}")

# ---- Display Table ----
if data:
    df = pd.DataFrame(data, columns=["Organization", "Contact Person", "Contact", "Address", "Email", "Source Type"])

    # Apply Search Filter
    if st.session_state.search:
        search = st.session_state.search.lower()
        df = df[df["Organization"].str.lower().str.contains(search) | df["Contact Person"].str.lower().str.contains(search)]

    # Display Table
    df.index += 1
    df.columns = ["🏢 Organization", "👤 Contact Person", "📞 Contact", "📍 Address", "✉️ Email", "📘 Source Type"]
    st.markdown(f"<p style='font-size:14px;'>🎯 {len(df)} filtered lead(s)</p>", unsafe_allow_html=True)
    st.dataframe(df, use_container_width=True)

    # CSV Export
    st.download_button("📥 Download CSV", df.to_csv(index=False).encode('utf-8'), file_name="leads.csv")

    # ---- Dashboard ----
    if not df.empty:
        st.markdown("### 📊 Lead Dashboard Analytics")
        total = len(df)
        unique_orgs = df["🏢 Organization"].nunique()
        top_src = df["📘 Source Type"].value_counts().idxmax()

        col1, col2, col3 = st.columns(3)
        col1.metric("🧾 Total Leads", total)
        col2.metric("🏢 Unique Orgs", unique_orgs)
        col3.metric("🔥 Top Source", top_src.split(" ")[-1])

        pie = px.pie(df, names="📘 Source Type", title="Source Distribution", hole=0.4)
        org_counts = df["🏢 Organization"].value_counts().reset_index()
        org_counts.columns = ["Organization", "Count"]
        bar = px.bar(org_counts, x="Organization", y="Count", text="Count", title="Leads by Organization")
        bar.update_traces(textposition="outside")

        col4, col5 = st.columns(2)
        col4.plotly_chart(pie, use_container_width=True)
        col5.plotly_chart(bar, use_container_width=True)
    else:
        st.info("🔍 No analytics to display. Adjust filters to see data.")
else:
    st.warning("No data found.")

# ---- Pagination Controls ----
pages = max(1, math.ceil(total_count / per_page))
st.caption(f"Page {page} of {pages} — {total_count} total records")
prev, _, next = st.columns([1, 2, 1])
if page > 1 and prev.button("⬅ Previous"):
    st.session_state.page -= 1
    st.rerun()
if page < pages and next.button("Next ➡"):
    st.session_state.page += 1
    st.rerun()
