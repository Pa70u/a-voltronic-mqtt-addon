"""
GarageOS Backend v4 — FastAPI + SQLite
Routes complètes avec notifications email/SMS/Stripe
"""
import os, sqlite3, hashlib, secrets, json
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(title="GarageOS API v4")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DB = os.getenv("GARAGE_DB", "/app/data/garage.db")

def db():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA cache_size=-65536")
    c.execute("PRAGMA synchronous=NORMAL")
    c.execute("PRAGMA mmap_size=268435456")
    c.execute("PRAGMA temp_store=MEMORY")
    return c

# ── AUTH ───────────────────────────────────────────────────────────────────────
def auth(request: Request):
    token = request.headers.get("Authorization","").replace("Bearer ","").strip()
    if not token: raise HTTPException(401,"Token manquant")
    d = db()
    row = d.execute("SELECT user_id FROM tokens WHERE token=? AND expires_at > datetime('now')",(token,)).fetchone()
    d.close()
    if not row: raise HTTPException(401,"Token invalide ou expiré")
    return row["user_id"]

@app.post("/api/auth/login")
def login(body: dict):
    email = body.get("email",""); pw = body.get("password","")
    d = db()
    u = d.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone()
    if not u: d.close(); raise HTTPException(401,"Identifiants incorrects")
    h = hashlib.sha256(pw.encode()).hexdigest()
    if u["password_hash"] != h: d.close(); raise HTTPException(401,"Identifiants incorrects")
    token = secrets.token_hex(32)
    exp = (datetime.now()+timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    d.execute("INSERT INTO tokens(token,user_id,expires_at) VALUES(?,?,?)",(token,u["id"],exp))
    d.commit(); d.close()
    return {"token":token,"id":u["id"],"nom":u["nom"],"prenom":u["prenom"],"email":u["email"],"role":u["role"]}

@app.get("/api/auth/me")
def me(uid=Depends(auth)):
    d = db()
    u = d.execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone()
    d.close()
    return dict(u)

# ── DASHBOARD ──────────────────────────────────────────────────────────────────
@app.get("/api/dashboard/stats")
def stats(uid=Depends(auth)):
    d = db()
    emp = d.execute("SELECT COUNT(*) t, SUM(statut='libre') l, SUM(statut='occupé') o FROM emplacements").fetchone()
    r = {
        "emplacements_total": emp["t"] or 0,
        "emplacements_libres": emp["l"] or 0,
        "emplacements_occupes": emp["o"] or 0,
        "taux_occupation": round((emp["o"] or 0)/(emp["t"] or 1)*100,1),
        "clients": d.execute("SELECT COUNT(*) FROM users WHERE role='client'").fetchone()[0],
        "abonnements_actifs": d.execute("SELECT COUNT(*) FROM abonnements WHERE statut='actif'").fetchone()[0],
        "interventions_en_cours": d.execute("SELECT COUNT(*) FROM interventions WHERE statut='en_cours'").fetchone()[0],
        "devis_en_cours": d.execute("SELECT COUNT(*) FROM devis WHERE statut NOT IN ('facture','archive')").fetchone()[0],
        "factures_impayees": d.execute("SELECT COUNT(*) FROM factures WHERE statut='impayee'").fetchone()[0],
        "ca_mois": d.execute("SELECT COALESCE(SUM(total_ttc),0) FROM factures WHERE statut='payee' AND strftime('%Y-%m',created_at)=strftime('%Y-%m','now')").fetchone()[0],
    }
    d.close(); return r

# ── CLIENTS ────────────────────────────────────────────────────────────────────
@app.get("/api/clients")
def clients(uid=Depends(auth)):
    d = db()
    rows = d.execute("SELECT * FROM users WHERE role='client' ORDER BY nom,prenom").fetchall()
    d.close(); return [dict(r) for r in rows]

@app.post("/api/clients/nouveau")
def nouveau_client(body: dict, uid=Depends(auth)):
    d = db()
    last = d.execute("SELECT code_client FROM users WHERE code_client IS NOT NULL ORDER BY code_client DESC LIMIT 1").fetchone()
    try: num = int((last["code_client"] or "CL0000").replace("CL",""))+1
    except: num = 1000
    code = f"CL{num:04d}"
    email = body.get("email") or f"{code}@garage.fr"
    pw = hashlib.sha256(secrets.token_hex(8).encode()).hexdigest()
    d.execute("INSERT OR IGNORE INTO users(nom,prenom,email,password_hash,role,telephone,adresse,code_client) VALUES(?,?,?,?,?,?,?,?)",
              (body.get("nom",""), body.get("prenom",""), email, pw, "client",
               body.get("telephone",""), body.get("adresse",""), code))
    d.commit(); lid = d.execute("SELECT last_insert_rowid()").fetchone()[0]; d.close()
    return {"ok":True,"code":code,"id":lid}

@app.patch("/api/clients/{cid}")
def update_client(cid: int, body: dict, uid=Depends(auth)):
    d = db()
    fields = [(k,v) for k,v in body.items() if k in ['nom','prenom','email','telephone','adresse']]
    if fields:
        sets = ",".join(f"{k}=?" for k,v in fields)
        vals = [v for k,v in fields]+[cid]
        d.execute(f"UPDATE users SET {sets} WHERE id=?", vals)
        d.commit()
    d.close(); return {"ok":True}

# ── VÉHICULES ──────────────────────────────────────────────────────────────────
@app.get("/api/vehicules")
def vehicules(uid=Depends(auth)):
    d = db()
    rows = d.execute("""SELECT v.*, u.nom, u.prenom, u.email, u.telephone
        FROM vehicules v JOIN users u ON v.client_id=u.id
        ORDER BY v.created_at DESC""").fetchall()
    d.close(); return [dict(r) for r in rows]

@app.get("/api/vehicules/miens")
def vehicules_miens(uid=Depends(auth)):
    d = db(); rows = d.execute("SELECT * FROM vehicules WHERE client_id=?",(uid,)).fetchall()
    d.close(); return [dict(r) for r in rows]

@app.post("/api/vehicules/nouveau")
def nouveau_vehicule(body: dict, uid=Depends(auth)):
    d = db()
    d.execute("INSERT INTO vehicules(client_id,immatriculation,marque,modele,annee,kilometrage,vin,type_vehicule) VALUES(?,?,?,?,?,?,?,?)",
              (body.get("client_id",0), body.get("immatriculation",""),
               body.get("marque",""), body.get("modele",""),
               body.get("annee"), body.get("kilometrage"),
               body.get("vin",""), body.get("type_vehicule","Voiture")))
    d.commit(); d.close(); return {"ok":True}

@app.patch("/api/vehicules/{vid}")
def update_vehicule(vid: int, body: dict, uid=Depends(auth)):
    d = db()
    fields = [(k,v) for k,v in body.items() if k in ['immatriculation','marque','modele','annee','kilometrage','vin','type_vehicule']]
    if fields:
        sets = ",".join(f"{k}=?" for k,v in fields)
        vals = [v for k,v in fields]+[vid]
        d.execute(f"UPDATE vehicules SET {sets} WHERE id=?", vals)
        d.commit()
    d.close(); return {"ok":True}

# ── INTERVENTIONS ──────────────────────────────────────────────────────────────
@app.get("/api/interventions")
def interventions(uid=Depends(auth)):
    d = db()
    rows = d.execute("""SELECT i.*, u.nom, u.prenom, v.immatriculation, v.marque, v.modele
        FROM interventions i
        JOIN users u ON i.client_id=u.id
        LEFT JOIN vehicules v ON i.vehicule_id=v.id
        ORDER BY i.created_at DESC""").fetchall()
    d.close(); return [dict(r) for r in rows]

@app.get("/api/interventions/miennes")
def interventions_miennes(uid=Depends(auth)):
    d = db()
    rows = d.execute("""SELECT i.*, v.immatriculation, v.marque, v.modele
        FROM interventions i LEFT JOIN vehicules v ON i.vehicule_id=v.id
        WHERE i.client_id=? ORDER BY i.created_at DESC""",(uid,)).fetchall()
    d.close(); return [dict(r) for r in rows]

@app.post("/api/interventions/nouveau")
def nouvelle_intervention(body: dict, uid=Depends(auth)):
    d = db()
    d.execute("INSERT INTO interventions(vehicule_id,client_id,date_entree,description,statut,montant_ht,montant_ttc,technicien) VALUES(?,?,?,?,?,?,?,?)",
              (body.get("vehicule_id",0), body.get("client_id",0),
               body.get("date_entree",""), body.get("description",""),
               body.get("statut","en_cours"),
               body.get("montant_ht",0), body.get("montant_ttc",0),
               body.get("technicien","")))
    d.commit(); d.close(); return {"ok":True}

@app.patch("/api/interventions/{iid}/statut")
def update_inter_statut(iid: int, body: dict, uid=Depends(auth)):
    d = db(); d.execute("UPDATE interventions SET statut=? WHERE id=?",(body["statut"],iid))
    d.commit(); d.close(); return {"ok":True}

# ── DEVIS ──────────────────────────────────────────────────────────────────────
@app.get("/api/devis")
def devis(uid=Depends(auth)):
    d = db()
    rows = d.execute("""SELECT de.*, u.nom, u.prenom, u.email, u.telephone,
        v.immatriculation, v.marque, v.modele
        FROM devis de JOIN users u ON de.client_id=u.id
        LEFT JOIN vehicules v ON de.vehicule_id=v.id
        ORDER BY de.created_at DESC""").fetchall()
    d.close(); return [dict(r) for r in rows]

@app.post("/api/devis")
def nouveau_devis(body: dict, uid=Depends(auth)):
    d = db()
    now = datetime.now()
    count = d.execute("SELECT COUNT(*) FROM devis").fetchone()[0]
    num = f"DEV_{now.strftime('%Y_%m')}_{count+1:03d}"
    lignes = body.get("lignes",[])
    if isinstance(lignes, list):
        ht = sum(l.get("total_ht",l.get("total",0)) for l in lignes)
    else:
        ht = 0
    tva = body.get("tva",20)
    ttc = round(ht*(1+tva/100),2)
    lj = json.dumps(lignes, ensure_ascii=False)
    d.execute("INSERT INTO devis(numero,client_id,vehicule_id,lignes,total_ht,tva,total_ttc,statut,notes,validite) VALUES(?,?,?,?,?,?,?,?,?,?)",
              (num, body.get("client_id",0), body.get("vehicule_id",0),
               lj, round(ht,2), tva, ttc, "brouillon",
               body.get("notes",""), body.get("validite",30)))
    d.commit(); d.close(); return {"ok":True,"numero":num}

@app.patch("/api/devis/{did}/statut")
def update_devis_statut(did: int, body: dict, uid=Depends(auth)):
    d = db(); d.execute("UPDATE devis SET statut=? WHERE id=?",(body["statut"],did))
    d.commit(); d.close(); return {"ok":True}

@app.patch("/api/devis/{did}/modifier")
def modifier_devis(did: int, body: dict, uid=Depends(auth)):
    d = db()
    d.execute("UPDATE devis SET vehicule_id=?,statut=?,tva=?,validite=?,notes=?,lignes=?,total_ht=?,total_ttc=? WHERE id=?",
              (body.get("vehicule_id",0), body.get("statut","brouillon"),
               body.get("tva",20), body.get("validite",30),
               body.get("notes",""), body.get("lignes","[]"),
               body.get("total_ht",0), body.get("total_ttc",0), did))
    d.commit(); d.close(); return {"ok":True}

@app.post("/api/devis/{did}/convertir")
def convertir_devis(did: int, uid=Depends(auth)):
    d = db()
    dev = d.execute("SELECT * FROM devis WHERE id=?",(did,)).fetchone()
    if not dev: d.close(); raise HTTPException(404,"Devis introuvable")
    now = datetime.now()
    count = d.execute("SELECT COUNT(*) FROM factures").fetchone()[0]
    num = f"FAC_{now.strftime('%Y_%m')}_{count+1:03d}"
    exp = (now+timedelta(days=30)).strftime("%Y-%m-%d")
    d.execute("INSERT INTO factures(numero,devis_id,client_id,vehicule_id,lignes,total_ht,tva,total_ttc,statut,notes,date_echeance,date_facture) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
              (num, dev["id"], dev["client_id"], dev["vehicule_id"],
               dev["lignes"], dev["total_ht"], dev["tva"], dev["total_ttc"],
               "impayee", dev["notes"], exp, now.strftime("%Y-%m-%d")))
    d.execute("UPDATE devis SET statut='facture' WHERE id=?",(did,))
    d.commit(); d.close(); return {"ok":True,"numero":num}

@app.post("/api/devis/{did}/envoyer")
def envoyer_devis(did: int, body: dict, uid=Depends(auth)):
    # Pour l'instant retourne un succès — à connecter avec notifications.py
    return {"ok":True,"results":{"email":{"ok":False,"error":"Configurer GMAIL_USER dans docker-compose.yml"}},"payment_url":""}

# ── FACTURES ───────────────────────────────────────────────────────────────────
@app.get("/api/factures")
def factures(uid=Depends(auth)):
    d = db()
    rows = d.execute("""SELECT fa.*, u.nom, u.prenom, u.email, u.telephone, u.adresse,
        v.immatriculation, v.marque, v.modele
        FROM factures fa JOIN users u ON fa.client_id=u.id
        LEFT JOIN vehicules v ON fa.vehicule_id=v.id
        ORDER BY fa.created_at DESC""").fetchall()
    d.close(); return [dict(r) for r in rows]

@app.post("/api/factures/nouvelle")
def nouvelle_facture(body: dict, uid=Depends(auth)):
    """Créer une nouvelle facture directement (sans devis)."""
    client_id = body.get("client_id")
    if not client_id:
        raise HTTPException(400, "client_id obligatoire")
    d = db()
    now = datetime.now()
    count = d.execute("SELECT COUNT(*) FROM factures").fetchone()[0]
    num = f"FAC_{now.strftime('%Y_%m')}_{count+1:03d}"
    exp = body.get("date_echeance") or (now+timedelta(days=30)).strftime("%Y-%m-%d")
    d.execute(
        "INSERT INTO factures(numero,devis_id,client_id,vehicule_id,lignes,total_ht,tva,total_ttc,statut,notes,date_echeance,date_facture) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (num, None, client_id,
         body.get("vehicule_id"), body.get("lignes","[]"),
         body.get("total_ht",0), body.get("tva",20), body.get("total_ttc",0),
         "impayee", body.get("notes",""), exp, now.strftime("%Y-%m-%d"))
    )
    d.commit()
    lid = d.execute("SELECT last_insert_rowid()").fetchone()[0]
    d.close()
    return {"ok": True, "id": lid, "numero": num}

