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

MOIS_EN = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
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
    total_str = format_euro(total)
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
        titre = nettoyer(traduire_auto_utilisateur(row["titre"]))
        categorie = nettoyer(traduire_auto_utilisateur(row["categorie"]))
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


def appliquer_typographie_globale():
    st.markdown(
        """
        <style>
            html, body, .stApp {
                font-size: 16px !important;
            }

            .stApp, .stMarkdown, p, div, label, input, textarea, button, select {
                font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
            }

            .stMarkdown p,
            div[data-testid="stMarkdownContainer"] p,
            .jb-muted,
            .jb-list-meta,
            .jb-list-note,
            .jb-task-desc,
            .jb-task-meta,
            .profile-email,
            .profile-info-list span {
                font-size: 15px !important;
                line-height: 1.55 !important;
            }

            h1, .page-header-pro h1 {
                font-size: clamp(30px, 3vw, 42px) !important;
                line-height: 1.12 !important;
                letter-spacing: -0.8px !important;
            }

            h2 {
                font-size: 28px !important;
                line-height: 1.18 !important;
            }

            h3 {
                font-size: 22px !important;
                line-height: 1.24 !important;
            }

            .jb-card-title,
            .jb-chart-title,
            .jb-section-title {
                font-size: 18px !important;
                line-height: 1.25 !important;
                font-weight: 900 !important;
            }

            .jb-section-subtitle,
            .jb-chart-subtitle,
            .page-header-pro p {
                font-size: 15.5px !important;
                line-height: 1.55 !important;
            }

            .jb-kpi-label,
            .jb-mini-stat span {
                font-size: 14px !important;
                line-height: 1.35 !important;
                font-weight: 800 !important;
            }

            .jb-kpi-value {
                font-size: clamp(24px, 2.2vw, 32px) !important;
                line-height: 1.1 !important;
            }

            .jb-list-title,
            .jb-task-title {
                font-size: 16px !important;
                line-height: 1.35 !important;
                font-weight: 900 !important;
            }

            .jb-list-amount {
                font-size: 17px !important;
                font-weight: 950 !important;
            }

            div[data-testid="stTextInput"] label p,
            div[data-testid="stTextArea"] label p,
            div[data-testid="stSelectbox"] label p,
            div[data-testid="stNumberInput"] label p,
            div[data-testid="stDateInput"] label p,
            div[data-testid="stTimeInput"] label p,
            div[data-testid="stCheckbox"] label p {
                font-size: 14.5px !important;
                font-weight: 850 !important;
            }

            div[data-baseweb="input"] input,
            div[data-baseweb="textarea"] textarea,
            button {
                font-size: 15px !important;
            }

            @media (max-width: 768px) {
                html, body, .stApp {
                    font-size: 15.5px !important;
                }

                .jb-card-title,
                .jb-chart-title,
                .jb-section-title {
                    font-size: 17px !important;
                }
            }
        </style>
        """,
        unsafe_allow_html=True
    )


appliquer_typographie_globale()

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
        "ALTER TABLE utilisateurs ADD COLUMN pays_region VARCHAR(30) DEFAULT 'Europe'",
        "ALTER TABLE utilisateurs ADD COLUMN devise VARCHAR(10) DEFAULT 'EUR'",
        "ALTER TABLE utilisateurs ADD COLUMN langue VARCHAR(10) DEFAULT 'fr'",
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


# =========================
# PRÉFÉRENCES UTILISATEUR
# Pays / région, devise automatique, langue et traduction complète
# =========================

PAYS_DEVISES = {
    "Europe": "EUR",
    "Afrique": "FCFA",
    "Amérique": "USD",
}

LANGUES = {
    "fr": "Français",
    "en": "English",
}

