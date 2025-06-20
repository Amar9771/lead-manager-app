# app.py
from flask import Flask, render_template, request, jsonify
import pyodbc
import math

app = Flask(__name__)

# SQL Server connection string
conn_str = (
    "DRIVER={SQL Server};"
    "SERVER=Venus;"
    "DATABASE=Demo;"
    "UID=bcrisp;"
    "PWD=Bcrisp*5"
)

# Helper: Badge colors per source type
def get_source_type_color(source_type):
    return {
        "Personal Contacts": "primary",
        "INC Clients in Bcrisp": "secondary",
        "OCRA in Bcrisp": "info",
        "Bankers": "success",
        "Conference /Webinors": "warning",
        "Industry Database": "dark",
        "Social Media": "danger",
        "Client Reference": "light",
        "Board/wellwishers": "success"
    }.get(source_type, "secondary")

# Helper: Icon per source type
def get_source_type_icon(source_type):
    return {
        "Personal Contacts": "👥",
        "INC Clients in Bcrisp": "🏢",
        "OCRA in Bcrisp": "📂",
        "Bankers": "🏦",
        "Conference /Webinors": "🎤",
        "Industry Database": "📚",
        "Social Media": "📱",
        "Client Reference": "🔗",
        "Board/wellwishers": "👔"
    }.get(source_type, "📌")

@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    message = None
    show_form = False
    page = int(request.args.get('page', 1))
    per_page = 10
    sort_by = request.form.get('sort_by') or request.args.get('sort_by') or 'OrganizationName'

    where_clauses = []
    params = []

    show_all = request.form.get('show_all') == '1'
    org_name = request.form.get('organization_name', '').strip()
    source_types = request.form.getlist('source_type') or request.form.getlist('source_type[]')

    if org_name:
        where_clauses.append("OrganizationName LIKE ?")
        params.append(f"%{org_name}%")

    if source_types:
        placeholders = ','.join(['?'] * len(source_types))
        where_clauses.append(f"SourceType IN ({placeholders})")
        params.extend(source_types)

    if 'show_form' in request.form:
        show_form = True

    if 'add_lead' in request.form:
        org_name = request.form['org_name']
        contact_person = request.form['contact_person']
        contact_details = request.form['contact_details']
        email = request.form['email']
        address = request.form['address']
        source_type = request.form['source_type']

        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO LeadSources 
                (OrganizationName, ContactPersonName, ContactDetails, Address, Email, SourceType)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (org_name, contact_person, contact_details, address, email, source_type))
            conn.commit()
            message = f"✅ Lead '{org_name}' added successfully!"
            show_form = False

    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()

        if show_all:
            where_clause = ""
        else:
            where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ("WHERE 1=0" if request.method == 'POST' else "")

        count_query = f"SELECT COUNT(*) FROM LeadSources {where_clause}"
        cursor.execute(count_query, *params)
        total_count = cursor.fetchone()[0]

        offset = (page - 1) * per_page
        query = f"""
            SELECT OrganizationName, ContactPersonName, ContactDetails, Address, Email, SourceType
            FROM LeadSources
            {where_clause}
            ORDER BY {sort_by}
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
        cursor.execute(query, *params, offset, per_page)
        rows = cursor.fetchall()

        for row in rows:
            results.append({
                'OrganizationName': row.OrganizationName,
                'ContactPersonName': row.ContactPersonName,
                'ContactDetails': row.ContactDetails,
                'Address': row.Address,
                'Email': row.Email,
                'SourceType': row.SourceType
            })

    total_pages = math.ceil(total_count / per_page) if total_count > 0 else 1

    return render_template(
        'index.html',
        results=results,
        message=message,
        show_form=show_form,
        sort_by=sort_by,
        page=page,
        total_pages=total_pages,
        get_source_type_color=get_source_type_color,
        get_source_type_icon=get_source_type_icon,
        view_mode=request.form.get('view_mode', 'card')
    )

@app.route('/autocomplete')
def autocomplete():
    term = request.args.get('term', '')
    matches = []
    if term:
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT OrganizationName
                FROM LeadSources
                WHERE OrganizationName LIKE ?
            """, f'%{term}%')
            matches = [row[0] for row in cursor.fetchall()]
    return jsonify(matches)

if __name__ == '__main__':
    app.run(debug=True)