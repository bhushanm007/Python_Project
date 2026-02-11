
import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, timedelta
import plotly.express as px

# --- Database Setup ---
# This section creates the database file automatically if it doesn't exist
def init_db():
    conn = sqlite3.connect('job_crm.db')
    c = conn.cursor()
    
    # Create Companies Table
    c.execute('''CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE,
        website TEXT,
        notes TEXT
    )''')
    
    # Create Contacts Table
    c.execute('''CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY,
        company_id INTEGER,
        name TEXT,
        role TEXT,
        email TEXT,
        linkedin TEXT,
        referral_strength TEXT,
        FOREIGN KEY (company_id) REFERENCES companies (id)
    )''')
    
    # Create Applications Table
    c.execute('''CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY,
        company_id INTEGER,
        position_title TEXT,
        job_link TEXT,
        status TEXT,
        applied_date DATE,
        follow_up_date DATE,
        resume_version TEXT,
        meeting_link TEXT,
        notes TEXT,
        FOREIGN KEY (company_id) REFERENCES companies (id)
    )''')
    
    conn.commit()
    conn.close()

# Helper function to run commands (Insert/Update)
def run_query(query, params=()):
    conn = sqlite3.connect('job_crm.db')
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    conn.close()

# Helper function to get data (Select)
def get_data(query, params=()):
    conn = sqlite3.connect('job_crm.db')
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

# --- APP START ---
st.set_page_config(page_title="Job Hunter CRM", layout="wide", page_icon="💼")
init_db()

# Sidebar
st.sidebar.title("💼 Job Hunter CRM")
menu = st.sidebar.radio("Navigate", ["Dashboard", "My Pipeline", "Network & Contacts", "Tools & Email"])

# ==========================
# 1. DASHBOARD
# ==========================
if menu == "Dashboard":
    st.title("📊 Command Center")
    
    # Metrics
    try:
        total_apps = get_data("SELECT COUNT(*) as c FROM applications").iloc[0]['c']
        active_apps = get_data("SELECT COUNT(*) as c FROM applications WHERE status NOT IN ('Rejected', 'Offer Accepted')").iloc[0]['c']
        interviews = get_data("SELECT COUNT(*) as c FROM applications WHERE status LIKE '%Interview%'").iloc[0]['c']
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Applied", total_apps)
        col2.metric("Active Processes", active_apps)
        col3.metric("Interviews", interviews)
        
        # Action Items
        st.markdown("### 🚨 Action Items (Next 3 Days)")
        today = date.today()
        upcoming = today + timedelta(days=3)
        
        action_query = f"""
            SELECT c.name as Company, a.position_title, a.status, a.follow_up_date, a.meeting_link
            FROM applications a
            JOIN companies c ON a.company_id = c.id
            WHERE a.follow_up_date BETWEEN '{today}' AND '{upcoming}'
            OR (a.status LIKE '%Interview%' AND a.follow_up_date >= '{today}')
        """
        actions = get_data(action_query)
        
        if not actions.empty:
            st.warning(f"You have {len(actions)} tasks requiring attention!")
            st.dataframe(actions, use_container_width=True)
        else:
            st.success("✅ No urgent actions. Great job!")

        # Funnel Chart
        st.markdown("### 📉 Pipeline Funnel")
        funnel_data = get_data("SELECT status, COUNT(*) as count FROM applications GROUP BY status")
        if not funnel_data.empty:
            fig = px.bar(funnel_data, x='status', y='count', title="Applications by Stage", color='status')
            st.plotly_chart(fig, use_container_width=True)

    except Exception:
        st.info("Database initialized. Go to 'My Pipeline' to add your first job!")