# Traduction des textes visibles. Les valeurs enregistrées en base restent en français
# pour ne pas casser les filtres, catégories et requêtes existantes.
TRADUCTIONS_EN = {
    # Menus / navigation
    "Tableau de bord": "Dashboard",
    "Budget mensuel": "Monthly budget",
    "Ajouter une tâche": "Add task",
    "Mes tâches": "My tasks",
    "Ajouter une dépense": "Add expense",
    "Mes dépenses": "My expenses",
    "Paiements programmés": "Scheduled payments",
    "Alertes": "Alerts",
    "Mon profil": "My profile",
    "Se déconnecter": "Log out",
    "Connecté :": "Signed in:",
    "MENU": "MENU",
    "Menu rapide": "Quick menu",
    "Ouvrir le menu": "Open menu",
    "Sur téléphone, utilisez ce menu pour ajouter une tâche, saisir une dépense ou ouvrir vos pages.": "On phone or tablet, use this menu to add a task, enter an expense, or open your pages.",
    "Pilotez vos priorités.": "Drive your priorities.",
    "Construisez vos résultats.": "Build your results.",

    # Auth
    "Espace personnel sécurisé": "Secure personal area",
    "Choisissez une action": "Choose an action",
    "Connexion": "Login",
    "Inscription": "Sign up",
    "Votre espace pour gérer tâches, budget et paiements.": "Your space to manage tasks, budget, and payments.",
    "Tâches": "Tasks",
    "Budget": "Budget",
    "Se connecter": "Log in",
    "Entrez votre email et votre mot de passe.": "Enter your email and password.",
    "Adresse email": "Email address",
    "exemple@email.com": "example@email.com",
    "Mot de passe": "Password",
    "Votre mot de passe": "Your password",
    "Veuillez remplir tous les champs.": "Please fill in all fields.",
    "Email ou mot de passe incorrect.": "Incorrect email or password.",
    "Pas encore de compte ? Cliquez sur": "No account yet? Click",
    "Créez votre espace personnel en quelques secondes.": "Create your personal space in a few seconds.",
    "Sécurisé": "Secure",
    "Mobile": "Mobile",
    "Suivi": "Tracking",
    "Créer un compte": "Create an account",
    "Après la création, vous serez ramené automatiquement vers Connexion.": "After creation, you will be redirected to Login automatically.",
    "Nom complet": "Full name",
    "Votre nom complet": "Your full name",
    "Minimum 6 caractères": "Minimum 6 characters",
    "Confirmer le mot de passe": "Confirm password",
    "Répétez le mot de passe": "Repeat password",
    "Créer mon compte": "Create my account",
    "Le nom, l’email et le mot de passe sont obligatoires.": "Name, email, and password are required.",
    "Veuillez entrer une adresse email valide.": "Please enter a valid email address.",
    "Les mots de passe ne correspondent pas.": "Passwords do not match.",
    "Le mot de passe doit contenir au moins 6 caractères.": "Password must contain at least 6 characters.",
    "Compte créé avec succès.": "Account created successfully.",
    "Connectez-vous maintenant avec votre mot de passe.": "Now log in with your password.",
    "Déjà inscrit ? Cliquez sur": "Already registered? Click",
    "Compte créé avec succès. Connectez-vous maintenant avec votre mot de passe.": "Account created successfully. Now log in with your password.",

    # Dashboard
    "Espace JordyBusiness": "JordyBusiness space",
    "Bonjour": "Hello",
    "heureux de vous revoir.": "happy to see you again.",
    "Aujourd’hui, gardez le contrôle sur vos tâches, vos dépenses et vos objectifs.": "Today, stay in control of your tasks, expenses, and goals.",
    "Capital du mois": "Monthly capital",
    "Revenus prévus": "Expected income",
    "Dépenses du mois": "Monthly expenses",
    "du budget": "of budget",
    "Reste disponible": "Available balance",
    "Tâches en retard": "Overdue tasks",
    "À traiter rapidement": "Handle quickly",
    "Vous avez dépensé": "You have spent",
    "de votre budget mensuel.": "of your monthly budget.",
    "dépensés": "spent",
    "budget total": "total budget",
    "Analyse visuelle": "Visual analysis",
    "Vue complète des dépenses, de la progression et des tâches.": "Complete view of expenses, progress, and tasks.",
    "Dépenses par catégorie": "Expenses by category",
    "Aucune dépense enregistrée ce mois.": "No expenses recorded this month.",
    "Répartition du mois de": "Breakdown for",
    "État des tâches": "Task status",
    "Progression globale de votre travail.": "Overall progress of your work.",
    "Progression des dépenses": "Expense progress",
    "Cumul des dépenses jour après jour.": "Cumulative expenses day by day.",
    "Catégories les plus coûteuses": "Most expensive categories",
    "Classement des montants par catégorie.": "Ranking of amounts by category.",
    "Vos prochaines échéances.": "Your next due dates.",
    "Aucun paiement programmé.": "No scheduled payment.",
    "Actif": "Active",
    "Inactif": "Inactive",
    "Tâches récentes": "Recent tasks",
    "Voir toutes les tâches": "View all tasks",
    "Aucune alerte récente.": "No recent alert.",
    "Voir toutes les alertes": "View all alerts",

    # Budget / expenses
    "Mois": "Month",
    "Année": "Year",
    "Progression du budget": "Budget progress",
    "Vous avez utilisé": "You have used",
    "de votre capital mensuel.": "of your monthly capital.",
    "Définir ou modifier le capital du mois": "Set or update the monthly capital",
    "Capital mensuel": "Monthly capital",
    "Enregistrer": "Save",
    "Dépenses de": "Expenses for",
    "Aucune donnée à afficher.": "No data to display.",
    "Aucune dépense à afficher.": "No expenses to display.",
    "Analysez vos dépenses, suivez votre progression et gardez une vision claire de votre budget.": "Analyze your expenses, track your progress, and keep a clear view of your budget.",
    "Dépenses": "Expenses",
    "Diagrammes des dépenses": "Expense charts",
    "Aucune dépense à analyser pour cette période.": "No expense to analyze for this period.",
    "Dépenses enregistrées": "Recorded expenses",
    "Supprimer une dépense": "Delete an expense",
    "Dépense à supprimer": "Expense to delete",
    "Je confirme la suppression.": "I confirm deletion.",
    "Supprimer": "Delete",
    "Coche la confirmation.": "Check the confirmation box.",

    # Tasks
    "Titre": "Title",
    "Description": "Description",
    "Catégorie": "Category",
    "Priorité": "Priority",
    "Date limite": "Deadline",
    "Heure limite": "Deadline time",
    "Durée estimée en minutes": "Estimated duration in minutes",
    "Cette tâche est liée à une dépense ?": "Is this task linked to an expense?",
    "Montant estimé": "Estimated amount",
    "Ajouter la tâche": "Add task",
    "Le titre est obligatoire.": "Title is required.",
    "Le montant doit être supérieur à 0.": "Amount must be greater than 0.",
    "Tâche ajoutée avec succès.": "Task added successfully.",
    "Aucune tâche.": "No task.",
    "Aucune tâche à afficher.": "No task to display.",
    "Total": "Total",
    "À faire": "To do",
    "En cours": "In progress",
    "Terminée": "Completed",
    "Terminées": "Completed",
    "Progression des tâches": "Task progress",
    "des tâches sont terminées.": "of tasks are completed.",
    "Filtrer les tâches": "Filter tasks",
    "Toutes": "All",
    "Modification rapide": "Quick update",
    "Tâche": "Task",
    "Nouveau statut": "New status",
    "Modifier": "Update",
    "Statut": "Status",
    "Échéance": "Due date",
    "Dépense": "Expense",
    "Oui": "Yes",
    "Non": "No",
    "Non définie": "Not set",
    "Non précisé": "Not specified",
    "En retard": "Overdue",
    "Basse": "Low",
    "Moyenne": "Medium",
    "Haute": "High",
    "basse": "low",
    "moyenne": "medium",
    "haute": "high",

    # Add expense / payments
    "Montant": "Amount",
    "Date": "Date",
    "Mode de paiement": "Payment method",
    "Note": "Note",
    "Ajouter la dépense": "Add expense",
    "Dépense ajoutée.": "Expense added.",
    "Programmer un paiement automatique": "Schedule an automatic payment",
    "Exemple : Loyer": "Example: Rent",
    "Fréquence": "Frequency",
    "mensuelle": "monthly",
    "hebdomadaire": "weekly",
    "annuelle": "yearly",
    "Jour du mois": "Day of month",
    "Jour de semaine 1=lundi, 7=dimanche": "Weekday 1=Monday, 7=Sunday",
    "Mois annuel": "Annual month",
    "Prochaine date d'exécution": "Next execution date",
    "Ajouter le paiement programmé": "Add scheduled payment",
    "Liste des paiements programmés": "Scheduled payment list",
    "Paiement": "Payment",
    "Paiement à supprimer": "Payment to delete",
    "Mettre à jour": "Update",
    "État du paiement mis à jour.": "Payment status updated.",
    "Paiement programmé supprimé.": "Scheduled payment deleted.",
    "Paiement introuvable.": "Payment not found.",

    # Alerts / profile
    "Aucune alerte.": "No alert.",
    "Marquer toutes les alertes comme lues": "Mark all alerts as read",
    "Toutes les alertes ont été marquées comme lues.": "All alerts have been marked as read.",
    "Gérez vos informations personnelles, votre sécurité et votre compte.": "Manage your personal information, security, and account.",
    "Téléphone non renseigné": "Phone not provided",
    "Adresse non renseignée": "Address not provided",
    "Informations": "Information",
    "Préférences": "Preferences",
    "Sécurité": "Security",
    "Zone sensible": "Sensitive area",
    "Modifier mes informations": "Update my information",
    "Numéro de téléphone": "Phone number",
    "Adresse": "Address",
    "Photo de profil": "Profile photo",
    "Enregistrer les modifications": "Save changes",
    "L’image est trop grande. Choisis une image de moins de 2 Mo.": "The image is too large. Choose an image under 2 MB.",
    "Le nom et l’email sont obligatoires.": "Name and email are required.",
    "Profil mis à jour avec succès.": "Profile updated successfully.",
    "Pays / Région": "Country / Region",
    "La devise change automatiquement selon la région.": "Currency changes automatically depending on the region.",
    "Devise automatique": "Automatic currency",
    "Aucune conversion n'est faite, seul l'affichage change.": "No conversion is made; only the display changes.",
    "Langue": "Language",
    "La devise est appliquée à tous les montants. Quand English est choisi, l’interface du site passe en anglais.": "Currency is applied to all amounts. The full site translation is active while keeping the current design.",
    "Enregistrer les préférences": "Save preferences",
    "Préférences mises à jour.": "Preferences updated.",
    "Devise utilisée": "Currency used",
    "Modifier mon mot de passe": "Change my password",
    "Mot de passe actuel": "Current password",
    "Nouveau mot de passe": "New password",
    "Confirmer le nouveau mot de passe": "Confirm new password",
    "Modifier le mot de passe": "Change password",
    "Tous les champs sont obligatoires.": "All fields are required.",
    "Le mot de passe actuel est incorrect.": "Current password is incorrect.",
    "Le nouveau mot de passe doit contenir au moins 6 caractères.": "The new password must contain at least 6 characters.",
    "Mot de passe modifié avec succès.": "Password changed successfully.",
    "Supprimer mon compte": "Delete my account",
    "Cette action est définitive. Elle supprimera votre compte utilisateur.": "This action is permanent. It will delete your user account.",
    "Écris SUPPRIMER pour confirmer": "Type DELETE to confirm",
    "Supprimer définitivement mon compte": "Permanently delete my account",
    "Tu dois écrire exactement SUPPRIMER.": "You must type DELETE exactly.",
    "Le mot de passe est obligatoire.": "Password is required.",
    "Mot de passe incorrect. Suppression annulée.": "Incorrect password. Deletion canceled.",
    "Compte supprimé avec succès.": "Account deleted successfully.",

    # Categories / modes
    "Études": "Studies",
    "Travail": "Work",
    "Maison": "Home",
    "Santé": "Health",
    "Courses": "Groceries",
    "Personnel": "Personal",
    "Autre": "Other",
    "Logement": "Housing",
    "Nourriture": "Food",
    "Transport": "Transport",
    "Facture": "Bills",
    "Loisirs": "Leisure",
    "Espèces": "Cash",
    "Carte bancaire": "Bank card",
    "Mobile Money": "Mobile Money",
    "Virement": "Bank transfer",

    # Months
    "Janvier": "January",
    "Février": "February",
    "Mars": "March",
    "Avril": "April",
    "Mai": "May",
    "Juin": "June",
    "Juillet": "July",
    "Août": "August",
    "Septembre": "September",
    "Octobre": "October",
    "Novembre": "November",
    "Décembre": "December",

    # Misc
    "Aucune tâche récente.": "No recent task.",
    "Montant dépensé": "Amount spent",
    "Jour du mois": "Day of month",
    "Cumul": "Cumulative",
    "Nombre de tâches": "Number of tasks",
    "Dépense automatique créée": "Automatic expense created",
    "Dépense créée automatiquement depuis une tâche terminée.": "Expense automatically created from a completed task.",
    "Dépense créée automatiquement depuis un paiement programmé.": "Expense automatically created from a scheduled payment.",
    "Paiement automatique exécuté": "Automatic payment executed",
    "Budget insuffisant": "Insufficient budget",
    "Paiement exécuté automatiquement.": "Payment executed automatically.",
    "Budget insuffisant.": "Insufficient budget.",
    "Tâche introuvable.": "Task not found.",
    "Dépense introuvable.": "Expense not found.",
    "Tâche supprimée.": "Task deleted.",
    "Dépense supprimée.": "Expense deleted.",
    "Statut modifié avec succès.": "Status updated successfully.",
    "Statut modifié. Une dépense a été créée automatiquement.": "Status updated. An expense was created automatically.",
    "Connexion MySQL impossible.": "MySQL connection impossible.",
    "Vérifie XAMPP, MySQL et database.py.": "Check XAMPP, MySQL, and database.py.",
}


