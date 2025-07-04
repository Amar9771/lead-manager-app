import streamlit as st
import pyodbc
import pandas as pd
import math
import plotly.express as px
import hashlib
from datetime import datetime

# ---------------------- AUTH SECTION ----------------------

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(password, hashed):
    return hash_password(password) == hashed

def get_connection():
    return pyodbc.connect(
        "DRIVER={SQL Server};SERVER=Venus;DATABASE=Demo;UID=bcrisp;PWD=Bcrisp*5"
    )

def init_user_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Users' AND xtype='U')
            CREATE TABLE Users (
                id INT IDENTITY(1,1) PRIMARY KEY,
                username NVARCHAR(255) UNIQUE,
                password NVARCHAR(255),
                role NVARCHAR(50)
            )
        """)
        result = cursor.execute("SELECT * FROM Users WHERE username='admin'").fetchone()
        if not result:
            cursor.execute("INSERT INTO Users (username, password, role) VALUES (?, ?, ?)",
                           ("admin", hash_password("admin123"), "admin"))
            conn.commit()

def login():
    st.title("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        with get_connection() as conn:
            df = pd.read_sql("SELECT * FROM Users WHERE username = ?", conn, params=(username,))
            if not df.empty and check_password(password, df['password'][0]):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = df['role'][0]
                st.success(f"✅ Welcome, {username}!")
                st.rerun()
            else:
                st.error("❌ Invalid credentials.")

def logout():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.rerun()

# ---------------------- SESSION INIT ----------------------

init_user_db()
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
    st.stop()

# ---------------------- PAGE SETUP ----------------------

st.set_page_config(layout="wide", page_title="Lead Manager")
st.markdown(f"<p style='text-align:right;'>👋 Logged in as: <b>{st.session_state.username}</b></p>", unsafe_allow_html=True)
if st.button("🔓 Logout"):
    logout()

# ---------------------- UI STYLE ----------------------

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
    table {
        border-collapse: collapse;
        border: 1px solid #ddd;
        width: 100% !important;
    }
    td {
        border-bottom: 1px solid #eee !important;
        padding: 6px 8px;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------- FILTER SETUP ----------------------

for key, default in {
    "dark_mode": False,
    "page": 1,
    "org_name": "All",
    "source_types": []
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.sidebar.markdown("### 🔍 Filters")

try:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='LeadSources' AND xtype='U')
            CREATE TABLE LeadSources (
                LeadID INT IDENTITY(1,1) PRIMARY KEY,
                OrganizationName NVARCHAR(255),
                ContactPersonName NVARCHAR(255),
                ContactDetails NVARCHAR(255),
                Address NVARCHAR(MAX),
                Email NVARCHAR(255),
                SourceType NVARCHAR(100),
                Remarks NVARCHAR(MAX),
                CreatedOn DATETIME
            )
        """)
        cursor.execute("SELECT DISTINCT OrganizationName FROM LeadSources ORDER BY OrganizationName")
        org_names = [row[0] for row in cursor.fetchall()]
except Exception as e:
    org_names = []
    st.sidebar.error(f"Error loading orgs: {e}")

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

# ---------------------- ADD LEAD ----------------------

if st.sidebar.checkbox("➕ Add New Lead"):
    with st.form("add_lead_form"):
        st.markdown("### ➕ Add New Lead")
        org = st.text_input("Organization")
        contact = st.text_input("Contact Person")
        phone = st.text_input("Contact Details")
        email = st.text_input("Email")
        addr = st.text_area("Address")
        remarks = st.text_area("Remarks")
        source = st.selectbox("Source Type", [
            "Personal Contacts", "INC Clients in Bcrisp", "OCRA in Bcrisp", "Bankers",
            "Conference /Webinors", "Industry Database", "Social Media",
            "Client Reference", "Board/wellwishers"])
        if st.form_submit_button("✅ Submit Lead") and org:
            try:
                with get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO LeadSources 
                        (OrganizationName, ContactPersonName, ContactDetails, Address, Email, SourceType, Remarks, CreatedOn)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (org, contact, phone, addr, email, source, remarks, datetime.now()))
                    conn.commit()
                    st.success(f"✅ Lead '{org}' added successfully!")
            except Exception as e:
                st.error(f"❌ Insert Error: {e}")

# ---------------------- FILTERING AND DATA ----------------------

filters, params = [], []
if st.session_state.org_name != "All":
    filters.append("OrganizationName = ?")
    params.append(st.session_state.org_name)
if st.session_state.source_types:
    placeholders = ','.join('?' for _ in st.session_state.source_types)
    filters.append(f"SourceType IN ({placeholders})")
    params.extend(st.session_state.source_types)

where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
page, per_page = st.session_state.page, 1000
offset = (page - 1) * per_page

data, total_count = [], 0
try:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM LeadSources {where_clause}", params)
        total_count = cur.fetchone()[0]
        query = f"""
            SELECT LeadID, OrganizationName, ContactPersonName, ContactDetails, Address, Email, SourceType, Remarks, CreatedOn
            FROM LeadSources {where_clause}
            ORDER BY OrganizationName OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
        cur.execute(query, (*params, offset, per_page))
        data = cur.fetchall()
except Exception as e:
    st.error(f"Database Error: {e}")

# ---------------------- DISPLAY DATA ----------------------

if data:
    df = pd.DataFrame(data, columns=[
        "Lead ID", "Organization", "Contact Person", "Contact", "Address", "Email", "Source Type", "Remarks", "Created On"
    ])
    df.index += 1
    st.dataframe(df, use_container_width=True)

    st.markdown("### 📊 Dashboard")
    total = len(df)
    unique_orgs = df["Organization"].nunique()
    top_src = df["Source Type"].value_counts().idxmax()

    col1, col2, col3 = st.columns(3)
    col1.metric("🧾 Total Leads", total)
    col2.metric("🏢 Unique Orgs", unique_orgs)
    col3.metric("🔥 Top Source", top_src)

    pie = px.pie(df, names="Source Type", title="Lead Source Distribution", hole=0.4)
    bar_data = df["Organization"].value_counts().reset_index()
    bar_data.columns = ["Organization", "Count"]
    bar = px.bar(bar_data, x="Organization", y="Count", title="Leads per Org", text="Count")

    col4, col5 = st.columns(2)
    col4.plotly_chart(pie, use_container_width=True)
    col5.plotly_chart(bar, use_container_width=True)
else:
    st.warning("No data found.")

# ---------------------- PAGINATION ----------------------

pages = max(1, math.ceil(total_count / per_page))
st.caption(f"Page {page} of {pages} — {total_count} total results")
prev, _, next = st.columns([1, 2, 1])
if page > 1 and prev.button("⬅ Previous"):
    st.session_state.page -= 1
    st.rerun()
if page < pages and next.button("Next ➡"):
    st.session_state.page += 1
    st.rerun()