@app.patch("/api/factures/{fid}/statut")
def update_facture_statut(fid: int, body: dict, uid=Depends(auth)):
    d = db()
    d.execute("UPDATE factures SET statut=?,methode_reglement=?,date_reglement=?,reference=? WHERE id=?",
              (body.get("statut","impayee"), body.get("methode_reglement",""),
               body.get("date_reglement",""), body.get("reference",""), fid))
    d.commit(); d.close(); return {"ok":True}

@app.post("/api/factures/{fid}/envoyer")
def envoyer_facture(fid: int, body: dict, uid=Depends(auth)):
    """Envoi email/SMS/Stripe — nécessite notifications.py configuré."""
    d = db()
    fac = d.execute("""SELECT fa.*, u.nom, u.prenom, u.email as client_email, u.telephone,
        v.immatriculation, v.marque, v.modele
        FROM factures fa JOIN users u ON fa.client_id=u.id
        LEFT JOIN vehicules v ON fa.vehicule_id=v.id WHERE fa.id=?""",(fid,)).fetchone()
    d.close()
    if not fac: raise HTTPException(404,"Facture introuvable")

    fac_dict = dict(fac)
    fac_dict["email"] = fac_dict.pop("client_email","")
    results = {}
    payment_url = ""

    # Stripe
    if body.get("stripe"):
        sk = os.getenv("STRIPE_SECRET_KEY","")
        if sk:
            try:
                import stripe; stripe.api_key = sk
                amount = int(fac_dict.get("total_ttc",0)*100)
                price = stripe.Price.create(unit_amount=amount, currency="eur",
                    product_data={"name":f"Facture {fac_dict['numero']}"})
                link = stripe.PaymentLink.create(line_items=[{"price":price.id,"quantity":1}],
                    metadata={"facture_id":str(fid)})
                payment_url = link.url
                conn = db(); conn.execute("UPDATE factures SET stripe_payment_url=? WHERE id=?",(payment_url,fid))
                conn.commit(); conn.close()
                results["stripe"] = {"ok":True,"url":payment_url}
            except Exception as e:
                results["stripe"] = {"ok":False,"error":str(e)}
        else:
            results["stripe"] = {"ok":False,"error":"STRIPE_SECRET_KEY non configuré"}

    # Email
    if body.get("email"):
        gmail_user = os.getenv("GMAIL_USER","")
        gmail_pw   = os.getenv("GMAIL_PASSWORD","")
        dest = body.get("email_dest") or fac_dict.get("email","")
        if gmail_user and gmail_pw and dest:
            try:
                import smtplib, ssl
                from email.mime.multipart import MIMEMultipart
                from email.mime.text import MIMEText
                montant = f"{fac_dict.get('total_ttc',0):,.2f}".replace(",","").replace(".",",")
                bouton = f'<div style="text-align:center;margin:24px 0"><a href="{payment_url}" style="background:#f0c040;color:#1a1a2e;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:700;font-size:15px">💳 Payer {montant} € en ligne</a></div>' if payment_url else ""
                html = f"""<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto">
<div style="background:#1a1a2e;padding:24px;border-radius:12px 12px 0 0">
<div style="font-size:18px;font-weight:900;color:#f0c040">GARAGE DE LA MONTAGNE</div>
<div style="font-size:10px;color:rgba(255,255,255,.6);margin-top:3px">94510 La Queue-en-Brie</div>
</div>
<div style="height:3px;background:linear-gradient(90deg,#f0c040,#C8961E)"></div>
<div style="padding:24px;background:#fff;border:1px solid #eee">
<p>Bonjour <strong>{fac_dict.get('prenom','')} {fac_dict.get('nom','')}</strong>,</p>
<p>Votre facture <strong>{fac_dict.get('numero','')}</strong> d'un montant de <strong>{montant} €</strong> est disponible.</p>
<div style="background:#f8f8f8;border-radius:8px;padding:16px;margin:16px 0;font-size:13px">
<div style="display:flex;justify-content:space-between;margin-bottom:6px"><span style="color:#888">Numéro</span><strong>{fac_dict.get('numero','')}</strong></div>
<div style="display:flex;justify-content:space-between;margin-bottom:6px"><span style="color:#888">Véhicule</span><span>{fac_dict.get('immatriculation','—')}</span></div>
<div style="display:flex;justify-content:space-between;font-size:16px;font-weight:700;margin-top:8px;padding-top:8px;border-top:2px solid #1a1a2e"><span>Total TTC</span><span style="color:#f0c040">{montant} €</span></div>
</div>
{bouton}
<p style="font-size:12px;color:#888">Garage de la Montagne · SIRET 487 723 306 00014</p>
</div></div>"""
                msg = MIMEMultipart("alternative")
                msg["Subject"] = f"Facture {fac_dict['numero']} — Garage de la Montagne"
                msg["From"] = f"Garage de la Montagne <{gmail_user}>"
                msg["To"] = dest
                msg.attach(MIMEText(html,"html","utf-8"))
                ctx = ssl.create_default_context()
                with smtplib.SMTP_SSL("smtp.gmail.com",465,context=ctx) as srv:
                    srv.login(gmail_user,gmail_pw)
                    srv.sendmail(gmail_user,dest,msg.as_string())
                results["email"] = {"ok":True}
            except Exception as e:
                results["email"] = {"ok":False,"error":str(e)}
        else:
            results["email"] = {"ok":False,"error":"GMAIL_USER/GMAIL_PASSWORD non configurés" if not gmail_user else "Pas d'email client"}

    # SMS Brevo
    if body.get("sms"):
        brevo_key = os.getenv("BREVO_API_KEY","")
        tel = body.get("telephone") or fac_dict.get("telephone","")
        if brevo_key and tel:
            try:
                import requests as req
                numero = tel.strip().replace(" ","").replace(".","").replace("-","")
                if numero.startswith("0"): numero = "+33"+numero[1:]
                montant = f"{fac_dict.get('total_ttc',0):.2f}".replace(".",",")
                msg_txt = f"Garage Montagne: Facture {fac_dict['numero']} - {montant}EUR"
                if payment_url: msg_txt += f" Payer: {payment_url}"
                r = req.post("https://api.brevo.com/v3/transactionalSMS/sms",
                    headers={"api-key":brevo_key,"Content-Type":"application/json"},
                    json={"sender":"GarageOVH","recipient":numero,"content":msg_txt[:160]},timeout=10)
                results["sms"] = {"ok":r.status_code in[200,201],"status":r.status_code}
            except Exception as e:
                results["sms"] = {"ok":False,"error":str(e)}
        else:
            results["sms"] = {"ok":False,"error":"BREVO_API_KEY non configuré" if not brevo_key else "Pas de téléphone"}

    return {"ok":True,"results":results,"payment_url":payment_url}