def devise_depuis_pays(pays_region):
    return PAYS_DEVISES.get(pays_region, "EUR")


def symbole_devise(devise):
    if devise == "EUR":
        return "€"
    if devise == "USD":
        return "$"
    if devise == "FCFA":
        return "FCFA"
    return devise


def langue_utilisateur():
    utilisateur = st.session_state.get("utilisateur") or {}
    langue = utilisateur.get("langue") or st.session_state.get("langue_interface", "fr") or "fr"
    return langue if langue in LANGUES else "fr"


def traduire_texte(texte):
    if texte is None or langue_utilisateur() != "en":
        return texte

    if not isinstance(texte, str):
        return texte

    resultat = texte

    # Remplacements longs d'abord pour éviter les traductions partielles incorrectes.
    for fr, en in sorted(TRADUCTIONS_EN.items(), key=lambda item: len(item[0]), reverse=True):
        resultat = resultat.replace(fr, en)

    return resultat




def _texte_simple_pour_traduction_auto(texte):
    if not isinstance(texte, str):
        return False

    texte = texte.strip()
    if texte == "":
        return False

    # Ne pas envoyer le HTML/CSS/JS au traducteur automatique.
    if "<" in texte and ">" in texte:
        return False

    # Ne pas traduire les emails, liens, clés techniques ou textes trop longs.
    if "@" in texte or "http://" in texte or "https://" in texte:
        return False

    if len(texte) > 500:
        return False

    return True


