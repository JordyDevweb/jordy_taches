import calendar
import html
import textwrap
import io
import base64
from datetime import date, datetime, timedelta

import bcrypt
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from database import get_connection


st.set_page_config(
    page_title="jordy_taches",
    page_icon="JB",
    layout="wide",
    initial_sidebar_state="expanded"
)


CATEGORIES_TACHES = [
    "Études",
    "Travail",
    "Maison",
    "Finance",
    "Santé",
    "Courses",
    "Personnel",
    "Autre"
]

CATEGORIES_DEPENSES = [
    "Logement",
    "Nourriture",
    "Transport",
    "Facture",
    "Loisirs",
    "Santé",
    "Études",
    "Courses",
    "Maison",
    "Autre"
]

PRIORITES = ["basse", "moyenne", "haute"]
STATUTS = ["a_faire", "en_cours", "terminee"]
MODES_PAIEMENT = ["Espèces", "Carte bancaire", "Mobile Money", "Virement", "Autre"]

MOIS_FR = {
    1: "Janvier",
    2: "Février",
    3: "Mars",
    4: "Avril",
    5: "Mai",
    6: "Juin",
    7: "Juillet",
    8: "Août",
    9: "Septembre",
    10: "Octobre",
    11: "Novembre",
    12: "Décembre",
}


def get_paiement_icone(categorie, titre):
    titre_lower = titre.lower() if titre else ""
    cat_lower = categorie.lower() if categorie else ""
    if "loyer" in titre_lower or "maison" in cat_lower or "logement" in cat_lower:
        return "house-door-fill"
    elif "internet" in titre_lower or "wifi" in titre_lower:
        return "wifi"
    elif "tel" in titre_lower or "téléphone" in titre_lower or "mobile" in titre_lower:
        return "telephone-fill"
    elif "élec" in titre_lower or "eau" in titre_lower or "facture" in cat_lower:
        return "lightning-charge-fill"
    elif "auto" in titre_lower or "voiture" in titre_lower or "transport" in cat_lower:
        return "car-front-fill"
    elif "nourriture" in cat_lower or "resto" in titre_lower or "courses" in cat_lower:
        return "cart-fill"
    return "credit-card-fill"


def draw_donut_chart(depenses):
    total = float(depenses["montant"].sum())
    resume = depenses.groupby("categorie")["montant"].sum().sort_values(ascending=False)
    
    color_palette = {
        "Logement": "#2563eb",     # Bleu royal moderne
        "Alimentation": "#16a34a",   # Vert émeraude moderne
        "Nourriture": "#16a34a",     # Vert émeraude moderne
        "Transport": "#f59e0b",    # Ambre/Orange moderne
        "Loisirs": "#7c3aed",      # Violet moderne
        "Facture": "#06b6d4",      # Cyan moderne
        "Autre": "#6b7280",        # Gris moderne
        "Courses": "#6b7280",      # Gris moderne
        "Maison": "#8b5cf6",       # Violet clair moderne
        "Personnel": "#94a3b8"     # Gris ardoise moderne
    }
    
    colors = [color_palette.get(cat, "#6c757d") for cat in resume.index]
    
    fig, ax = plt.subplots(figsize=(3, 3), facecolor='none')
    ax.set_facecolor('none')
    
    # Donut pie
    wedges, texts = ax.pie(
        resume.values,
        colors=colors,
        startangle=90,
        wedgeprops={"width": 0.28, "edgecolor": "white", "linewidth": 1.5},
        radius=1.0
    )
    
    # Text in center
    total_str = f"{total:,.2f}".replace(",", " ").replace(".", ",") + " €"
    ax.text(0, 0.08, total_str, ha='center', va='center', fontsize=11, fontweight='bold', color='#1e293b')
    ax.text(0, -0.18, "Total", ha='center', va='center', fontsize=8, color='#64748b')
    
    # Hide axes
    ax.axis('equal')
    plt.tight_layout()
    
    return fig, resume, total, color_palette


def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150, transparent=True)
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return "data:image/png;base64," + img_str


def get_taches_recentes_html(df):
    if df.empty:
        return "<div class='jb-muted' style='padding:20px 0;'>Aucune tâche récente.</div>"

    # En-tête du tableau
    html_code = """
<div style="width:100%;">
<div style="display:grid; grid-template-columns:2fr 1fr 1.2fr 1fr 28px; gap:8px; padding:8px 0 12px 0; border-bottom:2px solid #f1f5f9; margin-bottom:4px;">
<span style="color:#94a3b8; font-size:11px; font-weight:800; text-transform:uppercase; letter-spacing:0.05em;">Tâche</span>
<span style="color:#94a3b8; font-size:11px; font-weight:800; text-transform:uppercase; letter-spacing:0.05em;">Catégorie</span>
<span style="color:#94a3b8; font-size:11px; font-weight:800; text-transform:uppercase; letter-spacing:0.05em;">Échéance</span>
<span style="color:#94a3b8; font-size:11px; font-weight:800; text-transform:uppercase; letter-spacing:0.05em;">Statut</span>
<span></span>
</div>
"""

    maintenant = datetime.now()

    for _, row in df.iterrows():
        titre = nettoyer(row["titre"])
        categorie = nettoyer(row["categorie"])
        statut = row["statut"]
        date_limite = row["date_limite"]
        heure_limite = row["heure_limite"]

        # Vérifier si en retard
        if statut != "terminee" and not pd.isna(date_limite):
            date_lim_val = pd.to_datetime(date_limite).date()
            heure_lim_val = convertir_heure_mysql(heure_limite) if not pd.isna(heure_limite) else None
            if heure_lim_val:
                moment_limite = datetime.combine(date_lim_val, heure_lim_val)
            else:
                moment_limite = datetime.combine(date_lim_val, datetime.max.time())
            if maintenant > moment_limite:
                statut = "en_retard"

        # Checkbox et style selon statut
        if statut == "terminee":
            checkbox = '<i class="bi bi-check-square-fill" style="color:#16a34a; font-size:15px; flex-shrink:0;"></i>'
            titre_style = 'text-decoration:line-through; color:#94a3b8; font-size:13px;'
            statut_pill = '<span style="background:#dcfce7; color:#166534; padding:3px 10px; border-radius:999px; font-size:11px; font-weight:700; white-space:nowrap;">Terminée</span>'
        elif statut == "en_retard":
            checkbox = '<i class="bi bi-square" style="color:#dc2626; font-size:15px; flex-shrink:0;"></i>'
            titre_style = 'color:#dc2626; font-weight:600; font-size:13px;'
            statut_pill = '<span style="background:#fee2e2; color:#991b1b; padding:3px 10px; border-radius:999px; font-size:11px; font-weight:700; white-space:nowrap;">En retard</span>'
        elif statut == "en_cours":
            checkbox = '<i class="bi bi-square" style="color:#2563eb; font-size:15px; flex-shrink:0;"></i>'
            titre_style = 'color:#1e293b; font-weight:500; font-size:13px;'
            statut_pill = '<span style="background:#dbeafe; color:#1d4ed8; padding:3px 10px; border-radius:999px; font-size:11px; font-weight:700; white-space:nowrap;">En cours</span>'
        else:
            checkbox = '<i class="bi bi-square" style="color:#cbd5e1; font-size:15px; flex-shrink:0;"></i>'
            titre_style = 'color:#475569; font-weight:500; font-size:13px;'
            statut_pill = '<span style="background:#fef3c7; color:#92400e; padding:3px 10px; border-radius:999px; font-size:11px; font-weight:700; white-space:nowrap;">À faire</span>'

        # Catégorie pill couleur
        cat_colors = {
            "Travail": ("bg:#dbeafe", "color:#1d4ed8"),
            "Finance": ("bg:#dcfce7", "color:#166534"),
            "Personnel": ("bg:#f1f5f9", "color:#475569"),
            "Maison": ("bg:#f5f3ff", "color:#6d28d9"),
            "Courses": ("bg:#fef3c7", "color:#92400e"),
            "Études": ("bg:#f0fdf4", "color:#166534"),
            "Santé": ("bg:#fef2f2", "color:#991b1b"),
        }
        cat_bg = "#f1f5f9"
        cat_fg = "#475569"
        if categorie in cat_colors:
            bg_s, fg_s = cat_colors[categorie]
            cat_bg = bg_s.replace("bg:", "")
            cat_fg = fg_s.replace("color:", "")

        # Format date
        date_str = ""
        if not pd.isna(date_limite):
            try:
                if isinstance(date_limite, str):
                    dt = datetime.strptime(date_limite, "%Y-%m-%d")
                else:
                    dt = date_limite
                date_str = f"{dt.day} {nom_mois(dt.month)[:3].lower()}. {dt.year}"
            except Exception:
                date_str = str(date_limite)[:10]

        html_code += f"""
<div style="display:grid; grid-template-columns:2fr 1fr 1.2fr 1fr 28px; gap:8px; align-items:center; padding:10px 0; border-bottom:1px solid #f8fafc;">
<div style="display:flex; align-items:center; gap:8px; min-width:0;">
{checkbox}
<span style="{titre_style} overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{titre}</span>
</div>
<div>
<span style="background:{cat_bg}; color:{cat_fg}; padding:3px 10px; border-radius:999px; font-size:11px; font-weight:700; white-space:nowrap;">{categorie}</span>
</div>
<div style="display:flex; align-items:center; gap:4px; color:#64748b; font-size:12px; white-space:nowrap;">
<i class="bi bi-calendar3" style="font-size:12px;"></i>
<span>{date_str}</span>
</div>
<div>{statut_pill}</div>
<div style="color:#cbd5e1; text-align:center;">
<i class="bi bi-three-dots-vertical" style="font-size:13px; cursor:pointer;"></i>
</div>
</div>
"""

    html_code += "</div>"
    return html_code


