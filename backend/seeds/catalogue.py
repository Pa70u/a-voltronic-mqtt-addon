"""Catalogue des prestations par défaut pour un garage automobile.

Récupéré du `frontend/index.html` legacy (constante `PRESTATIONS`).
Sert au bootstrap initial — éditable ensuite par l'admin.
"""

CATALOGUE_DEFAUT = [
    {
        "famille": "Vidange & Filtres",
        "icone": "🛢️",
        "prestations": [
            ("Vidange huile moteur + filtre à huile", 45),
            ("Remplacement filtre à air", 25),
            ("Remplacement filtre d'habitacle / climatisation", 20),
            ("Remplacement filtre à carburant diesel", 35),
            ("Remplacement filtre à carburant essence", 30),
            ("Kit révision complet (huile + 4 filtres)", 120),
        ],
    },
    {
        "famille": "Freinage",
        "icone": "🛑",
        "prestations": [
            ("Remplacement plaquettes de frein avant", 80),
            ("Remplacement plaquettes de frein arrière", 75),
            ("Remplacement disques + plaquettes avant", 180),
            ("Remplacement disques + plaquettes arrière", 170),
            ("Remplacement disques + plaquettes 4 roues", 320),
            ("Remplacement tambours + mâchoires arrière", 160),
            ("Purge circuit de freinage", 45),
            ("Remplacement flexible de frein", 55),
            ("Remplacement étrier de frein avant", 140),
            ("Remplacement étrier de frein arrière", 130),
            ("Réglage frein à main", 25),
        ],
    },
    {
        "famille": "Distribution & Moteur",
        "icone": "⚙️",
        "prestations": [
            ("Remplacement courroie de distribution", 280),
            ("Kit distribution complet (courroie + galet + pompe à eau)", 420),
            ("Remplacement chaîne de distribution", 380),
            ("Remplacement courroie accessoires", 95),
            ("Remplacement joints de culasse", 650),
            ("Remplacement joints de soupapes", 420),
            ("Diagnostic moteur (lecture codes défauts)", 55),
            ("Remplacement bougies d'allumage (4 cyl.)", 85),
            ("Remplacement bougies de préchauffage (4 cyl.)", 120),
            ("Remplacement bobine d'allumage", 90),
            ("Remplacement injecteurs (unité)", 180),
            ("Nettoyage injecteurs", 120),
            ("Remplacement turbo", 850),
            ("Remplacement vanne EGR", 280),
            ("Nettoyage vanne EGR", 95),
            ("Remplacement FAP / DPF", 680),
            ("Régénération FAP", 85),
            ("Remplacement pompe à huile", 320),
            ("Remplacement pompe à eau", 180),
            ("Remplacement thermostat", 95),
        ],
    },
    {
        "famille": "Transmission",
        "icone": "🔩",
        "prestations": [
            ("Remplacement embrayage (kit complet)", 520),
            ("Remplacement embrayage + volant moteur", 780),
            ("Remplacement boîte de vitesses manuelle", 950),
            ("Révision boîte automatique", 680),
            ("Vidange boîte de vitesses manuelle", 65),
            ("Vidange boîte automatique", 95),
            ("Remplacement transmission avant gauche", 280),
            ("Remplacement transmission avant droite", 280),
            ("Remplacement soufflet de transmission", 95),
            ("Remplacement joint homocinétique", 120),
            ("Remplacement cardans (unité)", 180),
        ],
    },
    {
        "famille": "Suspension & Direction",
        "icone": "🚗",
        "prestations": [
            ("Remplacement amortisseurs avant (paire)", 280),
            ("Remplacement amortisseurs arrière (paire)", 240),
            ("Remplacement amortisseurs 4 roues", 480),
            ("Remplacement ressorts avant (paire)", 160),
            ("Remplacement ressorts arrière (paire)", 140),
            ("Remplacement rotule de suspension", 120),
            ("Remplacement rotule de direction", 110),
            ("Remplacement triangle de suspension", 180),
            ("Remplacement biellette de barre stabilisatrice", 65),
            ("Remplacement barre stabilisatrice", 140),
            ("Remplacement silent-bloc", 85),
            ("Géométrie 2 essieux (parallélisme)", 65),
            ("Géométrie 4 roues", 95),
            ("Remplacement crémaillère de direction", 380),
            ("Remplacement pompe de direction assistée", 280),
            ("Purge direction assistée hydraulique", 45),
        ],
    },
    {
        "famille": "Pneumatiques",
        "icone": "🛞",
        "prestations": [
            ("Montage / démontage pneu (unité)", 15),
            ("Équilibrage roue (unité)", 10),
            ("Permutation pneumatiques (4 roues)", 40),
            ("Remplacement valve (unité)", 5),
            ("Réparation crevaison", 25),
            ("Montage train complet 4 pneus", 100),
        ],
    },
    {
        "famille": "Refroidissement & Climatisation",
        "icone": "❄️",
        "prestations": [
            ("Remplacement liquide de refroidissement", 55),
            ("Remplacement radiateur de refroidissement", 280),
            ("Remplacement radiateur de chauffage", 320),
            ("Remplacement moto-ventilateur", 180),
            ("Recharge climatisation (R134a)", 85),
            ("Recharge climatisation (R1234yf)", 120),
            ("Diagnostic climatisation", 45),
            ("Remplacement compresseur de climatisation", 580),
            ("Désinfection climatisation", 55),
        ],
    },
    {
        "famille": "Électricité",
        "icone": "⚡",
        "prestations": [
            ("Remplacement batterie", 95),
            ("Test batterie et alternateur", 25),
            ("Remplacement alternateur", 280),
            ("Remplacement démarreur", 220),
            ("Diagnostic électrique", 65),
            ("Remplacement faisceau électrique", 180),
            ("Remplacement capteur ABS (unité)", 95),
            ("Remplacement capteur de stationnement", 75),
            ("Remplacement calculateur moteur", 450),
            ("Programmation / codage calculateur", 85),
        ],
    },
    {
        "famille": "Échappement",
        "icone": "💨",
        "prestations": [
            ("Remplacement pot catalytique", 380),
            ("Remplacement silencieux arrière", 180),
            ("Remplacement silencieux intermédiaire", 140),
            ("Remplacement ligne d'échappement complète", 420),
            ("Remplacement sonde lambda", 120),
            ("Remplacement joint de collecteur", 85),
        ],
    },
    {
        "famille": "Carrosserie",
        "icone": "🔧",
        "prestations": [
            ("Débosselage sans peinture (PDR) — petite zone", 80),
            ("Débosselage sans peinture (PDR) — grande zone", 150),
            ("Réparation bosselure avec peinture (petite)", 250),
            ("Réparation bosselure avec peinture (grande)", 450),
            ("Remplacement aile avant", 380),
            ("Remplacement aile arrière", 420),
            ("Remplacement pare-chocs avant", 280),
            ("Remplacement pare-chocs arrière", 260),
            ("Remplacement capot", 350),
            ("Remplacement coffre / hayon", 380),
            ("Remplacement portière", 420),
            ("Remplacement rétroviseur (unité)", 95),
            ("Remplacement vitre latérale", 180),
            ("Remplacement pare-brise", 320),
            ("Calibration caméra pare-brise", 85),
            ("Polissage carrosserie (demi-véhicule)", 180),
            ("Polissage carrosserie (véhicule complet)", 320),
            ("Retouche peinture locale", 120),
            ("Mise en peinture panneau complet", 380),
            ("Traitement anti-corrosion", 95),
        ],
    },
    {
        "famille": "Peinture",
        "icone": "🎨",
        "prestations": [
            ("Peinture aile avant", 280),
            ("Peinture aile arrière", 300),
            ("Peinture portière", 260),
            ("Peinture capot", 320),
            ("Peinture coffre / hayon", 340),
            ("Peinture pare-chocs avant", 220),
            ("Peinture pare-chocs arrière", 210),
            ("Peinture toit", 380),
            ("Peinture complète véhicule", 2800),
            ("Application vernis", 120),
            ("Lustrage / polissage après peinture", 95),
        ],
    },
    {
        "famille": "Main d'œuvre",
        "icone": "👷",
        "prestations": [
            ("Main d'œuvre mécanique (1h)", 85),
            ("Main d'œuvre mécanique (2h)", 170),
            ("Main d'œuvre mécanique (3h)", 255),
            ("Main d'œuvre carrosserie (1h)", 95),
            ("Main d'œuvre carrosserie (2h)", 190),
            ("Main d'œuvre carrosserie (3h)", 285),
            ("Forfait diagnostic complet", 85),
            ("Forfait révision entretien", 65),
            ("Frais de dossier", 25),
        ],
    },
]


def seed(conn):
    """Insère le catalogue par défaut dans la base SQLite ouverte `conn`.

    Idempotent : si une famille existe déjà (même nom), elle est ignorée.
    """
    for ordre_f, fam in enumerate(CATALOGUE_DEFAUT):
        cur = conn.execute(
            "SELECT id FROM prestations_familles WHERE nom=?", (fam["famille"],)
        )
        row = cur.fetchone()
        if row:
            famille_id = row[0]
        else:
            cur = conn.execute(
                "INSERT INTO prestations_familles(nom, icone, ordre) VALUES(?,?,?)",
                (fam["famille"], fam["icone"], ordre_f),
            )
            famille_id = cur.lastrowid

        for ordre_p, (libelle, pu_ht) in enumerate(fam["prestations"]):
            existing = conn.execute(
                "SELECT id FROM prestations WHERE famille_id=? AND libelle=?",
                (famille_id, libelle),
            ).fetchone()
            if existing:
                continue
            conn.execute(
                "INSERT INTO prestations(famille_id, libelle, pu_ht, ordre) VALUES(?,?,?,?)",
                (famille_id, libelle, pu_ht, ordre_p),
            )
    conn.commit()
