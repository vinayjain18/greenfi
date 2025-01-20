import streamlit as st
import requests
import mysql.connector
from dotenv import load_dotenv
from mysql.connector import Error
import hmac
load_dotenv()

st.set_page_config(page_title="GreenFi", layout="wide")
st.markdown(
    """
    <style>
    .stToolbarActionButton {
        display: none;
        visibility: hidden;
    }
    ._profilePreview_gzau3_63, ._container_gzau3_1 {
        display: none !important;
        visibility: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True
)


def check_password():
    """Returns `True` if the user had a correct password."""

    def login_form():
        """Form with widgets to collect user information"""
        with st.form("Credentials"):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.form_submit_button("Log in", on_click=password_entered)

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["username"] in st.secrets[
            "passwords"
        ] and hmac.compare_digest(
            st.session_state["password"],
            st.secrets.passwords[st.session_state["username"]],
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the username or password.
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    # Return True if the username + password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show inputs for username + password.
    login_form()
    if "password_correct" in st.session_state:
        st.error("😕 User not known or password incorrect")
    return False

if not check_password():
    st.stop()

def connect():
    """Connect to MySQL database."""
    try:
        db_config = {
           'host': st.secrets["db_host"],
           'user': st.secrets["db_user"],
           'password': st.secrets["db_password"],
           'database': st.secrets["db_database"]
       }
        print('Connecting to MySQL database...')
        conn = mysql.connector.connect(**db_config)
        if conn.is_connected():
            print('Connected to MySQL database')
            return conn
    except Error as e:
        print(e)
    return None

def disconnect(conn):
    """Disconnect from MySQL database."""
    if conn is not None and conn.is_connected():
        conn.close()
        print('Disconnected from MySQL database')

# Base URL of your Flask app
BASE_URL = st.secrets["BASE_URL"]

def search_company():
    st.title("Search Company")
    search_term = st.text_input("Enter company name to search:")
    page = st.number_input("Page number", min_value=1, value=1)
    per_page = st.number_input("Results per page", min_value=1, value=10)

    if st.button("Search"):
        response = requests.get(f"{BASE_URL}/getallcompany", params={
            "search_term": search_term,
            "page": page,
            "per_page": per_page
        })
        if response.status_code == 200:
            companies = response.json().get('companies', [])
            st.write("### Search Results")
            for company in companies:
                st.write(f"ID: {company['id']}, Name: {company['name']}, Country: {company['country']}")
            st.write(f"Page: {response.json().get('page')}, Total: {response.json().get('total')}")
        else:
            st.error("Failed to fetch companies")

def update_company_details(company=None):
    st.title("Update Company Details")
    
    try:
        conn = connect()
        if conn is None:
            st.error('Failed to connect to the database')
            return
        
        cursor = conn.cursor()
        # Fetch unique country ISO codes for the dropdown
        cursor.execute("SELECT DISTINCT country_iso_code FROM d_company_details")
        countries = [row[0] for row in cursor.fetchall()]
        
        company_id = st.text_input("Enter Company ID:", value=company['id'] if company else "")
        new_name = st.text_input("Updated Company Name:", value=company['name'] if company else "")
        new_industry = st.text_input("Updated Industry:", value=company['industry'] if company else "")
        new_country_iso_code = st.selectbox("Updated Country:", options=[""] + countries, index=countries.index(company['country']) if company else 0)
        
        if st.button("Update"):
            response = requests.post(f"{BASE_URL}/company/edit", data={
                "company_id": company_id,
                "name": new_name,
                "industry": new_industry,
                "country_iso_code": new_country_iso_code
            })
            if response.status_code == 200:
                st.success("Company details updated successfully")
                st.write(response.json())
            else:
                st.error("Failed to update company details")
                st.write(response.json())
        
        cursor.close()
        
    except Exception as e:
        st.error(f"Error: {str(e)}")
    finally:
        if conn and conn.is_connected():
            disconnect(conn)

def delete_company(company_id=None):
    st.title("Delete Company")
    company_id_input = st.text_input("Enter Company ID to delete:", value=company_id if company_id else "")
    if st.button("Delete"):
        response = requests.get(f"{BASE_URL}/deleteCompany", params={"company_id": company_id_input})
        if response.status_code == 200:
            st.success("Company deleted successfully")
            st.write(response.json())
        else:
            st.error("Failed to delete company")
            st.write(response.json())

def add_company_details():
    st.title("Add Company Details")
    
    try:
        conn = connect()
        if conn is None:
            st.error('Failed to connect to the database')
            return
        
        cursor = conn.cursor()
        # Fetch unique country ISO codes for the dropdown
        cursor.execute("SELECT DISTINCT country_iso_code FROM d_company_details")
        countries = [row[0] for row in cursor.fetchall()]
        
        company_name = st.text_input("Company Name:")
        country_iso_code = st.selectbox("Country:", options=[""] + countries)
        industry = st.text_input("Industry:")

        if st.button("Add Company"):
            response = requests.post(f"{BASE_URL}/addCompanyDetails", json={
                "company_name": company_name,
                "country_iso_code": country_iso_code,
                "industry_name": industry
            })
            if response.status_code == 200:
                st.success("Company added successfully")
                st.write(response.json())
            else:
                st.error("Failed to add company")
                st.write(response.json())
        
        cursor.close()
        
    except Exception as e:
        st.error(f"Error: {str(e)}")
    finally:
        if conn and conn.is_connected():
            disconnect(conn)
    

def search_companies_by_name_and_country():
    st.title("Search Company")
    # Initialize session state for modals
    if 'edit_company_id' not in st.session_state:
        st.session_state.edit_company_id = None
    if 'delete_company_id' not in st.session_state:
        st.session_state.delete_company_id = None
    try:
        conn = connect()
        if conn is None:
            st.error('Failed to connect to the database')
            return
        
        cursor = conn.cursor()
        # Fetch unique country ISO codes for the dropdown
        cursor.execute("SELECT DISTINCT country_iso_code FROM d_company_details")
        countries = [row[0] for row in cursor.fetchall()]
        search_term = st.text_input("Enter company name to search:")
        country = st.selectbox("Select country (optional):", options=[""] + countries)
        if st.button("Search"):
            # Construct the query based on the presence of search_term and country
            if search_term and country:
                query = """
                SELECT company_id, name, country_iso_code, industry
                FROM d_company_details
                WHERE name LIKE %s AND country_iso_code = %s
                """
                cursor.execute(query, ('%' + search_term + '%', country))
            elif search_term:
                query = """
                SELECT company_id, name, country_iso_code, industry
                FROM d_company_details
                WHERE name LIKE %s
                """
                cursor.execute(query, ('%' + search_term + '%',))
            elif country:
                query = """
                SELECT company_id, name, country_iso_code, industry
                FROM d_company_details
                WHERE country_iso_code = %s
                """
                cursor.execute(query, (country,))
            else:
                st.error("Please enter a search term or select a country.")
                return
            
            companies = [{"id": row[0], "name": row[1], "country": row[2], "industry": row[3]} for row in cursor.fetchall()]
            
            st.write("### Search Results")
            st.write(f"Total: {len(companies)}")
            st.table(companies)

        cursor.close()
        
    except Exception as e:
        st.error(f"Error: {str(e)}")
    finally:
        if conn and conn.is_connected():
            disconnect(conn)


# Streamlit app navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Search Company", "Add New Company", "Update Company Details", "Delete Company"])

if page == "Search Company":
    search_companies_by_name_and_country()
elif page == "Add New Company":
    add_company_details()
elif page == "Update Company Details":
    update_company_details()
elif page == "Delete Company":
    delete_company()