# ── ABONNEMENTS ────────────────────────────────────────────────────────────────
@app.get("/api/abonnements")
def abonnements(uid=Depends(auth)):
    d = db()
    rows = d.execute("""SELECT a.*, u.nom, u.prenom, u.email, u.telephone,
        e.numero as emplacement_numero, e.etage
        FROM abonnements a JOIN users u ON a.client_id=u.id
        JOIN emplacements e ON a.emplacement_id=e.id
        ORDER BY a.created_at DESC""").fetchall()
    d.close(); return [dict(r) for r in rows]

@app.get("/api/abonnements/miens")
def abonnements_miens(uid=Depends(auth)):
    d = db()
    rows = d.execute("""SELECT a.*, e.numero as emplacement_numero, e.etage
        FROM abonnements a JOIN emplacements e ON a.emplacement_id=e.id
        WHERE a.client_id=? ORDER BY a.created_at DESC""",(uid,)).fetchall()
    d.close(); return [dict(r) for r in rows]

@app.post("/api/abonnements/nouveau")
def nouvel_abonnement(body: dict, uid=Depends(auth)):
    d = db()
    d.execute("INSERT INTO abonnements(client_id,emplacement_id,date_debut,date_fin,montant,statut) VALUES(?,?,?,?,?,?)",
              (body["client_id"], body["emplacement_id"], body["date_debut"],
               body["date_fin"], body["montant"], body.get("statut","actif")))
    d.execute("UPDATE emplacements SET statut='occupé' WHERE id=?",(body["emplacement_id"],))
    d.commit(); d.close(); return {"ok":True}