def charger_css():
    try:
        with open("style.css", "r", encoding="utf-8") as fichier:
            st.markdown(f"<style>{fichier.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("Le fichier style.css est introuvable.")


charger_css()

st.markdown(
    """
    <link 
        href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" 
        rel="stylesheet"
    >
    <link 
        href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" 
        rel="stylesheet"
    >
    """,
    unsafe_allow_html=True
)

components.html(
    """
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        console.log("JordyBusiness dashboard chargé.");
    </script>
    """,
    height=0
)


def md(code):
    cleaned_lines = [line.strip() for line in str(code).splitlines()]
    cleaned_code = "\n".join(cleaned_lines)
    st.markdown(cleaned_code, unsafe_allow_html=True)


def nettoyer(texte):
    if texte is None:
        return ""
    return html.escape(str(texte))


def connexion_mysql():
    connection = get_connection()

    if connection is None:
        st.error("Connexion MySQL impossible. Vérifie XAMPP, MySQL et database.py.")
        return None

    return connection


def assurer_structure_profil():
    """Ajoute automatiquement les colonnes du profil si elles n'existent pas."""
    connection = get_connection()
    if connection is None:
        return

    cursor = connection.cursor()
    colonnes = [
        "ALTER TABLE utilisateurs ADD COLUMN telephone VARCHAR(30) NULL",
        "ALTER TABLE utilisateurs ADD COLUMN adresse TEXT NULL",
        "ALTER TABLE utilisateurs ADD COLUMN photo_profil LONGTEXT NULL",
    ]

    for sql in colonnes:
        try:
            cursor.execute(sql)
        except Exception:
            # Colonne déjà existante ou droits insuffisants : on ne bloque pas l'application.
            pass

    connection.commit()
    cursor.close()
    connection.close()


def id_utilisateur():
    return st.session_state["utilisateur"]["id"]


def nom_mois(mois):
    return MOIS_FR.get(int(mois), str(mois))


def format_euro(valeur):
    try:
        valeur = float(valeur)
    except Exception:
        valeur = 0.0

    return f"{valeur:,.2f}".replace(",", " ").replace(".", ",") + " €"


def convertir_heure_mysql(valeur):
    if valeur is None or pd.isna(valeur):
        return None

    if hasattr(valeur, "hour"):
        return valeur

    if isinstance(valeur, timedelta):
        total_secondes = int(valeur.total_seconds())
        heures = total_secondes // 3600
        minutes = (total_secondes % 3600) // 60
        secondes = total_secondes % 60
        return datetime.strptime(f"{heures:02d}:{minutes:02d}:{secondes:02d}", "%H:%M:%S").time()

    if isinstance(valeur, str):
        try:
            return datetime.strptime(valeur, "%H:%M:%S").time()
        except ValueError:
            try:
                return datetime.strptime(valeur, "%H:%M").time()
            except ValueError:
                return None

    return None


def date_suivante(prochaine_date, frequence, jour_mois=None, jour_semaine=None, mois_annuel=None):
    if isinstance(prochaine_date, str):
        prochaine_date = datetime.strptime(prochaine_date, "%Y-%m-%d").date()

    if frequence == "hebdomadaire":
        return prochaine_date + timedelta(days=7)

    if frequence == "annuelle":
        annee = prochaine_date.year + 1
        mois = int(mois_annuel or prochaine_date.month)
        jour = int(jour_mois or prochaine_date.day)
        dernier_jour = calendar.monthrange(annee, mois)[1]
        jour = min(jour, dernier_jour)
        return date(annee, mois, jour)

    annee = prochaine_date.year
    mois = prochaine_date.month + 1

    if mois > 12:
        mois = 1
        annee += 1

    jour = int(jour_mois or prochaine_date.day)
    dernier_jour = calendar.monthrange(annee, mois)[1]
    jour = min(jour, dernier_jour)

    return date(annee, mois, jour)


def afficher_tableau(df):
    if df.empty:
        st.info("Aucune donnée à afficher.")
        return

    df_affiche = df.copy()

    for colonne in ["montant", "montant_estime", "limite_mensuelle"]:
        if colonne in df_affiche.columns:
            df_affiche[colonne] = df_affiche[colonne].apply(format_euro)

    for colonne in ["liee_depense", "depense_creee", "active", "lue"]:
        if colonne in df_affiche.columns:
            df_affiche[colonne] = df_affiche[colonne].apply(lambda x: "Oui" if x else "Non")

    table_html = df_affiche.to_html(
        index=False,
        classes="table table-striped table-hover table-bordered align-middle",
        border=0,
        escape=False
    )

    st.markdown(table_html, unsafe_allow_html=True)


def badge_statut(statut):
    if statut == "terminee":
        return "<span class='jb-pill jb-pill-green'>Terminée</span>"
    if statut == "en_cours":
        return "<span class='jb-pill jb-pill-blue'>En cours</span>"
    return "<span class='jb-pill jb-pill-orange'>À faire</span>"


def badge_priorite(priorite):
    if priorite == "haute":
        return "<span class='jb-pill jb-pill-red'>Haute</span>"
    if priorite == "moyenne":
        return "<span class='jb-pill jb-pill-blue'>Moyenne</span>"
    return "<span class='jb-pill jb-pill-green'>Basse</span>"


def hacher_mot_de_passe(mot_de_passe):
    return bcrypt.hashpw(
        mot_de_passe.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")


def verifier_mot_de_passe(mot_de_passe, mot_de_passe_hash):
    return bcrypt.checkpw(
        mot_de_passe.encode("utf-8"),
        mot_de_passe_hash.encode("utf-8")
    )


def fichier_image_vers_base64(fichier):
    """Convertit une image uploadée en base64 pour l'enregistrer dans MySQL."""
    if fichier is None:
        return None

    donnees = fichier.getvalue()

    # Limite simple pour éviter d'alourdir la base de données.
    if len(donnees) > 2 * 1024 * 1024:
        return "IMAGE_TROP_GRANDE"

    image_base64 = base64.b64encode(donnees).decode("utf-8")
    return f"data:{fichier.type};base64,{image_base64}"


def photo_profil_html(utilisateur, taille=128):
    """Affiche la photo de profil ou une initiale professionnelle."""
    photo = utilisateur.get("photo_profil") if utilisateur else None
    nom = utilisateur.get("nom", "Utilisateur") if utilisateur else "Utilisateur"
    initiale = nom[0].upper() if nom else "U"

    if photo:
        return f"""
        <img src="{photo}" class="profile-avatar-img" style="width:{taille}px;height:{taille}px;">
        """

    return f"""
    <div class="profile-avatar-fallback" style="width:{taille}px;height:{taille}px;">
        {initiale}
    </div>
    """


def recharger_utilisateur_session():
    connection = connexion_mysql()
    if connection is None:
        return False

    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM utilisateurs WHERE id = %s LIMIT 1", (id_utilisateur(),))
    utilisateur = cursor.fetchone()
    cursor.close()
    connection.close()

    if utilisateur:
        st.session_state["utilisateur"] = utilisateur
        return True
    return False


def mettre_a_jour_profil(nom, email, telephone, adresse, photo_base64=None):
    email = email.strip().lower()

    connection = connexion_mysql()
    if connection is None:
        return False, "Connexion MySQL impossible."

    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id FROM utilisateurs
        WHERE email = %s AND id != %s
        LIMIT 1
        """,
        (email, id_utilisateur())
    )
    email_existe = cursor.fetchone()

    if email_existe:
        cursor.close()
        connection.close()
        return False, "Cet email est déjà utilisé par un autre compte."

    if photo_base64:
        cursor.execute(
            """
            UPDATE utilisateurs
            SET nom = %s, email = %s, telephone = %s, adresse = %s, photo_profil = %s
            WHERE id = %s
            """,
            (nom.strip(), email, telephone.strip(), adresse.strip(), photo_base64, id_utilisateur())
        )
    else:
        cursor.execute(
            """
            UPDATE utilisateurs
            SET nom = %s, email = %s, telephone = %s, adresse = %s
            WHERE id = %s
            """,
            (nom.strip(), email, telephone.strip(), adresse.strip(), id_utilisateur())
        )

    connection.commit()
    cursor.close()
    connection.close()
    recharger_utilisateur_session()

    return True, "Profil mis à jour avec succès."


def changer_mot_de_passe(mot_de_passe_actuel, nouveau_mot_de_passe, confirmation):
    utilisateur = st.session_state["utilisateur"]

    if not verifier_mot_de_passe(mot_de_passe_actuel, utilisateur["mot_de_passe_hash"]):
        return False, "Le mot de passe actuel est incorrect."

    if nouveau_mot_de_passe != confirmation:
        return False, "Les nouveaux mots de passe ne correspondent pas."

    if len(nouveau_mot_de_passe) < 6:
        return False, "Le nouveau mot de passe doit contenir au moins 6 caractères."

    nouveau_hash = hacher_mot_de_passe(nouveau_mot_de_passe)

    connection = connexion_mysql()
    if connection is None:
        return False, "Connexion MySQL impossible."

    cursor = connection.cursor()
    cursor.execute(
        "UPDATE utilisateurs SET mot_de_passe_hash = %s WHERE id = %s",
        (nouveau_hash, id_utilisateur())
    )
    connection.commit()
    cursor.close()
    connection.close()
    recharger_utilisateur_session()

    return True, "Mot de passe modifié avec succès."


def supprimer_compte_utilisateur(mot_de_passe):
    utilisateur = st.session_state["utilisateur"]

    if not verifier_mot_de_passe(mot_de_passe, utilisateur["mot_de_passe_hash"]):
        return False, "Mot de passe incorrect. Suppression annulée."

    connection = connexion_mysql()
    if connection is None:
        return False, "Connexion MySQL impossible."

    cursor = connection.cursor()
    cursor.execute("DELETE FROM utilisateurs WHERE id = %s", (id_utilisateur(),))
    connection.commit()
    cursor.close()
    connection.close()

    st.session_state["connecte"] = False
    st.session_state["utilisateur"] = None
    st.session_state.pop("automatisations_lancees", None)
    st.session_state["current_page"] = "dashboard"

    return True, "Compte supprimé avec succès."


def creer_utilisateur(nom, email, mot_de_passe):
    email = email.strip().lower()

    connection = connexion_mysql()
    if connection is None:
        return False, "Connexion MySQL impossible."

    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT id FROM utilisateurs WHERE email = %s", (email,))
    existe = cursor.fetchone()

    if existe:
        cursor.close()
        connection.close()
        return False, "Cet email est déjà utilisé."

    cursor.execute(
        """
        INSERT INTO utilisateurs (nom, email, mot_de_passe_hash)
        VALUES (%s, %s, %s)
        """,
        (nom.strip(), email, hacher_mot_de_passe(mot_de_passe))
    )

    connection.commit()
    cursor.close()
    connection.close()

    return True, "Compte créé avec succès."


def connecter_utilisateur(email, mot_de_passe):
    email = email.strip().lower()

    connection = connexion_mysql()
    if connection is None:
        return None

    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM utilisateurs WHERE email = %s", (email,))
    utilisateur = cursor.fetchone()

    cursor.close()
    connection.close()

    if utilisateur and verifier_mot_de_passe(mot_de_passe, utilisateur["mot_de_passe_hash"]):
        return utilisateur

    return None


def creer_alerte(titre, message, type_alerte="info"):
    connection = connexion_mysql()
    if connection is None:
        return

    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT id
        FROM alertes
        WHERE utilisateur_id = %s
        AND titre = %s
        AND message = %s
        AND DATE(cree_le) = CURDATE()
        LIMIT 1
        """,
        (id_utilisateur(), titre, message)
    )

    existe = cursor.fetchone()

    if not existe:
        cursor.execute(
            """
            INSERT INTO alertes (utilisateur_id, titre, message, type_alerte)
            VALUES (%s, %s, %s, %s)
            """,
            (id_utilisateur(), titre, message, type_alerte)
        )

    connection.commit()
    cursor.close()
    connection.close()


def recuperer_alertes(limite=20):
    connection = connexion_mysql()
    if connection is None:
        return pd.DataFrame()

    query = """
    SELECT id, titre, message, type_alerte, lue, cree_le
    FROM alertes
    WHERE utilisateur_id = %s
    ORDER BY cree_le DESC
    LIMIT %s
    """

    df = pd.read_sql(query, connection, params=(id_utilisateur(), limite))
    connection.close()

    return df


def marquer_alertes_lues():
    connection = connexion_mysql()
    if connection is None:
        return False, "Connexion MySQL impossible."

    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE alertes
        SET lue = TRUE
        WHERE utilisateur_id = %s
        """,
        (id_utilisateur(),)
    )

    connection.commit()
    cursor.close()
    connection.close()

    return True, "Toutes les alertes ont été marquées comme lues."


def recuperer_budget_mois(mois, annee):
    connection = connexion_mysql()
    if connection is None:
        return 0.0

    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT limite_mensuelle
        FROM budgets
        WHERE utilisateur_id = %s
        AND categorie = 'Global'
        AND mois = %s
        AND annee = %s
        LIMIT 1
        """,
        (id_utilisateur(), mois, annee)
    )

    budget = cursor.fetchone()

    cursor.close()
    connection.close()

    if budget:
        return float(budget["limite_mensuelle"])

    return 0.0