@st.cache_data(show_spinner=False, ttl=86400)
def _traduction_auto_cache(texte, cible):
    try:
        from deep_translator import GoogleTranslator
        resultat = GoogleTranslator(source="auto", target=cible).translate(texte)
        return resultat or texte
    except Exception:
        return texte


def traduire_auto_utilisateur(texte):
    """Traduit les textes saisis par l'utilisateur uniquement à l'affichage.

    Les données originales restent dans MySQL. Si la langue est English,
    les titres, notes, descriptions, catégories et alertes peuvent être affichés en anglais.
    """
    if texte is None:
        return ""

    if langue_utilisateur() != "en":
        return texte

    if not isinstance(texte, str):
        texte = str(texte)

    # D'abord les traductions fixes du site.
    texte_traduit = traduire_texte(texte)

    # Ensuite, traduction automatique pour les textes libres de l'utilisateur.
    if _texte_simple_pour_traduction_auto(texte_traduit):
        return _traduction_auto_cache(texte_traduit, "en")

    return texte_traduit

def t(texte):
    return traduire_texte(texte)


def devise_utilisateur():
    utilisateur = st.session_state.get("utilisateur") or {}
    pays_region = utilisateur.get("pays_region", "Europe") or "Europe"
    devise = utilisateur.get("devise") or devise_depuis_pays(pays_region)
    return devise


def format_monnaie(valeur, devise=None):
    devise = devise or devise_utilisateur()

    try:
        valeur = float(valeur or 0)
    except Exception:
        valeur = 0.0

    if devise == "USD":
        return f"${valeur:,.2f}"

    if devise == "FCFA":
        return f"{valeur:,.0f} FCFA".replace(",", " ")

    return f"{valeur:,.2f}".replace(",", " ").replace(".", ",") + " €"


def format_euro(valeur):
    # Ancien nom conservé pour ne pas casser les appels existants.
    # Cette fonction affiche maintenant la devise choisie par l'utilisateur.
    return format_monnaie(valeur)


# Patch léger de Streamlit : quand l'utilisateur choisit English,
# les labels, boutons, messages, titres et HTML affichés sont traduits.
def _installer_traduction_streamlit():
    try:
        from streamlit.delta_generator import DeltaGenerator
    except Exception:
        return

    if getattr(DeltaGenerator, "_jb_traduction_installee", False):
        return

    def traduire_args_kwargs(args, kwargs, traduire_premier_arg=True):
        args = list(args)
        if traduire_premier_arg and args and isinstance(args[0], str):
            args[0] = traduire_texte(args[0])

        for cle in ["label", "placeholder", "help", "body", "caption", "text"]:
            if cle in kwargs and isinstance(kwargs[cle], str):
                kwargs[cle] = traduire_texte(kwargs[cle])

        return tuple(args), kwargs

    def wrap_simple(nom):
        original = getattr(DeltaGenerator, nom, None)
        if original is None:
            return

        def wrapper(self, *args, **kwargs):
            args, kwargs = traduire_args_kwargs(args, kwargs)
            return original(self, *args, **kwargs)

        setattr(DeltaGenerator, nom, wrapper)

    def wrap_options(nom):
        original = getattr(DeltaGenerator, nom, None)
        if original is None:
            return

        def wrapper(self, *args, **kwargs):
            args = list(args)
            if args and isinstance(args[0], str):
                args[0] = traduire_texte(args[0])
            for cle in ["label", "placeholder", "help"]:
                if cle in kwargs and isinstance(kwargs[cle], str):
                    kwargs[cle] = traduire_texte(kwargs[cle])

            format_func_original = kwargs.get("format_func", None)
            if format_func_original is None:
                kwargs["format_func"] = lambda x: traduire_texte(str(x))
            else:
                kwargs["format_func"] = lambda x, f=format_func_original: traduire_texte(str(f(x)))

            return original(self, *args, **kwargs)

        setattr(DeltaGenerator, nom, wrapper)

    def wrap_tabs():
        original = getattr(DeltaGenerator, "tabs", None)
        if original is None:
            return

        def wrapper(self, tabs, *args, **kwargs):
            if isinstance(tabs, (list, tuple)):
                tabs = [traduire_texte(str(tab)) for tab in tabs]
            return original(self, tabs, *args, **kwargs)

        setattr(DeltaGenerator, "tabs", wrapper)

    for nom in [
        "markdown", "title", "header", "subheader", "caption", "text", "write",
        "info", "success", "error", "warning", "button", "form_submit_button",
        "checkbox", "text_input", "text_area", "number_input", "date_input", "time_input",
        "file_uploader", "expander",
    ]:
        wrap_simple(nom)

    for nom in ["selectbox", "radio", "multiselect"]:
        wrap_options(nom)

    wrap_tabs()
    DeltaGenerator._jb_traduction_installee = True


_installer_traduction_streamlit()


def nom_mois(mois):
    if langue_utilisateur() == "en":
        return MOIS_EN.get(int(mois), str(mois))
    return MOIS_FR.get(int(mois), str(mois))

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
        st.session_state["langue_interface"] = utilisateur.get("langue", "fr") or "fr"
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



