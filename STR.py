import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import plotly.express as px

# ---------------------- CONFIG ----------------------
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
    .top-banner {
        background-color: #1e3a8a;
        color: white;
        padding: 12px 25px;
        font-size: 22px;
        font-weight: bold;
        text-align: left;
        border-bottom: 3px solid #0d47a1;
    }
    div[data-testid="stDataFrame"] div[role="grid"] {
        overflow-x: auto;
        white-space: nowrap;
    }
    </style>
    <div class="top-banner">🚀 Lead Manager Dashboard</div>
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
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ---------------------- INIT ----------------------
init_user_db()
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if not st.session_state.logged_in:
    login()
    st.stop()

# ---------------------- HEADER ----------------------
st.markdown(f"""
""", unsafe_allow_html=True)

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
                source_types_from_db = [row[0] for row in conn.execute("SELECT DISTINCT SourceType FROM LeadSources WHERE SourceType IS NOT NULL")]
        except:
            org_names = []
            source_types_from_db = []

        st.selectbox("Organization", ["All"] + org_names, key="org_name")
        st.multiselect("Source Type", source_types_from_db, key="source_types")
        st.text_input("Search Org/Contact", key="search")
        if st.button("Reset Filters"):
            for k in ["org_name", "source_types", "search"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.experimental_rerun()

    # Add New Lead (Admin & User)
    if st.session_state.role in ['admin', 'user']:
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

        # Bulk Upload
        st.markdown("### 📤 Bulk Lead Upload")
        upload_file = st.file_uploader("Upload Excel or CSV", type=["xlsx", "csv"])
        if upload_file:
            try:
                if upload_file.name.endswith(".csv"):
                    bulk_df = pd.read_csv(upload_file)
                else:
                    bulk_df = pd.read_excel(upload_file)

                expected_cols = [
                    "OrganizationName", "ContactPersonName", "ContactDetails",
                    "Address", "Email", "SourceType"
                ]
                if all(col in bulk_df.columns for col in expected_cols):
                    bulk_df["SourceType"] = bulk_df["SourceType"].str.strip().str.title()
                    st.success("✅ File read successfully. Preview below:")
                    st.dataframe(bulk_df.head())
                    if st.button("🚀 Upload Leads to Database"):
                        with sqlite3.connect("leads.db") as conn:
                            for _, row in bulk_df.iterrows():
                                conn.execute("""
                                    INSERT INTO LeadSources 
                                    (OrganizationName, ContactPersonName, ContactDetails, Address, Email, SourceType)
                                    VALUES (?, ?, ?, ?, ?, ?)""",
                                    tuple(row[col] for col in expected_cols))
                        st.success("✅ All leads uploaded!")
                        st.experimental_rerun()
                else:
                    st.error(f"Missing required columns. Expected: {', '.join(expected_cols)}")
            except Exception as e:
                st.error(f"❌ Failed to read file: {e}")

        if st.checkbox("📥 Download Upload Template"):
            template = pd.DataFrame(columns=[
                "OrganizationName", "ContactPersonName", "ContactDetails",
                "Address", "Email", "SourceType"
            ])
            st.download_button("Download Template", template.to_csv(index=False), "lead_upload_template.csv", "text/csv")

    # Admin: Create User
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
    st.dataframe(df, use_container_width=True, hide_index=False)

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