def enregistrer_budget_mois(mois, annee, montant):
    connection = connexion_mysql()
    if connection is None:
        return False, "Connexion MySQL impossible."

    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT id
        FROM budgets
        WHERE utilisateur_id = %s
        AND categorie = 'Global'
        AND mois = %s
        AND annee = %s
        LIMIT 1
        """,
        (id_utilisateur(), mois, annee)
    )

    budget = cursor.fetchone()

    if budget:
        cursor.execute(
            """
            UPDATE budgets
            SET limite_mensuelle = %s
            WHERE id = %s
            """,
            (montant, budget["id"])
        )
    else:
        cursor.execute(
            """
            INSERT INTO budgets (utilisateur_id, categorie, limite_mensuelle, mois, annee)
            VALUES (%s, 'Global', %s, %s, %s)
            """,
            (id_utilisateur(), montant, mois, annee)
        )

    connection.commit()
    cursor.close()
    connection.close()

    return True, f"Capital de {nom_mois(mois)} {annee} enregistré."


def total_depenses_mois(mois, annee):
    connection = connexion_mysql()
    if connection is None:
        return 0.0

    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT COALESCE(SUM(montant), 0) AS total
        FROM depenses
        WHERE utilisateur_id = %s
        AND MONTH(date_depense) = %s
        AND YEAR(date_depense) = %s
        """,
        (id_utilisateur(), mois, annee)
    )

    resultat = cursor.fetchone()

    cursor.close()
    connection.close()

    return float(resultat["total"])


def ajouter_tache(titre, description, categorie, priorite, date_limite, heure_limite, duree_minutes, liee_depense, montant_estime):
    connection = connexion_mysql()
    if connection is None:
        return False, "Connexion MySQL impossible."

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO taches
        (
            utilisateur_id, titre, description, categorie, priorite,
            date_limite, heure_limite, duree_minutes,
            liee_depense, montant_estime
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            id_utilisateur(),
            titre.strip(),
            description.strip(),
            categorie,
            priorite,
            date_limite,
            heure_limite,
            duree_minutes,
            int(liee_depense),
            montant_estime if liee_depense else None
        )
    )

    connection.commit()
    cursor.close()
    connection.close()

    return True, "Tâche ajoutée avec succès."


def recuperer_taches():
    connection = connexion_mysql()
    if connection is None:
        return pd.DataFrame()

    query = """
    SELECT
        id, titre, description, categorie, priorite, statut,
        date_limite, heure_limite, duree_minutes,
        liee_depense, montant_estime, depense_creee, cree_le
    FROM taches
    WHERE utilisateur_id = %s
    ORDER BY date_limite ASC, heure_limite ASC
    """

    df = pd.read_sql(query, connection, params=(id_utilisateur(),))
    connection.close()

    return df


def modifier_statut_tache(tache_id, nouveau_statut):
    connection = connexion_mysql()
    if connection is None:
        return False, "Connexion MySQL impossible."

    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM taches WHERE id = %s AND utilisateur_id = %s",
        (tache_id, id_utilisateur())
    )

    tache = cursor.fetchone()

    if not tache:
        cursor.close()
        connection.close()
        return False, "Tâche introuvable."

    cursor.execute(
        """
        UPDATE taches
        SET statut = %s
        WHERE id = %s AND utilisateur_id = %s
        """,
        (nouveau_statut, tache_id, id_utilisateur())
    )

    depense_creee = False

    if (
        nouveau_statut == "terminee"
        and tache["liee_depense"]
        and not tache["depense_creee"]
        and tache["montant_estime"] is not None
        and float(tache["montant_estime"]) > 0
    ):
        cursor.execute(
            """
            INSERT INTO depenses
            (utilisateur_id, titre, categorie, montant, date_depense, mode_paiement, note, tache_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                id_utilisateur(),
                tache["titre"],
                tache["categorie"],
                tache["montant_estime"],
                date.today(),
                "Non précisé",
                "Dépense créée automatiquement depuis une tâche terminée.",
                tache_id
            )
        )

        cursor.execute(
            """
            UPDATE taches
            SET depense_creee = TRUE
            WHERE id = %s AND utilisateur_id = %s
            """,
            (tache_id, id_utilisateur())
        )

        depense_creee = True

    connection.commit()
    cursor.close()
    connection.close()

    if depense_creee:
        creer_alerte(
            "Dépense automatique créée",
            f"La tâche « {tache['titre']} » a généré une dépense de {format_euro(tache['montant_estime'])}.",
            "succes"
        )
        return True, "Statut modifié. Une dépense a été créée automatiquement."

    return True, "Statut modifié avec succès."


def supprimer_tache(tache_id):
    connection = connexion_mysql()
    if connection is None:
        return False, "Connexion MySQL impossible."

    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM taches WHERE id = %s AND utilisateur_id = %s",
        (tache_id, id_utilisateur())
    )

    connection.commit()
    lignes = cursor.rowcount

    cursor.close()
    connection.close()

    if lignes == 0:
        return False, "Tâche introuvable."

    return True, "Tâche supprimée."


def ajouter_depense(titre, categorie, montant, date_depense, mode_paiement, note):
    connection = connexion_mysql()
    if connection is None:
        return False, "Connexion MySQL impossible."

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO depenses
        (utilisateur_id, titre, categorie, montant, date_depense, mode_paiement, note)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            id_utilisateur(),
            titre.strip(),
            categorie,
            montant,
            date_depense,
            mode_paiement,
            note.strip()
        )
    )

    connection.commit()
    cursor.close()
    connection.close()

    return True, "Dépense ajoutée."


def recuperer_depenses_mois(mois, annee):
    connection = connexion_mysql()
    if connection is None:
        return pd.DataFrame()

    query = """
    SELECT
        id, titre, categorie, montant, date_depense, mode_paiement, note, tache_id, cree_le
    FROM depenses
    WHERE utilisateur_id = %s
    AND MONTH(date_depense) = %s
    AND YEAR(date_depense) = %s
    ORDER BY date_depense DESC, id DESC
    """

    df = pd.read_sql(query, connection, params=(id_utilisateur(), mois, annee))
    connection.close()

    return df


def supprimer_depense(depense_id):
    connection = connexion_mysql()
    if connection is None:
        return False, "Connexion MySQL impossible."

    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM depenses WHERE id = %s AND utilisateur_id = %s",
        (depense_id, id_utilisateur())
    )

    connection.commit()
    lignes = cursor.rowcount

    cursor.close()
    connection.close()

    if lignes == 0:
        return False, "Dépense introuvable."

    return True, "Dépense supprimée."


def ajouter_paiement_programme(titre, description, categorie, montant, frequence, jour_mois, jour_semaine, mois_annuel, prochaine_date, mode_paiement):
    connection = connexion_mysql()
    if connection is None:
        return False, "Connexion MySQL impossible."

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO paiements_programmes
        (
            utilisateur_id, titre, description, categorie, montant,
            frequence, jour_mois, jour_semaine, mois_annuel,
            prochaine_date, mode_paiement, active
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
        """,
        (
            id_utilisateur(),
            titre.strip(),
            description.strip(),
            categorie,
            montant,
            frequence,
            jour_mois,
            jour_semaine,
            mois_annuel,
            prochaine_date,
            mode_paiement
        )
    )

    connection.commit()
    cursor.close()
    connection.close()

    return True, "Paiement programmé ajouté."


def recuperer_paiements_programmes():
    connection = connexion_mysql()
    if connection is None:
        return pd.DataFrame()

    query = """
    SELECT
        id, titre, categorie, montant, frequence, jour_mois,
        jour_semaine, mois_annuel, prochaine_date, mode_paiement, active, cree_le
    FROM paiements_programmes
    WHERE utilisateur_id = %s
    ORDER BY prochaine_date ASC
    """

    df = pd.read_sql(query, connection, params=(id_utilisateur(),))
    connection.close()

    return df


def changer_etat_paiement(paiement_id, actif):
    connection = connexion_mysql()
    if connection is None:
        return False, "Connexion MySQL impossible."

    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE paiements_programmes
        SET active = %s
        WHERE id = %s AND utilisateur_id = %s
        """,
        (int(actif), paiement_id, id_utilisateur())
    )

    connection.commit()
    cursor.close()
    connection.close()

    return True, "État du paiement mis à jour."


def supprimer_paiement(paiement_id):
    connection = connexion_mysql()
    if connection is None:
        return False, "Connexion MySQL impossible."

    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM paiements_programmes
        WHERE id = %s AND utilisateur_id = %s
        """,
        (paiement_id, id_utilisateur())
    )

    connection.commit()
    lignes = cursor.rowcount

    cursor.close()
    connection.close()

    if lignes == 0:
        return False, "Paiement introuvable."

    return True, "Paiement programmé supprimé."


def verifier_taches_en_retard():
    taches = recuperer_taches()

    if taches.empty:
        return

    maintenant = datetime.now()

    for _, tache in taches.iterrows():
        if tache["statut"] == "terminee":
            continue

        if pd.isna(tache["date_limite"]) or pd.isna(tache["heure_limite"]):
            continue

        date_limite = pd.to_datetime(tache["date_limite"]).date()
        heure_limite = convertir_heure_mysql(tache["heure_limite"])

        if heure_limite is None:
            continue

        moment_limite = datetime.combine(date_limite, heure_limite)

        if maintenant > moment_limite:
            creer_alerte(
                "Tâche en retard",
                f"La tâche « {tache['titre']} » devait être terminée le {date_limite} à {heure_limite}.",
                "attention"
            )