def mettre_a_jour_preferences(pays_region, langue):
    devise = devise_depuis_pays(pays_region)

    connection = connexion_mysql()
    if connection is None:
        return False, "Connexion MySQL impossible."

    cursor = connection.cursor()
    cursor.execute(
        """
        UPDATE utilisateurs
        SET pays_region = %s, devise = %s, langue = %s
        WHERE id = %s
        """,
        (pays_region, devise, langue, id_utilisateur())
    )

    connection.commit()
    cursor.close()
    connection.close()
    recharger_utilisateur_session()
    st.session_state["langue_interface"] = langue

    return True, f"Préférences mises à jour. Devise utilisée : {symbole_devise(devise)} ({devise})."


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
                <span>{nettoyer(traduire_auto_utilisateur(cat))}</span>
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
        titre = nettoyer(traduire_auto_utilisateur(d.get("titre", "Dépense")))
        categorie = nettoyer(traduire_auto_utilisateur(d.get("categorie", "Autre")))
        montant = format_euro(d.get("montant", 0))
        date_depense = format_date_affichage(d.get("date_depense"))
        mode = nettoyer(traduire_auto_utilisateur(d.get("mode_paiement", "Non précisé")))
        note = nettoyer(traduire_auto_utilisateur(d.get("note", "")))
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
        titre = nettoyer(traduire_auto_utilisateur(t.get("titre", "Tâche")))
        description = nettoyer(traduire_auto_utilisateur(t.get("description", "")))
        categorie = nettoyer(traduire_auto_utilisateur(t.get("categorie", "Autre")))
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


AUTH_POSTER_IMAGE_BASE64 = """
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
""".replace("\n", "")