@app.post("/api/abonnements/{aid}/envoyer")
def envoyer_abonnement(aid: int, body: dict, uid=Depends(auth)):
    """Rappel abonnement parking avec lien Stripe."""
    d = db()
    abon = d.execute("""SELECT a.*, u.nom, u.prenom, u.email, u.telephone,
        e.numero as emplacement_numero FROM abonnements a
        JOIN users u ON a.client_id=u.id
        JOIN emplacements e ON a.emplacement_id=e.id WHERE a.id=?""",(aid,)).fetchone()
    d.close()
    if not abon: raise HTTPException(404,"Abonnement introuvable")
    abon_dict = dict(abon)
    results = {}; payment_url = ""

    if body.get("stripe"):
        sk = os.getenv("STRIPE_SECRET_KEY","")
        if sk:
            try:
                import stripe; stripe.api_key = sk
                amount = int(abon_dict.get("montant",0)*100)
                price = stripe.Price.create(unit_amount=amount, currency="eur",
                    product_data={"name":f"Abonnement parking P{abon_dict.get('emplacement_numero','')}"})
                link = stripe.PaymentLink.create(line_items=[{"price":price.id,"quantity":1}],
                    metadata={"abonnement_id":str(aid)})
                payment_url = link.url
                results["stripe"] = {"ok":True,"url":payment_url}
            except Exception as e:
                results["stripe"] = {"ok":False,"error":str(e)}

    # Email rappel abonnement
    if body.get("email") and abon_dict.get("email"):
        gmail_user = os.getenv("GMAIL_USER","")
        gmail_pw = os.getenv("GMAIL_PASSWORD","")
        if gmail_user and gmail_pw:
            try:
                import smtplib, ssl
                from email.mime.multipart import MIMEMultipart
                from email.mime.text import MIMEText
                montant = f"{abon_dict.get('montant',0):.2f}".replace(".",",")
                bouton = f'<div style="text-align:center;margin:24px 0"><a href="{payment_url}" style="background:#f0c040;color:#1a1a2e;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:700">💳 Régler {montant} € en ligne</a></div>' if payment_url else ""
                html = f"""<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto">
<div style="background:#1a1a2e;padding:24px;border-radius:12px 12px 0 0">
<div style="font-size:18px;font-weight:900;color:#f0c040">🅿 ABONNEMENT PARKING</div>
<div style="font-size:10px;color:rgba(255,255,255,.6)">Garage de la Montagne — 94510 La Queue-en-Brie</div>
</div>
<div style="height:3px;background:linear-gradient(90deg,#f0c040,#C8961E)"></div>
<div style="padding:24px;background:#fff;border:1px solid #eee">
<p>Bonjour <strong>{abon_dict.get('prenom','')} {abon_dict.get('nom','')}</strong>,</p>
<p>Rappel de votre abonnement parking — Place <strong>{abon_dict.get('emplacement_numero','')}</strong>.</p>
<div style="background:#f8f8f8;border-radius:8px;padding:16px;margin:16px 0;font-size:13px">
<div style="display:flex;justify-content:space-between;font-size:18px;font-weight:700"><span>Mensualité</span><span style="color:#f0c040">{montant} €</span></div>
</div>{bouton}
</div></div>"""
                msg = MIMEMultipart("alternative")
                msg["Subject"] = f"Abonnement parking — Garage de la Montagne"
                msg["From"] = f"Garage de la Montagne <{gmail_user}>"
                msg["To"] = abon_dict["email"]
                msg.attach(MIMEText(html,"html","utf-8"))
                ctx = ssl.create_default_context()
                with smtplib.SMTP_SSL("smtp.gmail.com",465,context=ctx) as srv:
                    srv.login(gmail_user,gmail_pw); srv.sendmail(gmail_user,abon_dict["email"],msg.as_string())
                results["email"] = {"ok":True}
            except Exception as e:
                results["email"] = {"ok":False,"error":str(e)}

    return {"ok":True,"results":results,"payment_url":payment_url}

