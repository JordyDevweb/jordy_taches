import mysql.connector
from mysql.connector import Error


def get_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="jordy_taches"
        )
        return connection

    except Error as e:
        print("Erreur de connexion à MySQL :", e)
        return None