def verifier_paiements_programmes():
    connection = connexion_mysql()
    if connection is None:
        return

    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM paiements_programmes
        WHERE utilisateur_id = %s
        AND active = TRUE
        AND prochaine_date <= CURDATE()
        ORDER BY prochaine_date ASC
        """,
        (id_utilisateur(),)
    )

    paiements = cursor.fetchall()

    for paiement in paiements:
        paiement_id = paiement["id"]
        date_execution = paiement["prochaine_date"]
        mois = date_execution.month
        annee = date_execution.year
        montant = float(paiement["montant"])

        cursor.execute(
            """
            SELECT id
            FROM executions_paiements
            WHERE paiement_programme_id = %s
            AND date_execution = %s
            LIMIT 1
            """,
            (paiement_id, date_execution)
        )

        deja_execute = cursor.fetchone()

        if deja_execute:
            prochaine = date_suivante(
                date_execution,
                paiement["frequence"],
                paiement["jour_mois"],
                paiement["jour_semaine"],
                paiement["mois_annuel"]
            )

            cursor.execute(
                """
                UPDATE paiements_programmes
                SET prochaine_date = %s
                WHERE id = %s
                """,
                (prochaine, paiement_id)
            )

            continue

        budget = recuperer_budget_mois(mois, annee)
        total = total_depenses_mois(mois, annee)
        reste = budget - total

        if reste >= montant:
            cursor.execute(
                """
                INSERT INTO depenses
                (utilisateur_id, titre, categorie, montant, date_depense, mode_paiement, note)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    id_utilisateur(),
                    paiement["titre"],
                    paiement["categorie"],
                    montant,
                    date_execution,
                    paiement["mode_paiement"],
                    "Dépense créée automatiquement depuis un paiement programmé."
                )
            )

            depense_id = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO executions_paiements
                (paiement_programme_id, utilisateur_id, date_execution, statut, depense_id, message)
                VALUES (%s, %s, %s, 'execute', %s, %s)
                """,
                (
                    paiement_id,
                    id_utilisateur(),
                    date_execution,
                    depense_id,
                    "Paiement exécuté automatiquement."
                )
            )

            creer_alerte(
                "Paiement automatique exécuté",
                f"Le paiement « {paiement['titre']} » de {format_euro(montant)} a été ajouté aux dépenses.",
                "succes"
            )

        else:
            cursor.execute(
                """
                INSERT INTO executions_paiements
                (paiement_programme_id, utilisateur_id, date_execution, statut, depense_id, message)
                VALUES (%s, %s, %s, 'budget_insuffisant', NULL, %s)
                """,
                (
                    paiement_id,
                    id_utilisateur(),
                    date_execution,
                    "Budget insuffisant."
                )
            )

            creer_alerte(
                "Budget insuffisant",
                f"Le paiement « {paiement['titre']} » de {format_euro(montant)} est prévu, mais ton reste disponible est seulement de {format_euro(reste)}.",
                "danger"
            )

        prochaine = date_suivante(
            date_execution,
            paiement["frequence"],
            paiement["jour_mois"],
            paiement["jour_semaine"],
            paiement["mois_annuel"]
        )

        cursor.execute(
            """
            UPDATE paiements_programmes
            SET prochaine_date = %s
            WHERE id = %s
            """,
            (prochaine, paiement_id)
        )

    connection.commit()
    cursor.close()
    connection.close()


def lancer_automatisations():
    if "automatisations_lancees" not in st.session_state:
        verifier_taches_en_retard()
        verifier_paiements_programmes()
        st.session_state["automatisations_lancees"] = True




def afficher_graphique_donut(depenses):
    """Diagramme donut compact utilisé dans les pages simples."""
    if depenses.empty:
        st.info("Aucune dépense ce mois.")
        return

    fig, resume, total, couleurs = creer_figure_donut_depenses(depenses, figsize=(3.4, 3.4))
    st.pyplot(fig, use_container_width=False)
    plt.close(fig)


def couleurs_jb():
    return [
        "#1e3a8a",  # bleu business
        "#0f766e",  # vert pétrole
        "#c59b2d",  # doré
        "#6d28d9",  # violet sobre
        "#64748b",  # gris ardoise
        "#b91c1c",  # rouge sérieux
        "#0891b2",  # cyan profond
        "#92400e",  # brun orange
    ]


def creer_figure_donut_depenses(depenses, figsize=(4.8, 4.8)):
    resume = depenses.groupby("categorie")["montant"].sum().sort_values(ascending=False)
    total = float(resume.sum())
    couleurs = couleurs_jb()[:len(resume)]

    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    ax.pie(
        resume.values,
        startangle=90,
        colors=couleurs,
        wedgeprops={"width": 0.36, "edgecolor": "white", "linewidth": 2.5},
    )

    ax.text(0, 0.08, format_euro(total), ha="center", va="center", fontsize=13, fontweight="bold", color="#101828")
    ax.text(0, -0.13, "Total", ha="center", va="center", fontsize=10, color="#667085")
    ax.set(aspect="equal")
    ax.axis("off")
    plt.tight_layout()
    return fig, resume, total, couleurs


def creer_figure_barres_categories(depenses):
    resume = depenses.groupby("categorie")["montant"].sum().sort_values(ascending=True)
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.barh(resume.index, resume.values)
    ax.set_xlabel("Montant dépensé")
    ax.grid(axis="x", alpha=0.20)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", labelsize=9)
    ax.tick_params(axis="x", labelsize=9)
    for i, v in enumerate(resume.values):
        ax.text(v, i, "  " + format_euro(v), va="center", fontsize=9, color="#334155")
    plt.tight_layout()
    return fig


def creer_figure_depenses_journalieres(depenses, mois, annee):
    if depenses.empty:
        return None

    df = depenses.copy()
    df["date_depense"] = pd.to_datetime(df["date_depense"])
    jours_mois = calendar.monthrange(annee, mois)[1]
    index_jours = pd.date_range(start=date(annee, mois, 1), end=date(annee, mois, jours_mois), freq="D")
    serie = df.groupby("date_depense")["montant"].sum().reindex(index_jours, fill_value=0).cumsum()

    fig, ax = plt.subplots(figsize=(8.5, 3.4))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.plot(index_jours.day, serie.values, linewidth=2.8, marker="o", markersize=3.5)
    ax.fill_between(index_jours.day, serie.values, alpha=0.08)
    ax.set_xlabel("Jour du mois")
    ax.set_ylabel("Cumul")
    ax.grid(alpha=0.20)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=9)
    plt.tight_layout()
    return fig


def creer_figure_statuts_taches(taches):
    statuts = {
        "a_faire": "À faire",
        "en_cours": "En cours",
        "terminee": "Terminées",
    }

    if taches.empty:
        valeurs = pd.Series([0, 0, 0], index=list(statuts.keys()))
    else:
        valeurs = taches["statut"].value_counts().reindex(list(statuts.keys()), fill_value=0)

    labels = [statuts[k] for k in valeurs.index]

    fig, ax = plt.subplots(figsize=(6.0, 3.2))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.bar(labels, valeurs.values)
    ax.set_ylabel("Nombre de tâches")
    ax.grid(axis="y", alpha=0.20)
    ax.spines[["top", "right"]].set_visible(False)
    for i, v in enumerate(valeurs.values):
        ax.text(i, v + 0.05, str(int(v)), ha="center", fontsize=10, fontweight="bold")
    plt.tight_layout()
    return fig


def image_figure(fig):
    return fig_to_base64(fig)


def legend_depenses_html(resume, total, couleurs):
    html_rows = ""
    for index, (cat, val) in enumerate(resume.items()):
        couleur = couleurs[index % len(couleurs)]
        pct = (float(val) / total * 100) if total > 0 else 0
        html_rows += f"""
        <div class="jb-legend-row">
            <div class="jb-legend-left">
                <span class="jb-legend-dot" style="background:{couleur};"></span>
                <span>{nettoyer(cat)}</span>
            </div>
            <div class="jb-legend-right">
                <span>{pct:.1f}%</span>
                <strong>{format_euro(val)}</strong>
            </div>
        </div>
        """
    return html_rows


def afficher_bloc_grands_diagrammes(depenses, taches, mois, annee):
    """Section analytique large du tableau de bord."""
    md("""
    <div class="jb-section-title-row">
        <div>
            <div class="jb-section-title">Analyse visuelle</div>
            <div class="jb-section-subtitle">Vue complète des dépenses, de la progression et des tâches.</div>
        </div>
    </div>
    """)

    col_left, col_right = st.columns([1.15, 0.85])

    with col_left:
        if depenses.empty:
            md("""
            <div class="jb-chart-card jb-chart-large">
                <div class="jb-chart-title">Dépenses par catégorie</div>
                <div class="jb-empty-state">Aucune dépense enregistrée ce mois.</div>
            </div>
            """)
        else:
            fig, resume, total, couleurs = creer_figure_donut_depenses(depenses, figsize=(4.7, 4.7))
            img_src = image_figure(fig)
            legend = legend_depenses_html(resume, total, couleurs)
            md(f"""
            <div class="jb-chart-card jb-chart-large">
                <div class="jb-chart-head">
                    <div>
                        <div class="jb-chart-title">Dépenses par catégorie</div>
                        <div class="jb-chart-subtitle">Répartition du mois de {nom_mois(mois)} {annee}</div>
                    </div>
                    <div class="jb-chart-badge">{format_euro(total)}</div>
                </div>
                <div class="jb-chart-split">
                    <div class="jb-chart-image-wrap"><img src="{img_src}" /></div>
                    <div class="jb-chart-legend">{legend}</div>
                </div>
            </div>
            """)

    with col_right:
        fig_tasks = creer_figure_statuts_taches(taches)
        img_tasks = image_figure(fig_tasks)
        total_taches = len(taches) if not taches.empty else 0
        terminees = len(taches[taches["statut"] == "terminee"]) if not taches.empty else 0
        progression = (terminees / total_taches * 100) if total_taches > 0 else 0
        md(f"""
        <div class="jb-chart-card jb-chart-large">
            <div class="jb-chart-head">
                <div>
                    <div class="jb-chart-title">État des tâches</div>
                    <div class="jb-chart-subtitle">Progression globale de votre travail.</div>
                </div>
                <div class="jb-chart-badge">{progression:.0f}%</div>
            </div>
            <div class="jb-chart-image-wrap"><img src="{img_tasks}" /></div>
            <div class="jb-progress slim"><div class="jb-progress-bar" style="width:{min(progression, 100)}%;">{progression:.1f}%</div></div>
        </div>
        """)

    if not depenses.empty:
        col_a, col_b = st.columns([1, 1])
        with col_a:
            fig_daily = creer_figure_depenses_journalieres(depenses, mois, annee)
            if fig_daily:
                img_daily = image_figure(fig_daily)
                md(f"""
                <div class="jb-chart-card">
                    <div class="jb-chart-head">
                        <div>
                            <div class="jb-chart-title">Progression des dépenses</div>
                            <div class="jb-chart-subtitle">Cumul des dépenses jour après jour.</div>
                        </div>
                    </div>
                    <div class="jb-chart-image-wrap wide"><img src="{img_daily}" /></div>
                </div>
                """)
        with col_b:
            fig_bar = creer_figure_barres_categories(depenses)
            img_bar = image_figure(fig_bar)
            md(f"""
            <div class="jb-chart-card">
                <div class="jb-chart-head">
                    <div>
                        <div class="jb-chart-title">Catégories les plus coûteuses</div>
                        <div class="jb-chart-subtitle">Classement des montants par catégorie.</div>
                    </div>
                </div>
                <div class="jb-chart-image-wrap wide"><img src="{img_bar}" /></div>
            </div>
            """)


def format_date_affichage(valeur):
    if valeur is None or pd.isna(valeur):
        return "Non définie"
    try:
        d = pd.to_datetime(valeur).date()
        return f"{d.day:02d}/{d.month:02d}/{d.year}"
    except Exception:
        return str(valeur)[:10]


def format_heure_affichage(valeur):
    heure = convertir_heure_mysql(valeur)
    if heure is None:
        return ""
    return heure.strftime("%H:%M")


def statut_infos(statut):
    data = {
        "a_faire": ("À faire", "jb-pill-orange", "bi-circle"),
        "en_cours": ("En cours", "jb-pill-blue", "bi-play-circle"),
        "terminee": ("Terminée", "jb-pill-green", "bi-check-circle"),
        "en_retard": ("En retard", "jb-pill-red", "bi-exclamation-circle"),
    }
    return data.get(statut, (str(statut), "jb-pill-grey", "bi-circle"))


def priorite_infos(priorite):
    data = {
        "basse": ("Basse", "jb-pill-green"),
        "moyenne": ("Moyenne", "jb-pill-blue"),
        "haute": ("Haute", "jb-pill-red"),
    }
    return data.get(priorite, (str(priorite), "jb-pill-grey"))


def categorie_icon(categorie):
    mapping = {
        "Logement": "bi-house-door",
        "Nourriture": "bi-basket",
        "Transport": "bi-bus-front",
        "Facture": "bi-receipt",
        "Loisirs": "bi-controller",
        "Santé": "bi-heart-pulse",
        "Études": "bi-mortarboard",
        "Courses": "bi-cart3",
        "Maison": "bi-house-gear",
        "Travail": "bi-briefcase",
        "Finance": "bi-wallet2",
        "Personnel": "bi-person",
    }
    return mapping.get(categorie, "bi-folder")


def afficher_depenses_liste(depenses):
    if depenses.empty:
        st.info("Aucune dépense à afficher.")
        return

    for _, d in depenses.iterrows():
        titre = nettoyer(d.get("titre", "Dépense"))
        categorie = nettoyer(d.get("categorie", "Autre"))
        montant = format_euro(d.get("montant", 0))
        date_depense = format_date_affichage(d.get("date_depense"))
        mode = nettoyer(d.get("mode_paiement", "Non précisé"))
        note = nettoyer(d.get("note", ""))
        icon = categorie_icon(categorie)

        md(f"""
        <div class="jb-list-card">
            <div class="jb-list-left">
                <div class="jb-list-icon"><i class="bi {icon}"></i></div>
                <div>
                    <div class="jb-list-title">{titre}</div>
                    <div class="jb-list-meta">{categorie} · {date_depense} · {mode}</div>
                    <div class="jb-list-note">{note}</div>
                </div>
            </div>
            <div class="jb-list-amount">{montant}</div>
        </div>
        """)


def changer_statut_depuis_bouton(tache_id, statut):
    succes, message = modifier_statut_tache(int(tache_id), statut)
    if succes:
        st.success(message)
        st.rerun()
    else:
        st.error(message)


def afficher_taches_liste(taches):
    if taches.empty:
        st.info("Aucune tâche à afficher.")
        return

    for _, t in taches.iterrows():
        tache_id = int(t["id"])
        titre = nettoyer(t.get("titre", "Tâche"))
        description = nettoyer(t.get("description", ""))
        categorie = nettoyer(t.get("categorie", "Autre"))
        statut = t.get("statut", "a_faire")
        priorite = t.get("priorite", "moyenne")
        statut_txt, statut_cls, statut_icon = statut_infos(statut)
        prio_txt, prio_cls = priorite_infos(priorite)
        date_limite = format_date_affichage(t.get("date_limite"))
        heure_limite = format_heure_affichage(t.get("heure_limite"))
        montant = format_euro(t.get("montant_estime", 0) or 0)
        depense = "Oui" if t.get("liee_depense") else "Non"
        icon = categorie_icon(categorie)

        md(f"""
        <div class="jb-task-card">
            <div class="jb-task-main">
                <div class="jb-task-icon"><i class="bi {icon}"></i></div>
                <div class="jb-task-content">
                    <div class="jb-task-title-row">
                        <div class="jb-task-title">{titre}</div>
                        <span class="jb-pill {statut_cls}"><i class="bi {statut_icon}"></i> {statut_txt}</span>
                    </div>
                    <div class="jb-task-desc">{description}</div>
                    <div class="jb-task-meta">
                        <span><i class="bi bi-folder"></i> {categorie}</span>
                        <span><i class="bi bi-calendar3"></i> {date_limite} {heure_limite}</span>
                        <span><i class="bi bi-flag"></i> <span class="jb-pill {prio_cls}">{prio_txt}</span></span>
                        <span><i class="bi bi-cash-coin"></i> Dépense : {depense} · {montant}</span>
                    </div>
                </div>
            </div>
        </div>
        """)

        c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 4])
        with c1:
            if st.button("À faire", key=f"todo_{tache_id}"):
                changer_statut_depuis_bouton(tache_id, "a_faire")
        with c2:
            if st.button("En cours", key=f"progress_{tache_id}"):
                changer_statut_depuis_bouton(tache_id, "en_cours")
        with c3:
            if st.button("Terminée", key=f"done_{tache_id}"):
                changer_statut_depuis_bouton(tache_id, "terminee")
        with c4:
            if st.button("Supprimer", key=f"delete_direct_{tache_id}"):
                succes, message = supprimer_tache(tache_id)
                if succes:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)


def page_connexion():
    # Page d'accueil / authentification améliorée pour PC et téléphone
    md("""
    <style>
        header[data-testid="stHeader"],
        div[data-testid="stToolbar"],
        div[data-testid="stDecoration"],
        div[data-testid="stStatusWidget"],
        #MainMenu,
        footer {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
        }

        .block-container {
            padding-top: 1.25rem !important;
            padding-bottom: 4rem !important;
        }

        .auth-modern-shell {
            max-width: 1040px;
            margin: 0 auto 26px auto;
            padding: 0 8px;
        }

        .auth-modern-hero {
            position: relative;
            overflow: hidden;
            border-radius: 34px;
            padding: 34px 34px 30px 34px;
            background:
                radial-gradient(circle at 18% 15%, rgba(59, 130, 246, 0.24), transparent 34%),
                radial-gradient(circle at 90% 20%, rgba(16, 185, 129, 0.24), transparent 34%),
                linear-gradient(135deg, #082f49 0%, #064e3b 100%);
            color: white;
            box-shadow: 0 28px 70px rgba(15, 23, 42, 0.20);
            border: 1px solid rgba(255, 255, 255, 0.16);
        }

        .auth-modern-hero::after {
            content: "";
            position: absolute;
            inset: auto -70px -130px auto;
            width: 270px;
            height: 270px;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.08);
        }

        .auth-modern-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 18px;
            position: relative;
            z-index: 1;
        }

        .auth-modern-logo {
            width: 78px;
            height: 78px;
            border-radius: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 25px !important;
            font-weight: 950 !important;
            color: #ffffff !important;
            background: linear-gradient(135deg, #2563eb, #0f766e);
            box-shadow: 0 18px 42px rgba(15, 118, 110, 0.32);
            border: 1px solid rgba(255, 255, 255, 0.22);
        }

        .auth-modern-badge {
            padding: 10px 14px;
            border-radius: 999px;
            color: rgba(255, 255, 255, 0.92) !important;
            background: rgba(255, 255, 255, 0.13);
            border: 1px solid rgba(255, 255, 255, 0.18);
            font-size: 13px !important;
            font-weight: 850 !important;
            backdrop-filter: blur(10px);
        }

        .auth-modern-title {
            position: relative;
            z-index: 1;
            margin-top: 24px;
            font-size: 44px !important;
            line-height: 1.02;
            letter-spacing: -1.2px;
            font-weight: 950 !important;
            color: #ffffff !important;
        }

        .auth-modern-subtitle {
            position: relative;
            z-index: 1;
            margin-top: 12px;
            max-width: 690px;
            color: rgba(255, 255, 255, 0.82) !important;
            font-size: 17px !important;
            line-height: 1.65;
            font-weight: 650 !important;
        }

        .auth-modern-benefits {
            position: relative;
            z-index: 1;
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-top: 24px;
        }

        .auth-modern-benefit {
            display: inline-flex;
            align-items: center;
            gap: 9px;
            padding: 12px 15px;
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.12);
            border: 1px solid rgba(255, 255, 255, 0.17);
            color: #ffffff !important;
            font-size: 14px !important;
            font-weight: 850 !important;
            backdrop-filter: blur(12px);
        }

        .auth-modern-benefit i {
            font-size: 18px !important;
            color: #ffffff !important;
        }

        .auth-panel {
            max-width: 560px;
            margin: 0 auto;
        }

        .auth-section-title {
            text-align: center;
            margin: 0 auto 18px auto;
        }

        .auth-section-title h2 {
            color: #101828 !important;
            font-size: 27px !important;
            font-weight: 950 !important;
            margin-bottom: 8px !important;
        }

        .auth-section-title p {
            color: #667085 !important;
            font-size: 15px !important;
            line-height: 1.55;
            font-weight: 650 !important;
            margin: 0 !important;
        }

        .auth-mini-help {
            margin: 14px 0 0 0;
            padding: 13px 15px;
            border-radius: 16px;
            background: #eff6ff;
            color: #1e3a8a !important;
            font-size: 13px !important;
            font-weight: 750 !important;
            border: 1px solid #bfdbfe;
        }

        .auth-form-heading {
            color: #101828 !important;
            font-size: 23px !important;
            line-height: 1.15;
            font-weight: 950 !important;
            margin-bottom: 6px;
        }

        .auth-form-subheading {
            color: #667085 !important;
            font-size: 14px !important;
            font-weight: 650 !important;
            line-height: 1.5;
            margin-bottom: 20px;
        }

        /* Radio transformé en vrais onglets propres */
        div[role="radiogroup"] {
            display: grid !important;
            grid-template-columns: 1fr 1fr !important;
            gap: 10px !important;
            background: #f1f5f9 !important;
            padding: 7px !important;
            border-radius: 18px !important;
            border: 1px solid #e2e8f0 !important;
            margin-bottom: 18px !important;
        }

        div[role="radiogroup"] label {
            margin: 0 !important;
            padding: 11px 12px !important;
            border-radius: 14px !important;
            background: transparent !important;
            border: 1px solid transparent !important;
            justify-content: center !important;
            transition: all .18s ease !important;
        }

        div[role="radiogroup"] label:has(input:checked) {
            background: #ffffff !important;
            border-color: #dbeafe !important;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08) !important;
        }

        div[role="radiogroup"] label p {
            color: #475569 !important;
            font-size: 15px !important;
            font-weight: 900 !important;
        }

        div[role="radiogroup"] label:has(input:checked) p {
            color: #1e3a8a !important;
        }

        div[data-testid="stForm"] {
            background: #ffffff !important;
            border: 1px solid #e3e7ee !important;
            border-radius: 26px !important;
            padding: 28px 30px !important;
            box-shadow: 0 18px 48px rgba(15, 23, 42, 0.09) !important;
        }

        div[data-testid="stTextInput"] label,
        div[data-testid="stTextInput"] label p {
            color: #101828 !important;
            opacity: 1 !important;
            visibility: visible !important;
            font-size: 14px !important;
            font-weight: 900 !important;
            margin-bottom: 7px !important;
        }

        div[data-testid="stTextInput"] input,
        div[data-baseweb="input"] input {
            background: #ffffff !important;
            color: #101828 !important;
            border: 1.5px solid #cbd5e1 !important;
            border-radius: 15px !important;
            min-height: 51px !important;
            font-size: 15px !important;
            font-weight: 700 !important;
            padding: 12px 15px !important;
            box-shadow: none !important;
        }

        div[data-testid="stTextInput"] input:focus,
        div[data-baseweb="input"] input:focus {
            border-color: #1e3a8a !important;
            box-shadow: 0 0 0 4px rgba(30, 58, 138, 0.12) !important;
        }

        div[data-testid="stTextInput"] input::placeholder {
            color: #94a3b8 !important;
            opacity: 1 !important;
        }

        div[data-testid="stForm"] .stFormSubmitButton button {
            width: 100% !important;
            background: linear-gradient(135deg, #1e3a8a, #0f766e) !important;
            color: white !important;
            border: none !important;
            border-radius: 15px !important;
            min-height: 50px !important;
            padding: 12px 24px !important;
            font-size: 15px !important;
            font-weight: 950 !important;
            box-shadow: 0 14px 30px rgba(30, 58, 138, 0.20) !important;
            transition: all .18s ease !important;
        }

        div[data-testid="stForm"] .stFormSubmitButton button:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 18px 34px rgba(15, 118, 110, 0.26) !important;
        }

        div[data-testid="stTextInput"] button {
            border-radius: 0 15px 15px 0 !important;
            background: #252733 !important;
            color: white !important;
        }

        div[data-testid="stAlert"] {
            border-radius: 16px !important;
            font-weight: 750 !important;
        }

        @media (max-width: 768px) {
            .block-container {
                padding-left: 14px !important;
                padding-right: 14px !important;
                padding-top: 12px !important;
                padding-bottom: 90px !important;
            }

            .auth-modern-shell {
                margin-bottom: 20px !important;
                padding: 0 !important;
            }

            .auth-modern-hero {
                border-radius: 26px !important;
                padding: 24px 20px 22px 20px !important;
                box-shadow: 0 18px 44px rgba(15, 23, 42, 0.16) !important;
            }

            .auth-modern-top {
                justify-content: center !important;
                flex-direction: column !important;
                gap: 12px !important;
            }

            .auth-modern-logo {
                width: 72px !important;
                height: 72px !important;
                border-radius: 22px !important;
                font-size: 23px !important;
            }

            .auth-modern-badge {
                font-size: 12px !important;
                padding: 8px 12px !important;
            }

            .auth-modern-title {
                text-align: center !important;
                margin-top: 18px !important;
                font-size: 34px !important;
                letter-spacing: -0.7px !important;
            }

            .auth-modern-subtitle {
                text-align: center !important;
                font-size: 14px !important;
                line-height: 1.55 !important;
                margin-left: auto !important;
                margin-right: auto !important;
            }

            .auth-modern-benefits {
                justify-content: center !important;
                gap: 8px !important;
                margin-top: 18px !important;
            }

            .auth-modern-benefit {
                padding: 9px 11px !important;
                border-radius: 15px !important;
                font-size: 12px !important;
            }

            .auth-modern-benefit i {
                font-size: 15px !important;
            }

            .auth-section-title h2 {
                font-size: 23px !important;
            }

            .auth-section-title p {
                font-size: 14px !important;
            }

            div[data-testid="stForm"] {
                padding: 22px 18px !important;
                border-radius: 22px !important;
            }

            .auth-form-heading {
                font-size: 21px !important;
            }
        }

        @media (max-width: 420px) {
            .auth-modern-title {
                font-size: 30px !important;
            }

            .auth-modern-benefit {
                width: 100% !important;
                justify-content: center !important;
            }
        }
    </style>
    """)

    if st.session_state.get("auth_mode") not in ["Connexion", "Inscription"]:
        st.session_state["auth_mode"] = "Connexion"

    if "login_email" not in st.session_state:
        st.session_state["login_email"] = ""

    md("""
    <div class="auth-modern-shell">
        <div class="auth-modern-hero">
            <div class="auth-modern-top">
                <div class="auth-modern-logo">JB</div>
                <div class="auth-modern-badge"><i class="bi bi-shield-lock"></i> Espace personnel sécurisé</div>
            </div>
            <div class="auth-modern-title">JordyBusiness</div>
            <div class="auth-modern-subtitle">
                Organisez vos tâches, suivez votre budget et gardez vos paiements programmés au même endroit.
            </div>
            <div class="auth-modern-benefits">
                <div class="auth-modern-benefit"><i class="bi bi-check2-circle"></i> Tâches claires</div>
                <div class="auth-modern-benefit"><i class="bi bi-wallet2"></i> Budget maîtrisé</div>
                <div class="auth-modern-benefit"><i class="bi bi-bell"></i> Alertes utiles</div>
            </div>
        </div>
    </div>
    """)

    st.markdown("<div class='auth-panel'>", unsafe_allow_html=True)

    md("""
    <div class="auth-section-title">
        <h2>Bienvenue</h2>
        <p>Connectez-vous ou créez votre compte pour accéder à votre espace.</p>
    </div>
    """)

    # Important : Streamlit interdit de modifier directement la valeur
    # d'un widget après sa création. On applique donc le changement AVANT
    # d'afficher le bouton Connexion / Inscription.
    if "auth_mode_a_appliquer" in st.session_state:
        st.session_state["auth_mode"] = st.session_state.pop("auth_mode_a_appliquer")

    mode = st.radio(
        "Choisissez une action",
        ["Connexion", "Inscription"],
        horizontal=True,
        label_visibility="collapsed",
        key="auth_mode"
    )

    notice = st.session_state.pop("auth_notice", None)
    if notice:
        st.success(notice)

    if mode == "Connexion":
        with st.form("connexion"):
            st.markdown("<div class='auth-form-heading'>Se connecter</div>", unsafe_allow_html=True)
            st.markdown(
                "<div class='auth-form-subheading'>Entrez votre email et votre mot de passe.</div>",
                unsafe_allow_html=True
            )

            email = st.text_input(
                "Adresse email",
                placeholder="exemple@email.com",
                key="login_email"
            )

            mot_de_passe = st.text_input(
                "Mot de passe",
                type="password",
                placeholder="Votre mot de passe",
                key="login_password"
            )

            bouton = st.form_submit_button("Connexion")

            if bouton:
                if email.strip() == "" or mot_de_passe.strip() == "":
                    st.error("Veuillez remplir tous les champs.")
                else:
                    utilisateur = connecter_utilisateur(email.strip(), mot_de_passe)

                    if utilisateur:
                        st.session_state["connecte"] = True
                        st.session_state["utilisateur"] = utilisateur
                        st.session_state.pop("automatisations_lancees", None)
                        st.rerun()
                    else:
                        st.error("Email ou mot de passe incorrect.")

        md("""
        <div class="auth-mini-help">
            Nouveau sur JordyBusiness ? Cliquez sur Inscription pour créer votre espace.
        </div>
        """)

    else:
        with st.form("inscription"):
            st.markdown("<div class='auth-form-heading'>Créer un compte</div>", unsafe_allow_html=True)
            st.markdown(
                "<div class='auth-form-subheading'>Après la création, vous serez automatiquement ramené vers Connexion.</div>",
                unsafe_allow_html=True
            )

            nom = st.text_input(
                "Nom complet",
                placeholder="Votre nom complet",
                key="register_name"
            )

            email = st.text_input(
                "Adresse email",
                placeholder="exemple@email.com",
                key="register_email"
            )

            mot_de_passe = st.text_input(
                "Mot de passe",
                type="password",
                placeholder="Minimum 6 caractères",
                key="register_password"
            )

            confirmation = st.text_input(
                "Confirmer le mot de passe",
                type="password",
                placeholder="Répétez le mot de passe",
                key="register_password_confirm"
            )

            bouton = st.form_submit_button("Créer mon compte")

            if bouton:
                email_propre = email.strip().lower()
                nom_propre = nom.strip()

                if nom_propre == "" or email_propre == "" or mot_de_passe.strip() == "":
                    st.error("Le nom, l’email et le mot de passe sont obligatoires.")
                elif "@" not in email_propre or "." not in email_propre:
                    st.error("Veuillez entrer une adresse email valide.")
                elif mot_de_passe != confirmation:
                    st.error("Les mots de passe ne correspondent pas.")
                elif len(mot_de_passe) < 6:
                    st.error("Le mot de passe doit contenir au moins 6 caractères.")
                else:
                    succes, message = creer_utilisateur(nom_propre, email_propre, mot_de_passe)

                    if succes:
                        st.session_state["auth_mode_a_appliquer"] = "Connexion"
                        st.session_state["login_email"] = email_propre
                        st.session_state["auth_notice"] = "Compte créé avec succès. Connectez-vous maintenant avec votre mot de passe."
                        st.rerun()
                    else:
                        st.error(message)

    st.markdown("</div>", unsafe_allow_html=True)

def page_tableau_de_bord():
    utilisateur = st.session_state["utilisateur"]
    aujourd_hui = date.today()
    mois = aujourd_hui.month
    annee = aujourd_hui.year

    budget = recuperer_budget_mois(mois, annee)
    depenses = recuperer_depenses_mois(mois, annee)
    total_depenses = float(depenses["montant"].sum()) if not depenses.empty else 0.0
    reste = budget - total_depenses
    pourcentage_depense = (total_depenses / budget * 100) if budget > 0 else 0
    pourcentage_reste = 100 - pourcentage_depense if budget > 0 else 0

    taches = recuperer_taches()
    taches_retard = 0
    if not taches.empty:
        aujourd_datetime = pd.to_datetime(date.today())
        taches_retard = len(taches[(pd.to_datetime(taches["date_limite"]) < aujourd_datetime) & (taches["statut"] != "terminee")])

    alertes_df = recuperer_alertes(100)
    alertes_non_lues_count = len(alertes_df[alertes_df["lue"] == 0]) if not alertes_df.empty else 0
    nom_complet = nettoyer(utilisateur.get("nom", "Utilisateur"))
    prenom = nom_complet.split()[0] if nom_complet else "Utilisateur"
    initiale = nom_complet[0].upper() if nom_complet else "U"
    mois_annee_courant = f"{nom_mois(mois)} {annee}"

    md(f"""
    <div class="jb-dashboard-header">
        <div>
            <div class="jb-welcome-small">Espace JordyBusiness</div>
            <h1>Bonjour {prenom}, heureux de vous revoir.</h1>
            <p>Aujourd’hui, gardez le contrôle sur vos tâches, vos dépenses et vos objectifs.</p>
        </div>
        <div class="jb-header-actions">
            <div class="jb-date-pill"><i class="bi bi-calendar3"></i><span>{mois_annee_courant}</span></div>
            <div class="jb-notif-pill"><i class="bi bi-bell"></i><span>{alertes_non_lues_count}</span></div>
            <div class="jb-user-pill"><div>{initiale}</div><span>{prenom}</span></div>
        </div>
    </div>
    """)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        md(f"""
        <div class="jb-kpi-card"><div class="jb-kpi-icon jb-kpi-icon-blue"><i class="bi bi-wallet2"></i></div>
        <div><div class="jb-kpi-label">Capital du mois</div><div class="jb-kpi-value jb-blue">{format_euro(budget)}</div><div class="jb-muted">Revenus prévus</div></div></div>
        """)
    with col2:
        md(f"""
        <div class="jb-kpi-card"><div class="jb-kpi-icon jb-kpi-icon-red"><i class="bi bi-graph-down-arrow"></i></div>
        <div><div class="jb-kpi-label">Dépenses du mois</div><div class="jb-kpi-value jb-red">{format_euro(total_depenses)}</div><div class="jb-muted">{pourcentage_depense:.1f}% du budget</div></div></div>
        """)
    with col3:
        md(f"""
        <div class="jb-kpi-card"><div class="jb-kpi-icon jb-kpi-icon-green"><i class="bi bi-cash-coin"></i></div>
        <div><div class="jb-kpi-label">Reste disponible</div><div class="jb-kpi-value jb-green">{format_euro(reste)}</div><div class="jb-muted">{pourcentage_reste:.1f}% du budget</div></div></div>
        """)
    with col4:
        md(f"""
        <div class="jb-kpi-card"><div class="jb-kpi-icon jb-kpi-icon-orange"><i class="bi bi-clock"></i></div>
        <div><div class="jb-kpi-label">Tâches en retard</div><div class="jb-kpi-value jb-orange">{taches_retard}</div><div class="jb-muted">À traiter rapidement</div></div></div>
        """)

    md(f"""
    <div class="jb-card jb-budget-card">
        <div class="jb-chart-head">
            <div><div class="jb-card-title">Budget mensuel</div><div class="jb-muted">Vous avez dépensé {pourcentage_depense:.1f}% de votre budget mensuel.</div></div>
            <div class="jb-chart-badge">{mois_annee_courant}</div>
        </div>
        <div class="jb-progress"><div class="jb-progress-bar" style="width:{min(pourcentage_depense,100)}%;">{pourcentage_depense:.1f}%</div></div>
        <div class="jb-budget-row"><strong>{format_euro(total_depenses)} dépensés</strong><span>{format_euro(budget)} budget total</span></div>
    </div>
    """)

    afficher_bloc_grands_diagrammes(depenses, taches, mois, annee)

    col_pay, col_tasks, col_alerts = st.columns([1, 1.1, 1])

    with col_pay:
        paiements = recuperer_paiements_programmes().head(4)
        md("""
        <div class="jb-card"><div class="jb-chart-head"><div><div class="jb-card-title">Paiements programmés</div><div class="jb-muted">Vos prochaines échéances.</div></div></div>
        """)
        if paiements.empty:
            md("<div class='jb-empty-state'>Aucun paiement programmé.</div>")
        else:
            for _, p in paiements.iterrows():
                icone = get_paiement_icone(p.get("categorie", ""), p.get("titre", ""))
                etat = "Actif" if p["active"] else "Inactif"
                classe = "jb-pill-green" if p["active"] else "jb-pill-orange"
                md(f"""
                <div class="jb-mini-row">
                    <div class="jb-mini-row-left"><div class="jb-mini-icon"><i class="bi bi-{icone}"></i></div><div><strong>{nettoyer(p['titre'])}</strong><span>{p['prochaine_date']}</span></div></div>
                    <div class="jb-mini-row-right"><strong>{format_euro(p['montant'])}</strong><span class="jb-pill {classe}">{etat}</span></div>
                </div>
                """)
        md("</div>")

    with col_tasks:
        md("<div class='jb-card'><div class='jb-card-title'>Tâches récentes</div>")
        taches_aff = taches.head(4).copy() if not taches.empty else pd.DataFrame()
        md(get_taches_recentes_html(taches_aff))
        if st.button("Voir toutes les tâches", key="nav_taches", use_container_width=True):
            st.session_state["current_page"] = "taches"
            st.rerun()
        md("</div>")

    with col_alerts:
        alertes = recuperer_alertes(3)
        md("<div class='jb-card'><div class='jb-card-title'>Alertes</div>")
        if alertes.empty:
            md("<div class='jb-alert-success'>Aucune alerte récente.</div>")
        else:
            for _, alerte in alertes.iterrows():
                classe = "jb-alert-info"
                if alerte["type_alerte"] == "danger":
                    classe = "jb-alert-danger"
                elif alerte["type_alerte"] == "attention":
                    classe = "jb-alert-warning"
                elif alerte["type_alerte"] == "succes":
                    classe = "jb-alert-success"
                md(f"""<div class="{classe}"><strong>{nettoyer(alerte['titre'])}</strong><br>{nettoyer(alerte['message'])}</div>""")
        if st.button("Voir toutes les alertes", key="nav_alertes", use_container_width=True):
            st.session_state["current_page"] = "alertes"
            st.rerun()
        md("</div>")


def page_budget():
    st.title("Budget mensuel")

    aujourd_hui = date.today()

    col1, col2 = st.columns(2)

    with col1:
        mois = st.selectbox(
            "Mois",
            list(MOIS_FR.keys()),
            index=aujourd_hui.month - 1,
            format_func=lambda x: MOIS_FR[x]
        )

    with col2:
        annee = st.number_input(
            "Année",
            min_value=2020,
            max_value=2100,
            value=aujourd_hui.year,
            step=1
        )

    budget = recuperer_budget_mois(mois, annee)
    depenses = recuperer_depenses_mois(mois, annee)
    total = float(depenses["montant"].sum()) if not depenses.empty else 0.0
    reste = budget - total
    progression = (total / budget * 100) if budget > 0 else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        md(f"""<div class="jb-mini-stat"><span>Capital du mois</span><strong>{format_euro(budget)}</strong></div>""")
    with c2:
        md(f"""<div class="jb-mini-stat"><span>Dépenses du mois</span><strong>{format_euro(total)}</strong></div>""")
    with c3:
        md(f"""<div class="jb-mini-stat"><span>Reste disponible</span><strong>{format_euro(reste)}</strong></div>""")

    md(f"""
    <div class="jb-card">
        <div class="jb-card-title">Progression du budget</div>
        <div class="jb-muted">Vous avez utilisé {progression:.1f}% de votre capital mensuel.</div>
        <br>
        <div class="jb-progress"><div class="jb-progress-bar" style="width:{min(progression, 100)}%;">{progression:.1f}%</div></div>
    </div>
    """)

    with st.form("form_budget"):
        st.subheader("Définir ou modifier le capital du mois")
        nouveau_budget = st.number_input(
            "Capital mensuel",
            min_value=0.0,
            value=float(budget),
            step=10.0
        )
        bouton = st.form_submit_button("Enregistrer")

        if bouton:
            succes, message = enregistrer_budget_mois(mois, annee, nouveau_budget)

            if succes:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    st.subheader(f"Dépenses de {nom_mois(mois)} {annee}")
    afficher_depenses_liste(depenses)


def page_ajouter_tache():
    st.title("Ajouter une tâche")

    with st.form("form_tache"):
        titre = st.text_input("Titre")
        description = st.text_area("Description")

        col1, col2 = st.columns(2)

        with col1:
            categorie = st.selectbox("Catégorie", CATEGORIES_TACHES)
            priorite = st.selectbox("Priorité", PRIORITES, index=1)

        with col2:
            date_limite = st.date_input("Date limite")
            heure_limite = st.time_input("Heure limite")
            duree_minutes = st.number_input(
                "Durée estimée en minutes",
                min_value=0,
                value=60,
                step=15
            )

        liee_depense = st.checkbox("Cette tâche est liée à une dépense ?")
        montant_estime = 0.0

        if liee_depense:
            montant_estime = st.number_input(
                "Montant estimé",
                min_value=0.0,
                step=0.5
            )

        bouton = st.form_submit_button("Ajouter la tâche")

        if bouton:
            if titre.strip() == "":
                st.error("Le titre est obligatoire.")
            elif liee_depense and montant_estime <= 0:
                st.error("Le montant doit être supérieur à 0.")
            else:
                succes, message = ajouter_tache(
                    titre,
                    description,
                    categorie,
                    priorite,
                    date_limite,
                    heure_limite,
                    duree_minutes,
                    liee_depense,
                    montant_estime
                )

                if succes:
                    st.success(message)
                else:
                    st.error(message)



def page_taches():
    st.title("Mes tâches")

    taches = recuperer_taches()

    if taches.empty:
        st.info("Aucune tâche.")
        return

    total = len(taches)
    a_faire = len(taches[taches["statut"] == "a_faire"])
    en_cours = len(taches[taches["statut"] == "en_cours"])
    terminees = len(taches[taches["statut"] == "terminee"])
    progression = (terminees / total * 100) if total > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        md(f"<div class='jb-mini-stat'><span>Total</span><strong>{total}</strong></div>")
    with c2:
        md(f"<div class='jb-mini-stat'><span>À faire</span><strong>{a_faire}</strong></div>")
    with c3:
        md(f"<div class='jb-mini-stat'><span>En cours</span><strong>{en_cours}</strong></div>")
    with c4:
        md(f"<div class='jb-mini-stat'><span>Terminées</span><strong>{terminees}</strong></div>")

    md(f"""
    <div class="jb-card">
        <div class="jb-card-title">Progression des tâches</div>
        <div class="jb-muted">{progression:.1f}% des tâches sont terminées.</div>
        <br>
        <div class="jb-progress"><div class="jb-progress-bar" style="width:{min(progression, 100)}%;">{progression:.1f}%</div></div>
    </div>
    """)

    filtre = st.selectbox(
        "Filtrer les tâches",
        ["Toutes", "À faire", "En cours", "Terminées"],
        index=0
    )

    taches_filtrees = taches.copy()
    if filtre == "À faire":
        taches_filtrees = taches_filtrees[taches_filtrees["statut"] == "a_faire"]
    elif filtre == "En cours":
        taches_filtrees = taches_filtrees[taches_filtrees["statut"] == "en_cours"]
    elif filtre == "Terminées":
        taches_filtrees = taches_filtrees[taches_filtrees["statut"] == "terminee"]

    afficher_taches_liste(taches_filtrees)

    st.markdown("---")
    st.subheader("Modification rapide")

    mapping = {int(row["id"]): f"#{row['id']} - {row['titre']}" for _, row in taches.iterrows()}

    with st.form("form_statut"):
        tache_id = st.selectbox("Tâche", list(mapping.keys()), format_func=lambda x: mapping[x])
        nouveau_statut_label = st.selectbox("Nouveau statut", ["À faire", "En cours", "Terminée"])
        statut_map = {"À faire": "a_faire", "En cours": "en_cours", "Terminée": "terminee"}
        bouton = st.form_submit_button("Modifier")

        if bouton:
            succes, message = modifier_statut_tache(tache_id, statut_map[nouveau_statut_label])
            if succes:
                st.success(message)
                st.rerun()
            else:
                st.error(message)


def page_ajouter_depense():
    st.title("Ajouter une dépense")

    with st.form("form_depense"):
        titre = st.text_input("Titre")

        col1, col2 = st.columns(2)

        with col1:
            categorie = st.selectbox("Catégorie", CATEGORIES_DEPENSES)
            montant = st.number_input("Montant", min_value=0.0, step=0.5)

        with col2:
            date_depense = st.date_input("Date")
            mode_paiement = st.selectbox("Mode de paiement", MODES_PAIEMENT)

        note = st.text_area("Note")
        bouton = st.form_submit_button("Ajouter la dépense")

        if bouton:
            if titre.strip() == "":
                st.error("Le titre est obligatoire.")
            elif montant <= 0:
                st.error("Le montant doit être supérieur à 0.")
            else:
                succes, message = ajouter_depense(
                    titre,
                    categorie,
                    montant,
                    date_depense,
                    mode_paiement,
                    note
                )

                if succes:
                    st.success(message)
                else:
                    st.error(message)




def page_depenses():
    st.markdown("""
    <div class="page-header-pro">
        <div>
            <h1>Mes dépenses</h1>
            <p>Analysez vos dépenses, suivez votre progression et gardez une vision claire de votre budget.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    aujourd_hui = date.today()
    col1, col2 = st.columns(2)
    with col1:
        mois = st.selectbox("Mois", list(MOIS_FR.keys()), index=aujourd_hui.month - 1, format_func=lambda x: MOIS_FR[x])
    with col2:
        annee = st.number_input("Année", min_value=2020, max_value=2100, value=aujourd_hui.year, step=1, key="annee_depenses")

    depenses = recuperer_depenses_mois(mois, annee)
    total = float(depenses["montant"].sum()) if not depenses.empty else 0.0
    budget = recuperer_budget_mois(mois, annee)
    reste = budget - total
    progression = (total / budget * 100) if budget > 0 else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        md(f"<div class='jb-mini-stat'><span>Capital du mois</span><strong>{format_euro(budget)}</strong></div>")
    with c2:
        md(f"<div class='jb-mini-stat'><span>Dépenses</span><strong>{format_euro(total)}</strong></div>")
    with c3:
        md(f"<div class='jb-mini-stat'><span>Reste disponible</span><strong>{format_euro(reste)}</strong></div>")

    md(f"""
    <div class="jb-card jb-budget-card">
        <div class="jb-chart-head">
            <div><div class="jb-card-title">Progression des dépenses</div><div class="jb-muted">Vous avez utilisé {progression:.1f}% de votre capital mensuel.</div></div>
            <div class="jb-chart-badge">{nom_mois(mois)} {annee}</div>
        </div>
        <div class="jb-progress"><div class="jb-progress-bar" style="width:{min(progression, 100)}%;">{progression:.1f}%</div></div>
    </div>
    """)

    if depenses.empty:
        md("""
        <div class="jb-chart-card">
            <div class="jb-chart-title">Diagrammes des dépenses</div>
            <div class="jb-empty-state">Aucune dépense à analyser pour cette période.</div>
        </div>
        """)
    else:
        afficher_bloc_grands_diagrammes(depenses, pd.DataFrame(), mois, annee)

    st.subheader("Dépenses enregistrées")
    afficher_depenses_liste(depenses)

    if not depenses.empty:
        st.markdown("---")
        st.subheader("Supprimer une dépense")
        mapping = {int(row["id"]): f"#{row['id']} - {row['titre']} - {format_euro(row['montant'])}" for _, row in depenses.iterrows()}
        with st.form("form_supprimer_depense"):
            depense_id = st.selectbox("Dépense à supprimer", list(mapping.keys()), format_func=lambda x: mapping[x])
            confirmation = st.checkbox("Je confirme la suppression.")
            bouton = st.form_submit_button("Supprimer")
            if bouton:
                if not confirmation:
                    st.warning("Coche la confirmation.")
                else:
                    succes, message = supprimer_depense(depense_id)
                    if succes:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)


