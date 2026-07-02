import re
import mysql.connector


HOST = "mysql-5bd6868-baloujordy28-6f58.l.aivencloud.com"
PORT = 18487
USER = "avnadmin"
DATABASE = "defaultdb"
SQL_FILE = r"C:\Users\acer\Desktop\jordy_taches\jordy_taches.sql"


def nettoyer_sql(contenu):
    lignes_nettoyees = []

    for ligne in contenu.splitlines():
        ligne_strip = ligne.strip()
        ligne_upper = ligne_strip.upper()

        if ligne_upper.startswith("CREATE DATABASE"):
            continue

        if ligne_upper.startswith("USE "):
            continue

        if ligne_upper.startswith("DROP DATABASE"):
            continue

        lignes_nettoyees.append(ligne)

    contenu = "\n".join(lignes_nettoyees)

    contenu = re.sub(r"--.*", "", contenu)

    return contenu


def decouper_requetes(contenu):
    requetes = []
    requete = ""

    for ligne in contenu.splitlines():
        requete += ligne + "\n"

        if ligne.strip().endswith(";"):
            requetes.append(requete.strip())
            requete = ""

    if requete.strip():
        requetes.append(requete.strip())

    return requetes


def main():
    password = input("Mot de passe Aiven : ").strip()

    if password == "":
        print("Erreur : le mot de passe est vide.")
        return

    print("Connexion à Aiven MySQL...")

    connection = mysql.connector.connect(
        host=HOST,
        port=PORT,
        user=USER,
        password=password,
        database=DATABASE,
        ssl_disabled=False
    )

    cursor = connection.cursor()

    print("Désactivation temporaire de sql_require_primary_key...")

    try:
        cursor.execute("SET SESSION sql_require_primary_key = 0;")
        print("OK : sql_require_primary_key désactivé pour cette session.")
    except Exception as e:
        print("Impossible de désactiver sql_require_primary_key :", e)

    print("Nettoyage des anciennes tables si elles existent...")

    tables = [
        "executions_paiements",
        "reservations",
        "paiements_programmes",
        "alertes",
        "depenses",
        "taches_recurrentes",
        "taches",
        "budgets",
        "utilisateurs"
    ]

    cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")

    for table in tables:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS `{table}`;")
            print(f"Table supprimée si existante : {table}")
        except Exception as e:
            print(f"Erreur suppression {table} :", e)

    cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

    print("Lecture du fichier SQL...")

    with open(SQL_FILE, "r", encoding="utf-8") as fichier:
        contenu = fichier.read()

    contenu = nettoyer_sql(contenu)
    requetes = decouper_requetes(contenu)

    print(f"{len(requetes)} requêtes trouvées. Import en cours...")

    erreurs = 0

    for index, requete in enumerate(requetes, start=1):
        if requete.strip():
            try:
                cursor.execute(requete)
                print(f"OK {index}/{len(requetes)}")
            except Exception as e:
                erreurs += 1
                print(f"Erreur requête {index} : {e}")
                print(requete[:300])
                print("-" * 60)

    connection.commit()

    cursor.execute("SHOW TABLES;")
    tables_importees = cursor.fetchall()

    print("\nTables importées :")
    for table in tables_importees:
        print("-", table[0])

    cursor.close()
    connection.close()

    if erreurs == 0:
        print("\nImport terminé avec succès.")
    else:
        print(f"\nImport terminé avec {erreurs} erreur(s).")


if __name__ == "__main__":
    main()