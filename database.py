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
        host = get_secret("host", "localhost")

        config = {
            "host": host,
            "user": get_secret("user", "root"),
            "password": get_secret("password", ""),
            "database": get_secret("database", "jordy_taches"),
            "port": int(get_secret("port", 3306)),
            "connection_timeout": 15,
            "autocommit": False,
        }

        if host not in ["localhost", "127.0.0.1"]:
            config["ssl_disabled"] = False

        connection = mysql.connector.connect(**config)
        return connection

    except Error as e:
        print("Erreur de connexion à MySQL :", e)

        try:
            st.error(f"Erreur MySQL détaillée : {e}")
        except Exception:
            pass

        return None