def page_paiements_programmes():
    st.title("Paiements programmés")

    with st.form("form_paiement"):
        st.subheader("Programmer un paiement automatique")

        titre = st.text_input("Titre", placeholder="Exemple : Loyer")
        description = st.text_area("Description")

        col1, col2 = st.columns(2)

        with col1:
            categorie = st.selectbox("Catégorie", CATEGORIES_DEPENSES, index=0)
            montant = st.number_input("Montant", min_value=0.0, step=10.0)
            mode_paiement = st.selectbox("Mode de paiement", MODES_PAIEMENT, index=3)

        with col2:
            frequence = st.selectbox("Fréquence", ["mensuelle", "hebdomadaire", "annuelle"])

            jour_mois = None
            jour_semaine = None
            mois_annuel = None

            if frequence == "mensuelle":
                jour_mois = st.number_input("Jour du mois", min_value=1, max_value=31, value=5, step=1)
            elif frequence == "hebdomadaire":
                jour_semaine = st.number_input("Jour de semaine 1=lundi, 7=dimanche", min_value=1, max_value=7, value=1, step=1)
            elif frequence == "annuelle":
                mois_annuel = st.number_input("Mois annuel", min_value=1, max_value=12, value=1, step=1)
                jour_mois = st.number_input("Jour du mois", min_value=1, max_value=31, value=1, step=1)

            prochaine_date = st.date_input("Prochaine date d'exécution")

        bouton = st.form_submit_button("Ajouter le paiement programmé")

        if bouton:
            if titre.strip() == "":
                st.error("Le titre est obligatoire.")
            elif montant <= 0:
                st.error("Le montant doit être supérieur à 0.")
            else:
                succes, message = ajouter_paiement_programme(
                    titre,
                    description,
                    categorie,
                    montant,
                    frequence,
                    jour_mois,
                    jour_semaine,
                    mois_annuel,
                    prochaine_date,
                    mode_paiement
                )

                if succes:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

    st.markdown("---")
    st.subheader("Liste des paiements programmés")

    paiements = recuperer_paiements_programmes()
    afficher_tableau(paiements)

    if not paiements.empty:
        mapping = {
            int(row["id"]): f"#{row['id']} - {row['titre']} - {format_euro(row['montant'])}"
            for _, row in paiements.iterrows()
        }

        col1, col2 = st.columns(2)

        with col1:
            with st.form("form_desactiver"):
                paiement_id = st.selectbox(
                    "Paiement",
                    list(mapping.keys()),
                    format_func=lambda x: mapping[x]
                )

                actif = st.checkbox("Actif", value=True)
                bouton = st.form_submit_button("Mettre à jour")

                if bouton:
                    succes, message = changer_etat_paiement(paiement_id, actif)

                    if succes:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

        with col2:
            with st.form("form_supprimer_paiement"):
                paiement_id = st.selectbox(
                    "Paiement à supprimer",
                    list(mapping.keys()),
                    format_func=lambda x: mapping[x],
                    key="delete_payment"
                )

                confirmation = st.checkbox("Je confirme la suppression.")
                bouton = st.form_submit_button("Supprimer")

                if bouton:
                    if not confirmation:
                        st.warning("Coche la confirmation.")
                    else:
                        succes, message = supprimer_paiement(paiement_id)

                        if succes:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)


