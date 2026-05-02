-- ─────────────────────────────────────────────────────────────────────────
-- GarageOS — Schéma SQLite v5
-- Versionner toute évolution. Ce fichier est canonique pour les tests
-- et le bootstrap d'une nouvelle base.
-- ─────────────────────────────────────────────────────────────────────────

-- ── Comptes (admin + clients) ───────────────────────────────────────────
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
    code_client TEXT,
    -- Préférences relances (factures + CT)
    pref_relance_email INTEGER DEFAULT 1,
    pref_relance_sms INTEGER DEFAULT 1
);

-- ── Parking ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS emplacements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT UNIQUE,
    statut TEXT DEFAULT 'libre',           -- libre | occupe | reserve | hors_service
    etage INTEGER DEFAULT 0,
    prix_mensuel REAL DEFAULT 80.0,
    prix_journalier REAL DEFAULT 5.0
);

CREATE TABLE IF NOT EXISTS abonnements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    emplacement_id INTEGER NOT NULL REFERENCES emplacements(id),
    date_debut TEXT NOT NULL,
    date_fin TEXT,                         -- NULL = abonnement ouvert
    date_engagement_fin TEXT,              -- 6 mois minimum (jalon 5)
    montant REAL NOT NULL,
    statut TEXT DEFAULT 'actif',           -- actif | termine | resilie | impaye
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    stripe_payment_url TEXT,
    derniere_relance TEXT
);
CREATE INDEX IF NOT EXISTS idx_abonnements_client ON abonnements(client_id);
CREATE INDEX IF NOT EXISTS idx_abonnements_emplacement ON abonnements(emplacement_id);
CREATE INDEX IF NOT EXISTS idx_abonnements_statut ON abonnements(statut);

-- ── Véhicules ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS vehicules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    immatriculation TEXT,
    marque TEXT,
    modele TEXT,
    annee INTEGER,
    kilometrage INTEGER,
    kilometrage_date TEXT,                 -- date du dernier relevé km
    vin TEXT,
    type_vehicule TEXT DEFAULT 'Voiture',
    -- Contrôle technique
    date_dernier_ct TEXT,
    date_prochain_ct TEXT,                 -- pour les relances J-60 / J-30 / J-7
    derniere_relance_ct TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_vehicules_client ON vehicules(client_id);
CREATE INDEX IF NOT EXISTS idx_vehicules_ct ON vehicules(date_prochain_ct);

-- ── Interventions ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS interventions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicule_id INTEGER REFERENCES vehicules(id) ON DELETE SET NULL,
    client_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date_entree TEXT,
    description TEXT,
    statut TEXT DEFAULT 'en_cours',        -- en_cours | termine | facture
    montant_ht REAL DEFAULT 0,
    montant_ttc REAL DEFAULT 0,
    technicien TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_interventions_client ON interventions(client_id);
CREATE INDEX IF NOT EXISTS idx_interventions_statut ON interventions(statut);

-- ── Devis ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS devis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT UNIQUE NOT NULL,
    client_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vehicule_id INTEGER REFERENCES vehicules(id) ON DELETE SET NULL,
    lignes TEXT,                           -- JSON: [{desc, qte, pu_ht, total_ht}]
    total_ht REAL DEFAULT 0,
    tva REAL DEFAULT 20.0,
    total_ttc REAL DEFAULT 0,
    statut TEXT DEFAULT 'brouillon',       -- brouillon | envoye | accepte | refuse | facture | archive
    notes TEXT,
    validite INTEGER DEFAULT 30,
    date_echeance TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_devis_client ON devis(client_id);

-- ── Factures ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS factures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT UNIQUE NOT NULL,
    devis_id INTEGER REFERENCES devis(id) ON DELETE SET NULL,
    client_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vehicule_id INTEGER REFERENCES vehicules(id) ON DELETE SET NULL,
    lignes TEXT,
    total_ht REAL DEFAULT 0,
    tva REAL DEFAULT 20.0,
    total_ttc REAL DEFAULT 0,
    statut TEXT DEFAULT 'impayee',         -- impayee | payee | annulee
    notes TEXT,
    date_facture TEXT,
    date_echeance TEXT,
    methode_reglement TEXT,
    date_reglement TEXT,
    reference TEXT,
    stripe_payment_url TEXT,
    derniere_relance TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_factures_client ON factures(client_id);
CREATE INDEX IF NOT EXISTS idx_factures_statut ON factures(statut);

-- ── Paiements ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS paiements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    facture_id INTEGER REFERENCES factures(id) ON DELETE SET NULL,
    type TEXT,                             -- facture | abonnement
    montant REAL,
    methode TEXT,                          -- cb | virement | especes | cheque
    statut TEXT DEFAULT 'en_attente',      -- en_attente | paye | echoue
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ── Sessions ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tokens (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_tokens_user ON tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_tokens_expires ON tokens(expires_at);

-- ── Configuration garage (clé/valeur) ───────────────────────────────────
CREATE TABLE IF NOT EXISTS config_garage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cle TEXT UNIQUE NOT NULL,
    valeur TEXT
);

-- ── Catalogue prestations (NOUVEAU jalon 2) ─────────────────────────────
CREATE TABLE IF NOT EXISTS prestations_familles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT UNIQUE NOT NULL,
    icone TEXT,                            -- emoji ou classe css
    ordre INTEGER DEFAULT 0,
    actif INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS prestations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    famille_id INTEGER NOT NULL REFERENCES prestations_familles(id) ON DELETE CASCADE,
    libelle TEXT NOT NULL,
    pu_ht REAL DEFAULT 0,
    duree_min INTEGER DEFAULT 0,           -- minutes (pour planification future)
    actif INTEGER DEFAULT 1,
    ordre INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_prestations_famille ON prestations(famille_id);

-- ── Journal des relances (audit) ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS relances_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cible_type TEXT NOT NULL,              -- facture | abonnement | ct
    cible_id INTEGER NOT NULL,
    canal TEXT NOT NULL,                   -- email | sms
    destinataire TEXT,
    statut TEXT NOT NULL,                  -- envoye | echec
    erreur TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_relances_cible ON relances_log(cible_type, cible_id);

-- ── Version du schéma ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT DEFAULT CURRENT_TIMESTAMP
);
INSERT OR IGNORE INTO schema_version(version) VALUES (5);
