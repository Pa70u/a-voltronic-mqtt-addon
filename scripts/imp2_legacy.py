
import pandas as pd, sqlite3
from datetime import datetime
from pathlib import Path
db = sqlite3.connect(Path("/app/data/garage.db"))
db.row_factory = sqlite3.Row
def mn(v):
    if pd.isna(v): return 0.0
    try: return float(str(v).replace(",",".").replace(" ",""))
    except: return 0.0
def md(v):
    if pd.isna(v): return None
    try: return datetime.strptime(str(v).strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
    except: return None
df = pd.read_csv("Export des factures-2.xls", sep="	", encoding="latin1", on_bad_lines="skip")
ok=0; skip=0
for _,row in df.iterrows():
    num=str(row.get("Numero de piece",row.get("Numéro de pièce",""))).strip()
    cc=str(row.get("Code client","")).strip()
    r=db.execute("SELECT id FROM users WHERE code_client=?",(cc,)).fetchone()
    cid=r["id"] if r else None
    if not cid or not num: skip+=1; continue
    ht=mn(row.get("Total HT")); tva=mn(row.get("Total TVA")); ttc=mn(row.get("Total TTC"))
    tp=round(tva/ht*100) if ht>0 else 20.0
    df2=md(row.get("Date")); de=md(row.get("Date d’échéance",row.get("Date d echéance",None)))
    st="payee" if str(row.get("Reglée",row.get("Réglée",""))).strip().lower()=="oui" else "impayee"
    try:
        db.execute("INSERT OR IGNORE INTO factures(numero,client_id,total_ht,tva,total_ttc,statut,date_echeance,date_facture,created_at) VALUES(?,?,?,?,?,?,?,?,?)",(num,cid,ht,tp,ttc,st,de,df2,df2 or datetime.now().strftime("%Y-%m-%d")))
        ok+=1
    except: skip+=1
db.commit(); db.close()
print(f"OK: {ok} | Skip: {skip}")