def page_alertes():
    st.title("Alertes")

    alertes = recuperer_alertes(100)

    if alertes.empty:
        st.success("Aucune alerte.")
    else:
        for _, alerte in alertes.iterrows():
            classe = "jb-alert-info"

            if alerte["type_alerte"] == "danger":
                classe = "jb-alert-danger"
            elif alerte["type_alerte"] == "attention":
                classe = "jb-alert-warning"
            elif alerte["type_alerte"] == "succes":
                classe = "jb-alert-success"

            md(f"""
            <div class="{classe}">
                <strong>{nettoyer(alerte["titre"])}</strong><br>
                {nettoyer(alerte["message"])}<br>
                <small>{alerte["cree_le"]}</small>
            </div>
            """)

    if st.button("Marquer toutes les alertes comme lues"):
        succes, message = marquer_alertes_lues()

        if succes:
            st.success(message)
            st.rerun()
        else:
            st.error(message)



def page_profil():
    utilisateur = st.session_state["utilisateur"]

    st.markdown(
        """
        <div class="page-header-pro">
            <div>
                <h1>Mon profil</h1>
                <p>Gérez vos informations personnelles, votre sécurité et votre compte.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    photo_html = photo_profil_html(utilisateur, 130)
    nom = utilisateur.get("nom", "")
    email = utilisateur.get("email", "")
    telephone = utilisateur.get("telephone", "") or ""
    adresse = utilisateur.get("adresse", "") or ""
    role = utilisateur.get("role", "utilisateur")

    col_gauche, col_droite = st.columns([0.9, 1.6])

    with col_gauche:
        st.markdown(
            f"""
            <div class="profile-card">
                <div class="profile-photo-wrap">{photo_html}</div>
                <div class="profile-name">{nettoyer(nom)}</div>
                <div class="profile-email">{nettoyer(email)}</div>
                <div class="profile-role">{nettoyer(role)}</div>
                <div class="profile-info-list">
                    <div><i class="bi bi-telephone"></i><span>{nettoyer(telephone) if telephone else "Téléphone non renseigné"}</span></div>
                    <div><i class="bi bi-geo-alt"></i><span>{nettoyer(adresse) if adresse else "Adresse non renseignée"}</span></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col_droite:
        tab1, tab2, tab3 = st.tabs(["Informations", "Sécurité", "Zone sensible"])

        with tab1:
            with st.form("form_modifier_profil"):
                st.subheader("Modifier mes informations")
                nouveau_nom = st.text_input("Nom complet", value=nom)
                nouvel_email = st.text_input("Adresse email", value=email)
                nouveau_telephone = st.text_input("Numéro de téléphone", value=telephone)
                nouvelle_adresse = st.text_area("Adresse", value=adresse)
                photo = st.file_uploader("Photo de profil", type=["png", "jpg", "jpeg"])
                bouton = st.form_submit_button("Enregistrer les modifications")

                if bouton:
                    photo_base64 = None
                    if photo is not None:
                        photo_base64 = fichier_image_vers_base64(photo)
                        if photo_base64 == "IMAGE_TROP_GRANDE":
                            st.error("L’image est trop grande. Choisis une image de moins de 2 Mo.")
                            st.stop()

                    if nouveau_nom.strip() == "" or nouvel_email.strip() == "":
                        st.error("Le nom et l’email sont obligatoires.")
                    else:
                        succes, message = mettre_a_jour_profil(nouveau_nom, nouvel_email, nouveau_telephone, nouvelle_adresse, photo_base64)
                        if succes:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)

        with tab2:
            with st.form("form_mot_de_passe"):
                st.subheader("Modifier mon mot de passe")
                mot_de_passe_actuel = st.text_input("Mot de passe actuel", type="password")
                nouveau_mot_de_passe = st.text_input("Nouveau mot de passe", type="password")
                confirmation = st.text_input("Confirmer le nouveau mot de passe", type="password")
                bouton = st.form_submit_button("Modifier le mot de passe")

                if bouton:
                    if mot_de_passe_actuel.strip() == "" or nouveau_mot_de_passe.strip() == "" or confirmation.strip() == "":
                        st.error("Tous les champs sont obligatoires.")
                    else:
                        succes, message = changer_mot_de_passe(mot_de_passe_actuel, nouveau_mot_de_passe, confirmation)
                        if succes:
                            st.success(message)
                        else:
                            st.error(message)

        with tab3:
            st.markdown(
                """
                <div class="danger-zone">
                    <h3>Supprimer mon compte</h3>
                    <p>Cette action est définitive. Elle supprimera votre compte utilisateur.</p>
                </div>
                """,
                unsafe_allow_html=True
            )
            with st.form("form_supprimer_compte"):
                confirmation_texte = st.text_input("Écris SUPPRIMER pour confirmer")
                mot_de_passe = st.text_input("Mot de passe", type="password")
                bouton = st.form_submit_button("Supprimer définitivement mon compte")

                if bouton:
                    if confirmation_texte != "SUPPRIMER":
                        st.error("Tu dois écrire exactement SUPPRIMER.")
                    elif mot_de_passe.strip() == "":
                        st.error("Le mot de passe est obligatoire.")
                    else:
                        succes, message = supprimer_compte_utilisateur(mot_de_passe)
                        if succes:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)