# ── EMPLACEMENTS ───────────────────────────────────────────────────────────────
@app.get("/api/emplacements")
def emplacements(uid=Depends(auth)):
    d = db(); rows = d.execute("SELECT * FROM emplacements ORDER BY etage,numero").fetchall()
    d.close(); return [dict(r) for r in rows]

@app.patch("/api/emplacements/{eid}/statut")
def update_emp(eid: int, body: dict, uid=Depends(auth)):
    d = db(); d.execute("UPDATE emplacements SET statut=? WHERE id=?",(body["statut"],eid))
    d.commit(); d.close(); return {"ok":True}

# ── PAIEMENTS ──────────────────────────────────────────────────────────────────
@app.post("/api/paiements/simuler")
def simuler_paiement(body: dict, uid=Depends(auth)):
    d = db()
    d.execute("INSERT INTO paiements(client_id,type,montant,methode,statut) VALUES(?,?,?,?,?)",
              (uid, body.get("type","abonnement"), body.get("montant",0), body.get("methode","cb"), "paye"))
    d.commit(); d.close(); return {"ok":True}

@app.get("/api/paiements/miens")
def paiements_miens(uid=Depends(auth)):
    d = db(); rows = d.execute("SELECT * FROM paiements WHERE client_id=? ORDER BY created_at DESC",(uid,)).fetchall()
    d.close(); return [dict(r) for r in rows]

