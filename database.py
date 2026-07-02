import streamlit as st
import mysql.connector
from mysql.connector import Error, pooling


def get_secret(cle, valeur_locale):
    """Lit les secrets Streamlit en ligne, et garde XAMPP en local."""
    try:
        return st.secrets["mysql"].get(cle, valeur_locale)
    except Exception:
        return valeur_locale


@st.cache_resource(show_spinner=False)
def get_pool(host, user, password, database, port):
    """Crée un pool de connexions MySQL pour éviter de reconnecter lentement à chaque action."""
    config = {
        "host": host,
        "user": user,
        "password": password,
        "database": database,
        "port": int(port),
        "connection_timeout": 10,
        "autocommit": False,
    }

    # Aiven / serveur distant : connexion SSL activée
    if host not in ["localhost", "127.0.0.1"]:
        config["ssl_disabled"] = False

    return pooling.MySQLConnectionPool(
        pool_name="jordybusiness_pool",
        pool_size=5,
        pool_reset_session=True,
        **config,
    )


def get_connection():
    try:
        host = get_secret("host", "localhost")
        user = get_secret("user", "root")
        password = get_secret("password", "")
        database = get_secret("database", "jordy_taches")
        port = int(get_secret("port", 3306))

        pool = get_pool(host, user, password, database, port)
        return pool.get_connection()

    except Error as e:
        print("Erreur de connexion à MySQL :", e)
        try:
            st.error(f"Erreur MySQL détaillée : {e}")
        except Exception:
            pass
        return None