if "connecte" not in st.session_state:
    st.session_state["connecte"] = False

if "utilisateur" not in st.session_state:
    st.session_state["utilisateur"] = None

if not st.session_state["connecte"]:
    page_connexion()
    st.stop()

assurer_structure_profil()
lancer_automatisations()


utilisateur = st.session_state["utilisateur"]


# =========================
# MENU PROFESSIONNEL STABLE
# Correction : plus de st.sidebar.radio, donc le CSS ne peut plus cacher les noms.
# =========================

if "current_page" not in st.session_state:
    st.session_state["current_page"] = "dashboard"


def changer_page(page_key):
    st.session_state["current_page"] = page_key


def bouton_menu(page_key, label):
    actif = st.session_state["current_page"] == page_key

    if actif:
        st.sidebar.markdown(
            f"<div class='jb-menu-active'>{nettoyer(label)}</div>",
            unsafe_allow_html=True
        )
    else:
        if st.sidebar.button(label, key=f"menu_{page_key}", use_container_width=True):
            changer_page(page_key)
            st.rerun()


st.sidebar.markdown(
    """
    <div class="jb-logo-box">
        <div class="jb-logo-mark" style="position: relative; display: flex; align-items: center; justify-content: center;">
            JB
            <i class="bi bi-arrow-up-right-short" style="position: absolute; top: 8px; right: 8px; font-size: 24px; color: white;"></i>
        </div>
        <div class="jb-logo-title">JordyBusiness</div>
        <div class="jb-logo-subtitle">jordy_taches</div>
    </div>
    """,
    unsafe_allow_html=True
)

