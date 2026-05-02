import sqlite3
db = sqlite3.connect('/app/data/garage.db')
migrations = [
    ("factures","stripe_payment_url","TEXT"),
    ("factures","montant_ht","REAL DEFAULT 0"),
    ("interventions","montant_ht","REAL DEFAULT 0"),
    ("devis","date_echeance","TEXT"),
    ("vehicules","type_vehicule","TEXT DEFAULT 'Voiture'"),
    ("abonnements","stripe_payment_url","TEXT"),
    ("abonnements","derniere_relance","TEXT"),
]
for table,col,typ in migrations:
    existing = [c[1] for c in db.execute(f"PRAGMA table_info({table})").fetchall()]
    if col not in existing:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
        print(f"OK {table}.{col}")
    else:
        print(f"= {table}.{col}")
db.execute("UPDATE factures SET montant_ht=ROUND(total_ttc/(1+tva/100.0),2) WHERE montant_ht=0 OR montant_ht IS NULL")
db.execute("UPDATE interventions SET montant_ht=ROUND(montant_ttc/1.2,2) WHERE montant_ht=0 OR montant_ht IS NULL")
db.execute("PRAGMA journal_mode=WAL")
db.execute("PRAGMA cache_size=-65536")
db.execute("PRAGMA synchronous=NORMAL")
db.execute("PRAGMA mmap_size=268435456")
db.execute("PRAGMA temp_store=MEMORY")
db.commit(); db.close()
print("DONE")