def page_connexion():
    # Page connexion / inscription professionnelle : fond clair, deux panneaux collés,
    # affiche complète à gauche et formulaire centré à droite.
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

        html, body {
            overflow-x: hidden !important;
        }

        .stApp {
            background:
                radial-gradient(circle at 15% 12%, rgba(59, 130, 246, 0.12), transparent 30%),
                radial-gradient(circle at 92% 88%, rgba(14, 165, 233, 0.12), transparent 34%),
                linear-gradient(180deg, #ffffff 0%, #f3f7fb 100%) !important;
            color: #0f172a !important;
        }

        .block-container {
            max-width: 1240px !important;
            padding-top: clamp(18px, 3vh, 34px) !important;
            padding-left: clamp(12px, 2vw, 24px) !important;
            padding-right: clamp(12px, 2vw, 24px) !important;
            padding-bottom: clamp(18px, 3vh, 34px) !important;
        }

        /* Le bloc global : deux cadres collés, centrés, sans espace vide. */
        div[data-testid="stHorizontalBlock"]:has(.jb-auth-poster-wrap) {
            gap: 0 !important;
            align-items: stretch !important;
            justify-content: center !important;
            min-height: calc(100vh - 70px) !important;
            width: 100% !important;
            filter: drop-shadow(0 26px 65px rgba(15, 23, 42, 0.14));
        }

        div[data-testid="stHorizontalBlock"]:has(.jb-auth-poster-wrap) > div[data-testid="column"],
        div[data-testid="stHorizontalBlock"]:has(.jb-auth-poster-wrap) > div {
            padding-left: 0 !important;
            padding-right: 0 !important;
        }

        /* Panneau gauche : affiche portefeuille électronique. */
        .jb-auth-poster-wrap {
            height: min(720px, calc(100vh - 76px));
            min-height: 620px;
            width: 100%;
            overflow: hidden;
            border-radius: 32px 0 0 32px;
            background: linear-gradient(135deg, #020617 0%, #061a3d 100%);
            border: 1px solid rgba(226, 232, 240, 0.65);
            border-right: none;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .jb-auth-poster-wrap img {
            width: 100%;
            height: 100%;
            display: block;
            object-fit: cover !important;
            object-position: center center !important;
        }

        /* Panneau droit : vrai cadre blanc professionnel. */
        div[data-testid="stHorizontalBlock"]:has(.jb-auth-poster-wrap) > div[data-testid="column"]:nth-child(2),
        div[data-testid="stHorizontalBlock"]:has(.jb-auth-poster-wrap) > div:nth-child(2),
        div[data-testid="column"]:has(.jb-auth-right-marker) {
            height: min(720px, calc(100vh - 76px)) !important;
            min-height: 620px !important;
            background: #ffffff !important;
            border-radius: 0 32px 32px 0 !important;
            border: 1px solid rgba(226, 232, 240, 0.95) !important;
            border-left: none !important;
            padding: 0 !important;
            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;
        }

        div[data-testid="column"]:has(.jb-auth-right-marker) > div,
        div[data-testid="stHorizontalBlock"]:has(.jb-auth-poster-wrap) > div:nth-child(2) > div {
            width: 100% !important;
        }

        .jb-auth-right-marker {
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        .jb-auth-form-space {
            max-width: 480px;
            margin: 0 auto;
            padding: 0 clamp(24px, 4vw, 46px);
        }

        /* Onglets Connexion / Inscription. */
        div[role="radiogroup"] {
            max-width: 480px !important;
            width: calc(100% - 64px) !important;
            margin: 0 auto 34px auto !important;
            display: grid !important;
            grid-template-columns: 1fr 1fr !important;
            gap: 0 !important;
            padding: 6px !important;
            border-radius: 18px !important;
            background: #f1f5f9 !important;
            border: 1px solid #e2e8f0 !important;
            box-shadow: none !important;
            overflow: hidden !important;
        }

        div[role="radiogroup"] label {
            width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
            cursor: pointer !important;
        }

        div[role="radiogroup"] label > div:first-child {
            display: none !important;
        }

        div[role="radiogroup"] label p,
        div[role="radiogroup"] label > div:last-child {
            width: 100% !important;
            text-align: center !important;
            padding: 14px 8px !important;
            border-radius: 13px !important;
            color: #64748b !important;
            font-size: 16px !important;
            line-height: 1.2 !important;
            font-weight: 900 !important;
            border: none !important;
            transition: all .16s ease !important;
        }

        div[role="radiogroup"] label:has(input:checked) p,
        div[role="radiogroup"] label:has(input:checked) > div:last-child {
            color: #ffffff !important;
            background: linear-gradient(135deg, #0b63f6 0%, #06b6d4 100%) !important;
            box-shadow: 0 12px 25px rgba(11, 99, 246, 0.24) !important;
        }

        /* Le formulaire : pas de carte séparée, il fait partie du panneau blanc. */
        div[data-testid="stForm"] {
            max-width: 480px !important;
            width: calc(100% - 64px) !important;
            margin: 0 auto !important;
            background: transparent !important;
            border: none !important;
            border-radius: 0 !important;
            padding: 0 !important;
            box-shadow: none !important;
        }

        div[data-testid="stForm"] > div {
            padding: 0 !important;
        }

        .jb-auth-title {
            color: #06132b !important;
            font-size: clamp(30px, 3vw, 40px) !important;
            line-height: 1.05 !important;
            font-weight: 950 !important;
            letter-spacing: -1.2px !important;
            margin: 0 0 10px 0 !important;
            text-align: left !important;
        }

        .jb-auth-subtitle {
            color: #64748b !important;
            font-size: 16.5px !important;
            line-height: 1.55 !important;
            font-weight: 650 !important;
            margin: 0 0 28px 0 !important;
            text-align: left !important;
        }

        div[data-testid="stTextInput"] {
            margin-bottom: 18px !important;
        }

        div[data-testid="stTextInput"] label,
        div[data-testid="stTextInput"] label p {
            color: #334155 !important;
            opacity: 1 !important;
            visibility: visible !important;
            font-size: 15px !important;
            line-height: 1.2 !important;
            font-weight: 850 !important;
            margin-bottom: 8px !important;
        }

        div[data-testid="stTextInput"] input,
        div[data-baseweb="input"] input {
            min-height: 56px !important;
            width: 100% !important;
            background: #ffffff !important;
            color: #0f172a !important;
            border: 1.5px solid #dbe3ef !important;
            border-radius: 15px !important;
            font-size: 16px !important;
            font-weight: 700 !important;
            padding: 14px 16px !important;
            box-shadow: 0 8px 22px rgba(15, 23, 42, 0.04) !important;
        }

        div[data-testid="stTextInput"] input:focus,
        div[data-baseweb="input"] input:focus {
            border-color: #0b63f6 !important;
            box-shadow: 0 0 0 4px rgba(11, 99, 246, 0.10) !important;
        }

        div[data-testid="stTextInput"] input::placeholder {
            color: #94a3b8 !important;
            opacity: 1 !important;
        }

        div[data-testid="stTextInput"] button {
            border-radius: 0 15px 15px 0 !important;
            background: #ffffff !important;
            color: #475569 !important;
        }

        div[data-testid="stCheckbox"] label,
        div[data-testid="stCheckbox"] label p {
            color: #334155 !important;
            font-size: 14px !important;
            font-weight: 750 !important;
        }

        .jb-forgot-link {
            text-align: right;
            padding-top: 7px;
        }

        .jb-forgot-link a {
            color: #0b63f6 !important;
            font-size: 14px !important;
            font-weight: 850 !important;
            text-decoration: none !important;
        }

        div[data-testid="stForm"] .stFormSubmitButton button {
            width: 100% !important;
            min-height: 60px !important;
            margin-top: 16px !important;
            border: none !important;
            border-radius: 16px !important;
            background: linear-gradient(135deg, #0b63f6 0%, #06b6d4 100%) !important;
            color: #ffffff !important;
            font-size: 17px !important;
            font-weight: 950 !important;
            box-shadow: 0 18px 38px rgba(11, 99, 246, 0.25) !important;
            transition: all .18s ease !important;
        }

        div[data-testid="stForm"] .stFormSubmitButton button:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 22px 46px rgba(11, 99, 246, 0.34) !important;
        }

        .jb-biometric-wrap {
            max-width: 480px;
            width: calc(100% - 64px);
            margin: 26px auto 0 auto;
        }

        .jb-biometric {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 14px;
            color: #94a3b8 !important;
            font-size: 13px !important;
            font-weight: 850 !important;
        }

        .jb-biometric::before,
        .jb-biometric::after {
            content: "";
            height: 1px;
            flex: 1;
            background: #e2e8f0;
        }

        .jb-fingerprint {
            width: 58px;
            height: 58px;
            margin: 18px auto 0 auto;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #ffffff;
            border: 1px solid #e2e8f0;
            box-shadow: 0 14px 30px rgba(15, 23, 42, 0.08);
            color: #0b63f6 !important;
            font-size: 29px !important;
        }

        .jb-auth-footer {
            max-width: 480px;
            width: calc(100% - 64px);
            margin: 28px auto 0 auto;
            text-align: center;
            color: #94a3b8 !important;
            font-size: 11px !important;
            font-weight: 950 !important;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .jb-auth-footer span {
            color: #0b63f6 !important;
            font-size: inherit !important;
            font-weight: 950 !important;
        }

        .jb-auth-footer b {
            color: #ef4444 !important;
            font-size: inherit !important;
        }

        div[data-testid="stAlert"] {
            max-width: 480px !important;
            width: calc(100% - 64px) !important;
            margin-left: auto !important;
            margin-right: auto !important;
            border-radius: 14px !important;
            font-weight: 750 !important;
        }

        /* Tablettes : les panneaux passent l'un sous l'autre, sans casser la lisibilité. */
        @media (max-width: 980px) {
            .block-container {
                max-width: 760px !important;
                padding-top: 18px !important;
                padding-bottom: 22px !important;
            }

            div[data-testid="stHorizontalBlock"]:has(.jb-auth-poster-wrap) {
                flex-direction: column !important;
                min-height: auto !important;
            }

            .jb-auth-poster-wrap {
                height: 520px !important;
                min-height: 520px !important;
                border-radius: 28px 28px 0 0 !important;
                border-right: 1px solid rgba(226, 232, 240, 0.65) !important;
                border-bottom: none !important;
            }

            .jb-auth-poster-wrap img {
                object-fit: cover !important;
                object-position: center center !important;
            }

            div[data-testid="stHorizontalBlock"]:has(.jb-auth-poster-wrap) > div[data-testid="column"]:nth-child(2),
            div[data-testid="stHorizontalBlock"]:has(.jb-auth-poster-wrap) > div:nth-child(2),
            div[data-testid="column"]:has(.jb-auth-right-marker) {
                height: auto !important;
                min-height: auto !important;
                border-radius: 0 0 28px 28px !important;
                border-left: 1px solid rgba(226, 232, 240, 0.95) !important;
                border-top: none !important;
                padding: 34px 0 38px 0 !important;
            }
        }

        /* Téléphones : affiche plus compacte, formulaire plein écran propre. */
        @media (max-width: 560px) {
            .block-container {
                padding: 0 !important;
                max-width: 100% !important;
            }

            .jb-auth-poster-wrap {
                height: 360px !important;
                min-height: 360px !important;
                border-radius: 0 !important;
                border-left: none !important;
                border-right: none !important;
            }

            .jb-auth-poster-wrap img {
                object-fit: cover !important;
                object-position: center top !important;
            }

            div[data-testid="stHorizontalBlock"]:has(.jb-auth-poster-wrap) > div[data-testid="column"]:nth-child(2),
            div[data-testid="stHorizontalBlock"]:has(.jb-auth-poster-wrap) > div:nth-child(2),
            div[data-testid="column"]:has(.jb-auth-right-marker) {
                border-radius: 0 !important;
                border-left: none !important;
                border-right: none !important;
                padding: 24px 0 30px 0 !important;
            }

            div[role="radiogroup"],
            div[data-testid="stForm"],
            .jb-biometric-wrap,
            .jb-auth-footer,
            div[data-testid="stAlert"] {
                width: calc(100% - 28px) !important;
                max-width: none !important;
            }

            div[role="radiogroup"] {
                margin-bottom: 26px !important;
                border-radius: 16px !important;
            }

            div[role="radiogroup"] label p,
            div[role="radiogroup"] label > div:last-child {
                font-size: 15px !important;
                padding: 13px 6px !important;
            }

            .jb-auth-title {
                font-size: 30px !important;
            }

            .jb-auth-subtitle {
                font-size: 14.5px !important;
                margin-bottom: 22px !important;
            }

            div[data-testid="stTextInput"] input,
            div[data-baseweb="input"] input {
                min-height: 52px !important;
                font-size: 15px !important;
            }

            .jb-forgot-link {
                text-align: left !important;
                padding-top: 0 !important;
            }
        }
    </style>
    """)

    if st.session_state.get("auth_mode") not in ["Connexion", "Inscription"]:
        st.session_state["auth_mode"] = "Connexion"

    if "login_email" not in st.session_state:
        st.session_state["login_email"] = ""

    if "auth_mode_a_appliquer" in st.session_state:
        st.session_state["auth_mode"] = st.session_state.pop("auth_mode_a_appliquer")

    col_affiche, col_form = st.columns([1.08, 0.92], gap="small")

    with col_affiche:
        st.markdown(
            f"""
            <div class="jb-auth-poster-wrap">
                <img src="data:image/jpeg;base64,{AUTH_POSTER_IMAGE_BASE64}" alt="JordyBusiness portefeuille digital">
            </div>
            """,
            unsafe_allow_html=True
        )

    with col_form:
        st.markdown('<div class="jb-auth-right-marker"></div>', unsafe_allow_html=True)

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
                st.markdown(
                    """
                    <div class="jb-auth-title">Bon retour !</div>
                    <div class="jb-auth-subtitle">Connectez-vous à votre compte pour accéder à votre portefeuille.</div>
                    """,
                    unsafe_allow_html=True
                )

                email = st.text_input(
                    "Email",
                    placeholder="exemple@domaine.com",
                    key="login_email"
                )

                mot_de_passe = st.text_input(
                    "Mot de passe",
                    type="password",
                    placeholder="Votre mot de passe",
                    key="login_password"
                )

                c1, c2 = st.columns([1, 1])
                with c1:
                    st.checkbox("Se souvenir de moi", key="remember_me")
                with c2:
                    st.markdown('<div class="jb-forgot-link"><a href="#">Mot de passe oublié ?</a></div>', unsafe_allow_html=True)

                bouton = st.form_submit_button("Se connecter  →")

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

            st.markdown(
                """
                <div class="jb-biometric-wrap">
                    <div class="jb-biometric">ou continuer avec</div>
                    <div class="jb-fingerprint"><i class="bi bi-fingerprint"></i></div>
                </div>
                """,
                unsafe_allow_html=True
            )

        else:
            with st.form("inscription"):
                st.markdown(
                    """
                    <div class="jb-auth-title">Créer un compte</div>
                    <div class="jb-auth-subtitle">Ouvrez votre espace JordyBusiness en quelques secondes.</div>
                    """,
                    unsafe_allow_html=True
                )

                nom = st.text_input(
                    "Nom complet",
                    placeholder="Votre nom complet",
                    key="register_name"
                )

                email = st.text_input(
                    "Email",
                    placeholder="exemple@domaine.com",
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

                bouton = st.form_submit_button("Créer mon compte  →")

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

        st.markdown(
            """
            <div class="jb-auth-footer">
                Created with <b>♥</b> by <span>JordyBalou</span>
            </div>
            """,
            unsafe_allow_html=True
        )

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
                    <div class="jb-mini-row-left"><div class="jb-mini-icon"><i class="bi bi-{icone}"></i></div><div><strong>{nettoyer(traduire_auto_utilisateur(p['titre']))}</strong><span>{p['prochaine_date']}</span></div></div>
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
                md(f"""<div class="{classe}"><strong>{nettoyer(traduire_auto_utilisateur(alerte['titre']))}</strong><br>{nettoyer(traduire_auto_utilisateur(alerte['message']))}</div>""")
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
                <strong>{nettoyer(traduire_auto_utilisateur(alerte["titre"]))}</strong><br>
                {nettoyer(traduire_auto_utilisateur(alerte["message"]))}<br>
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
    pays_region = utilisateur.get("pays_region", "Europe") or "Europe"
    devise = utilisateur.get("devise", devise_depuis_pays(pays_region)) or devise_depuis_pays(pays_region)
    langue = utilisateur.get("langue", "fr") or "fr"

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
                    <div><i class="bi bi-globe"></i><span>{nettoyer(pays_region)} · {LANGUES.get(langue, "Français")}</span></div>
                    <div><i class="bi bi-currency-exchange"></i><span>{symbole_devise(devise)} ({nettoyer(devise)})</span></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col_droite:
        tab1, tab2, tab3, tab4 = st.tabs(["Informations", "Préférences", "Sécurité", "Zone sensible"])

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
            with st.form("form_preferences"):
                st.subheader("Préférences")

                pays_options = list(PAYS_DEVISES.keys())
                if pays_region not in pays_options:
                    pays_region_index = 0
                else:
                    pays_region_index = pays_options.index(pays_region)

                nouveau_pays_region = st.selectbox(
                    "Pays / Région",
                    pays_options,
                    index=pays_region_index,
                    help="La devise change automatiquement selon la région."
                )

                devise_auto = devise_depuis_pays(nouveau_pays_region)
                st.info(f"Devise automatique : {symbole_devise(devise_auto)} ({devise_auto}). Aucune conversion n'est faite, seul l'affichage change.")

                langue_labels = ["Français", "English"]
                langue_actuelle_label = "English" if langue == "en" else "Français"
                nouvelle_langue_label = st.selectbox(
                    "Langue",
                    langue_labels,
                    index=langue_labels.index(langue_actuelle_label)
                )
                nouvelle_langue = "en" if nouvelle_langue_label == "English" else "fr"

                st.caption("La devise est appliquée à tous les montants. Quand English est choisi, l’interface du site passe en anglais.")

                bouton_preferences = st.form_submit_button("Enregistrer les préférences")

                if bouton_preferences:
                    succes, message = mettre_a_jour_preferences(nouveau_pays_region, nouvelle_langue)
                    if succes:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

        with tab3:
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

        with tab4:
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

PAGES_VALIDES = {
    "dashboard", "budget", "ajouter_tache", "taches", "ajouter_depense",
    "depenses", "paiements", "alertes", "profil"
}

try:
    page_url = st.query_params.get("page", None)
except Exception:
    try:
        page_url = st.experimental_get_query_params().get("page", [None])[0]
    except Exception:
        page_url = None

if page_url in PAGES_VALIDES:
    st.session_state["current_page"] = page_url


def changer_page(page_key):
    st.session_state["current_page"] = page_key
    try:
        st.query_params["page"] = page_key
    except Exception:
        try:
            st.experimental_set_query_params(page=page_key)
        except Exception:
            pass


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
# MENU RAPIDE POUR TÉLÉPHONE / TABLETTE
# Visible seulement sur téléphone et tablette, sous forme de menu déroulant.
# Sur ordinateur, ce bloc est caché et seule la sidebar reste affichée.
# =========================

MENU_RAPIDE = [
    ("dashboard", "Tableau de bord"),
    ("ajouter_tache", "Ajouter une tâche"),
    ("taches", "Mes tâches"),
    ("ajouter_depense", "Ajouter une dépense"),
    ("depenses", "Mes dépenses"),
    ("budget", "Budget mensuel"),
    ("paiements", "Paiements programmés"),
    ("alertes", "Alertes"),
    ("profil", "Mon profil"),
]


def afficher_menu_rapide_mobile():
    page_actuelle = st.session_state.get("current_page", "dashboard")

    liens = ""
    for page_key, label in MENU_RAPIDE:
        label_affiche = nettoyer(t(label))
        classe = "jb-mobile-link-active" if page_key == page_actuelle else ""
        liens += f"""
        <a class="jb-mobile-dropdown-link {classe}" href="?page={page_key}">
            {label_affiche}
        </a>
        """

    st.markdown(
        f"""
        <style>
            .jb-mobile-menu-only {{
                display: none;
            }}

            @media (max-width: 1024px) {{
                .jb-mobile-menu-only {{
                    display: block;
                    margin: 0 0 16px 0;
                }}

                .jb-mobile-dropdown {{
                    background: #ffffff;
                    border: 1px solid #e2e8f0;
                    border-radius: 18px;
                    box-shadow: 0 14px 34px rgba(15, 23, 42, 0.09);
                    overflow: hidden;
                }}

                .jb-mobile-dropdown summary {{
                    list-style: none;
                    cursor: pointer;
                    padding: 14px 16px;
                    font-weight: 900;
                    color: #0f172a;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    gap: 12px;
                }}

                .jb-mobile-dropdown summary::-webkit-details-marker {{
                    display: none;
                }}

                .jb-mobile-dropdown summary::after {{
                    content: "⌄";
                    width: 30px;
                    height: 30px;
                    border-radius: 999px;
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    background: #f1f5f9;
                    color: #0f766e;
                    font-size: 18px;
                    font-weight: 900;
                }}

                .jb-mobile-dropdown[open] summary::after {{
                    content: "⌃";
                }}

                .jb-mobile-dropdown-text {{
                    padding: 0 16px 12px 16px;
                    color: #64748b;
                    font-size: 13px;
                    font-weight: 650;
                    line-height: 1.45;
                    border-bottom: 1px solid #f1f5f9;
                }}

                .jb-mobile-dropdown-list {{
                    padding: 8px;
                    display: grid;
                    gap: 6px;
                }}

                .jb-mobile-dropdown-link {{
                    display: block;
                    text-decoration: none !important;
                    color: #334155 !important;
                    background: #f8fafc;
                    border: 1px solid #edf2f7;
                    border-radius: 12px;
                    padding: 11px 13px;
                    font-size: 14px;
                    font-weight: 850;
                }}

                .jb-mobile-dropdown-link:hover,
                .jb-mobile-link-active {{
                    background: linear-gradient(135deg, #1e3a8a, #0f766e) !important;
                    color: #ffffff !important;
                    border-color: transparent !important;
                }}
            }}
        </style>

        <div class="jb-mobile-menu-only">
            <details class="jb-mobile-dropdown">
                <summary>{nettoyer(t("Menu rapide"))}</summary>
                <div class="jb-mobile-dropdown-text">
                    {nettoyer(t("Sur téléphone, utilisez ce menu pour ajouter une tâche, saisir une dépense ou ouvrir vos pages."))}
                </div>
                <div class="jb-mobile-dropdown-list">
                    {liens}
                </div>
            </details>
        </div>
        """,
        unsafe_allow_html=True
    )


afficher_menu_rapide_mobile()

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