st.sidebar.markdown(f"**Connecté :** {nettoyer(utilisateur['nom'])}")
st.sidebar.caption(nettoyer(utilisateur["email"]))
st.sidebar.markdown("---")
st.sidebar.markdown("<div class='jb-menu-label'>MENU</div>", unsafe_allow_html=True)

bouton_menu("dashboard", "Tableau de bord")
bouton_menu("budget", "Budget mensuel")
bouton_menu("ajouter_tache", "Ajouter une tâche")
bouton_menu("taches", "Mes tâches")
bouton_menu("ajouter_depense", "Ajouter une dépense")
bouton_menu("depenses", "Mes dépenses")
bouton_menu("paiements", "Paiements programmés")
bouton_menu("alertes", "Alertes")
bouton_menu("profil", "Mon profil")

st.sidebar.markdown(
    """
    <div class="jb-sidebar-tip" style="display: flex; gap: 12px; align-items: center; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; padding: 14px; margin-top: 20px;">
        <div style="width: 40px; height: 40px; border-radius: 50%; background: rgba(197, 155, 45, 0.18); display: flex; align-items: center; justify-content: center; font-size: 20px; color: #c59b2d;">
            <i class="bi bi-bullseye"></i>
        </div>
        <div>
            <div style="font-size: 14px !important; font-weight: 700; color: white;">Pilotez vos priorités.</div>
            <div style="font-size: 13px !important; color: rgba(255,255,255,0.7);">Construisez vos résultats.</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

st.sidebar.markdown("---")

if st.sidebar.button("Se déconnecter", use_container_width=True):
    st.session_state["connecte"] = False
    st.session_state["utilisateur"] = None
    st.session_state.pop("automatisations_lancees", None)
    st.session_state["current_page"] = "dashboard"
    st.rerun()


# =========================
# ROUTAGE DES PAGES
# =========================

page_actuelle = st.session_state.get("current_page", "dashboard")

if page_actuelle == "dashboard":
    page_tableau_de_bord()

elif page_actuelle == "budget":
    page_budget()

elif page_actuelle == "ajouter_tache":
    page_ajouter_tache()

elif page_actuelle == "taches":
    page_taches()

elif page_actuelle == "ajouter_depense":
    page_ajouter_depense()

elif page_actuelle == "depenses":
    page_depenses()

elif page_actuelle == "paiements":
    page_paiements_programmes()

elif page_actuelle == "alertes":
    page_alertes()

elif page_actuelle == "profil":
    page_profil()

else:
    st.session_state["current_page"] = "dashboard"
    page_tableau_de_bord()
