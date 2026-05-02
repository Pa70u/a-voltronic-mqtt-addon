-- ─────────────────────────────────────────────────────────────────────────
-- GarageOS — Schéma SQLite (état actuel reproduit pour tests + init)
-- À versionner lors des évolutions (jalon 2+).
-- ─────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT,
    prenom TEXT,
    email TEXT UNIQUE,
    password_hash TEXT,
    role TEXT DEFAULT 'client',
    telephone TEXT,
    adresse TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    code_client TEXT
);

CREATE TABLE IF NOT EXISTS emplacements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT UNIQUE,
    statut TEXT DEFAULT 'libre',
    etage INTEGER DEFAULT 0,
    prix_mensuel REAL DEFAULT 80.0,
    prix_journalier REAL DEFAULT 5.0
);

CREATE TABLE IF NOT EXISTS abonnements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER,
    emplacement_id INTEGER,
    date_debut TEXT,
    date_fin TEXT,
    montant REAL,
    statut TEXT DEFAULT 'actif',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    stripe_payment_url TEXT,
    derniere_relance TEXT
);

CREATE TABLE IF NOT EXISTS vehicules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER,
    immatriculation TEXT,
    marque TEXT,
    modele TEXT,
    annee INTEGER,
    kilometrage INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    vin TEXT,
    type_vehicule TEXT DEFAULT 'Voiture'
);

CREATE TABLE IF NOT EXISTS interventions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicule_id INTEGER,
    client_id INTEGER,
    date_entree TEXT,
    description TEXT,
    statut TEXT DEFAULT 'en_cours',
    montant_ttc REAL DEFAULT 0,
    technicien TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    montant_ht REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS devis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT UNIQUE,
    client_id INTEGER,
    vehicule_id INTEGER,
    lignes TEXT,
    total_ht REAL,
    tva REAL DEFAULT 20.0,
    total_ttc REAL,
    statut TEXT DEFAULT 'brouillon',
    notes TEXT,
    validite INTEGER DEFAULT 30,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    date_echeance TEXT
);

CREATE TABLE IF NOT EXISTS factures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT UNIQUE,
    devis_id INTEGER,
    client_id INTEGER,
    vehicule_id INTEGER,
    lignes TEXT,
    total_ht REAL,
    tva REAL DEFAULT 20.0,
    total_ttc REAL,
    statut TEXT DEFAULT 'impayee',
    notes TEXT,
    date_echeance TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    date_facture TEXT,
    methode_reglement TEXT,
    date_reglement TEXT,
    reference TEXT,
    stripe_payment_url TEXT,
    montant_ht REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS paiements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER,
    facture_id INTEGER,
    type TEXT,
    montant REAL,
    methode TEXT,
    statut TEXT DEFAULT 'en_attente',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tokens (
    token TEXT PRIMARY KEY,
    user_id INTEGER,
    expires_at TEXT
);

CREATE TABLE IF NOT EXISTS config_garage (
    id INTEGER PRIMARY KEY,
    cle TEXT UNIQUE,
    valeur TEXT
);
