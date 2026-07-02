import streamlit as st
import mysql.connector
from mysql.connector import Error


def get_secret(cle, valeur_locale):
    try:
        return st.secrets["mysql"].get(cle, valeur_locale)
    except Exception:
        return valeur_locale


def get_connection():
    try:
        connection = mysql.connector.connect(
            host=get_secret("host", "localhost"),
            user=get_secret("user", "root"),
            password=get_secret("password", ""),
            database=get_secret("database", "jordy_taches"),
            port=int(get_secret("port", 3306))
        )
        return connection

    except Error as e:
        print("Erreur de connexion à MySQL :", e)
        return None