# ==========================
# 2. MY PIPELINE
# ==========================
elif menu == "My Pipeline":
    st.title("🗂️ Application Pipeline")
    
    tab1, tab2 = st.tabs(["➕ New Application", "📋 Manage Applications"])
    
    with tab1:
        st.subheader("Log a New Job")
        col1, col2 = st.columns(2)
        
        with col1:
            existing_companies = get_data("SELECT name FROM companies")['name'].tolist()
            comp_mode = st.radio("Company", ["Existing", "New"], horizontal=True)
            
            if comp_mode == "Existing":
                company_name = st.selectbox("Select Company", existing_companies) if existing_companies else None
            else:
                company_name = st.text_input("Enter New Company Name")
                
            position = st.text_input("Position Title")
            job_link = st.text_input("Link to Job Post")

        with col2:
            status = st.selectbox("Stage", ["Applied", "Screening", "Tech Interview", "Manager Interview", "Offer", "Rejected"])
            applied_date = st.date_input("Date Applied", date.today())
            follow_up = st.date_input("Next Follow-up Date")
            resume_ver = st.text_input("Resume Version Sent", "v1.0")

        if st.button("Save Application"):
            if company_name:
                # Check/Create Company
                check_comp = get_data("SELECT id FROM companies WHERE name=?", (company_name,))
                
                if check_comp.empty:
                    run_query("INSERT INTO companies (name) VALUES (?)", (company_name,))
                    # FIXED: Added int() to force standard integer conversion
                    comp_id = int(get_data("SELECT id FROM companies WHERE name=?", (company_name,)).iloc[0]['id'])
                else:
                    # FIXED: Added int() to force standard integer conversion
                    comp_id = int(check_comp.iloc[0]['id'])
                
                # Insert Application
                run_query('''
                    INSERT INTO applications (company_id, position_title, job_link, status, applied_date, follow_up_date, resume_version)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (comp_id, position, job_link, status, applied_date, follow_up, resume_ver))
                st.success("Application Saved Successfully!")
            else:
                st.error("Please enter a company name.")

    with tab2:
        st.subheader("Update Status & Details")
        df = get_data("""
            SELECT a.id, c.name as Company, a.position_title, a.status, a.follow_up_date, a.meeting_link 
            FROM applications a 
            JOIN companies c ON a.company_id = c.id
        """)
        st.dataframe(df, hide_index=True, use_container_width=True)
        
        st.divider()
        st.write("Edit an Application:")
        app_id_to_edit = st.number_input("Enter ID (from table above)", min_value=0, step=1)
        if app_id_to_edit > 0:
            details = get_data("SELECT * FROM applications WHERE id=?", (app_id_to_edit,))
            if not details.empty:
                new_status = st.selectbox("Update Status", ["Applied", "Screening", "Tech Interview", "Manager Interview", "Offer", "Rejected"], index=0)
                new_notes = st.text_area("Notes", value=details.iloc[0]['notes'] or "")
                new_link = st.text_input("Meeting Link", value=details.iloc[0]['meeting_link'] or "")
                
                if st.button("Update Record"):
                    run_query("UPDATE applications SET status=?, notes=?, meeting_link=? WHERE id=?", (new_status, new_notes, new_link, app_id_to_edit))
                    st.success("Updated!")

# ==========================
# 3. NETWORK
# ==========================
elif menu == "Network & Contacts":
    st.title("🤝 Networking Hub")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Add Contact")
        companies = get_data("SELECT id, name FROM companies")
        
        if not companies.empty:
            c_dict = dict(zip(companies['name'], companies['id']))
            selected_c = st.selectbox("Company", list(c_dict.keys()))
            
            c_name = st.text_input("Name")
            c_role = st.text_input("Role")
            c_email = st.text_input("Email")
            c_strength = st.select_slider("Strength", options=["Cold", "Acquaintance", "Friend", "Strong Reference"])
            
            if st.button("Save Contact"):
                run_query("INSERT INTO contacts (company_id, name, role, email, referral_strength) VALUES (?, ?, ?, ?, ?)",
                          (c_dict[selected_c], c_name, c_role, c_email, c_strength))
                st.success("Contact Added!")
        else:
            st.warning("Add a company first.")

    with col2:
        st.subheader("Your Network")
        network_df = get_data("""
            SELECT c.name as Company, ct.name as Contact, ct.role, ct.email, ct.referral_strength 
            FROM contacts ct 
            JOIN companies c ON ct.company_id = c.id
        """)
        st.dataframe(network_df, use_container_width=True)

# ==========================
# 4. TOOLS
# ==========================
elif menu == "Tools & Email":
    st.title("📧 Email Helper")
    
    pending = get_data("SELECT a.id, c.name, a.position_title FROM applications a JOIN companies c ON a.company_id = c.id")
    
    if not pending.empty:
        choice = st.selectbox("Draft email for:", pending['position_title'] + " at " + pending['name'])
        row = pending[pending['position_title'] + " at " + pending['name'] == choice].iloc[0]
        
        email_type = st.radio("Type", ["Follow-up", "Thank You"])
        
        if email_type == "Follow-up":
            st.code(f"""
Subject: Following up on my application for {row['position_title']}

Hi [Hiring Manager],

I recently applied for the {row['position_title']} role at {row['name']} and wanted to reiterate my interest.
Please let me know if you need any further information.

Best,
[Your Name]
            """)
        elif email_type == "Thank You":
            st.code(f"""
Subject: Thank you / {row['position_title']} Interview

Hi [Interviewer Name],

Thank you for speaking with me about the {row['position_title']} role at {row['name']}.
I am excited about the opportunity and look forward to hearing next steps.

Best,
[Your Name]
            """)
    else:
        st.info("Add applications to draft emails.")