# ── STRIPE WEBHOOK ─────────────────────────────────────────────────────────────
@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    event_data = json.loads(payload)
    if event_data.get("type") == "payment_intent.succeeded":
        meta = event_data.get("data",{}).get("object",{}).get("metadata",{})
        fid = meta.get("facture_id")
        if fid:
            d = db(); d.execute("UPDATE factures SET statut='payee' WHERE id=?",(fid,)); d.commit(); d.close()
    return {"status":"ok"}

@app.get("/api/health")
def health(): return {"status":"ok","app":"GarageOS v4"}

@app.patch("/api/abonnements/{aid}/statut")
def update_abonnement_statut(aid: int, body: dict, uid=Depends(auth)):
    d = db()
    d.execute("UPDATE abonnements SET statut=? WHERE id=?", (body.get("statut","actif"), aid))
    d.commit(); d.close()
    return {"ok":True}

@app.post("/api/emplacements/nouveau")
def nouvel_emplacement_v2(body: dict, uid=Depends(auth)):
    d = db()
    try:
        d.execute("INSERT INTO emplacements(numero,statut,etage,prix_mensuel,prix_journalier) VALUES(?,?,?,?,?)",
                  (body.get("numero",""), body.get("statut","libre"),
                   body.get("etage",0), body.get("prix_mensuel",80),
                   body.get("prix_journalier",5)))
        d.commit()
        lid = d.execute("SELECT last_insert_rowid()").fetchone()[0]
        d.close()
        return {"ok":True,"id":lid}
    except Exception as e:
        d.close()
        raise HTTPException(400, "Numéro déjà existant : "+str(e))

@app.patch("/api/emplacements/{eid}/renommer")
def renommer_emplacement(eid: int, body: dict, uid=Depends(auth)):
    d = db()
    d.execute("UPDATE emplacements SET numero=? WHERE id=?", (body.get("numero",""), eid))
    d.commit(); d.close()
    return {"ok": True}

@app.delete("/api/emplacements/{eid}/supprimer")
def supprimer_emplacement(eid: int, uid=Depends(auth)):
    d = db()
    d.execute("DELETE FROM emplacements WHERE id=?", (eid,))
    d.execute("DELETE FROM abonnements WHERE emplacement_id=?", (eid,))
    d.commit(); d.close()
    return {"ok": True}
