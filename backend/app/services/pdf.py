"""Génération PDF factures + devis (reportlab).

Mentions légales lues depuis la table `config_garage` (cle/valeur).
"""
from __future__ import annotations

import json
import sqlite3
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Palette light/bleu (cohérente avec l'admin v5)
NAVY = colors.HexColor("#1e3a8a")
BLUE = colors.HexColor("#2563eb")
GRAY_LIGHT = colors.HexColor("#f3f4f6")
GRAY_BORDER = colors.HexColor("#e5e7eb")
GRAY_TEXT = colors.HexColor("#6b7280")
BLACK = colors.HexColor("#111827")


def get_garage_config(conn: sqlite3.Connection) -> dict[str, str]:
    rows = conn.execute("SELECT cle, valeur FROM config_garage").fetchall()
    return {r["cle"] if hasattr(r, "keys") else r[0]:
            r["valeur"] if hasattr(r, "keys") else r[1] for r in rows}


def _fmt_money(v: float | int | None) -> str:
    return f"{(v or 0):,.2f}".replace(",", " ").replace(".", ",") + " €"


def _styles():
    base = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle(
            "h1", parent=base["Heading1"], fontName="Helvetica-Bold",
            fontSize=20, textColor=NAVY, spaceAfter=2,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=11, textColor=NAVY, spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "small", parent=base["BodyText"], fontName="Helvetica",
            fontSize=8, textColor=GRAY_TEXT, leading=10,
        ),
        "body": ParagraphStyle(
            "body", parent=base["BodyText"], fontName="Helvetica",
            fontSize=10, textColor=BLACK, leading=13,
        ),
        "bodyB": ParagraphStyle(
            "bodyB", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=10, textColor=BLACK, leading=13,
        ),
    }


def _header_block(cfg: dict[str, str], styles) -> Table:
    left = [
        Paragraph(f"<b>{cfg.get('nom','GARAGE')}</b>", styles["h1"]),
        Paragraph(cfg.get("adresse", ""), styles["small"]),
        Paragraph(cfg.get("cp_ville", ""), styles["small"]),
        Spacer(1, 4),
        Paragraph(f"SIRET&nbsp;: {cfg.get('siret','—')}", styles["small"]),
        Paragraph(f"TVA&nbsp;: {cfg.get('tva','—')}", styles["small"]),
    ]
    return Table([[left, ""]], colWidths=[120 * mm, 60 * mm])


def _client_block(client: dict, styles) -> Table:
    nom = f"{client.get('prenom','') or ''} {client.get('nom','') or ''}".strip()
    cells = [
        Paragraph("<b>Facturé à</b>", styles["h2"]),
        Paragraph(nom or "—", styles["body"]),
    ]
    if client.get("adresse"):
        cells.append(Paragraph(client["adresse"], styles["small"]))
    if client.get("email"):
        cells.append(Paragraph(client["email"], styles["small"]))
    if client.get("telephone"):
        cells.append(Paragraph(client["telephone"], styles["small"]))
    return Table([[cells]], colWidths=[90 * mm], hAlign="LEFT")


def _vehicule_block(veh: dict, styles) -> Table | None:
    if not (veh.get("immatriculation") or veh.get("marque")):
        return None
    libelle = " ".join(filter(None, [
        veh.get("marque"), veh.get("modele"), veh.get("immatriculation"),
    ]))
    cells = [
        Paragraph("<b>Véhicule</b>", styles["h2"]),
        Paragraph(libelle, styles["body"]),
    ]
    if veh.get("kilometrage"):
        cells.append(Paragraph(f"{veh['kilometrage']:,} km".replace(",", " "),
                               styles["small"]))
    return Table([[cells]], colWidths=[90 * mm], hAlign="LEFT")


def _meta_block(label: str, numero: str, date_emission: str | None,
                date_echeance: str | None, validite: int | None, styles) -> Table:
    rows = [
        ["Numéro", Paragraph(f"<b>{numero}</b>", styles["body"])],
        ["Date", date_emission or "—"],
    ]
    if date_echeance:
        rows.append(["Échéance", date_echeance])
    if validite:
        rows.append(["Validité", f"{validite} jours"])

    t = Table(rows, colWidths=[28 * mm, 52 * mm])
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
        ("TEXTCOLOR", (0, 0), (0, -1), GRAY_TEXT),
        ("BACKGROUND", (0, 0), (-1, -1), GRAY_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, GRAY_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, GRAY_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _lignes_table(lignes: list[dict]) -> Table:
    data = [["Désignation", "Qté", "PU HT", "Total HT"]]
    for l in lignes:
        qte = l.get("qte", 1)
        pu = l.get("pu_ht", 0)
        total = l.get("total_ht")
        if total is None:
            total = round(qte * pu, 2)
        data.append([
            l.get("desc", ""),
            f"{qte:g}",
            _fmt_money(pu),
            _fmt_money(total),
        ])

    t = Table(data, colWidths=[100 * mm, 15 * mm, 30 * mm, 35 * mm])
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, NAVY),
        ("INNERGRID", (0, 1), (-1, -1), 0.25, GRAY_BORDER),
        ("BOX", (0, 0), (-1, -1), 0.5, GRAY_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRAY_LIGHT]),
    ]))
    return t


def _totaux_table(total_ht: float, tva_pct: float, total_ttc: float) -> Table:
    data = [
        ["Total HT", _fmt_money(total_ht)],
        [f"TVA ({tva_pct:g} %)", _fmt_money(total_ttc - total_ht)],
        ["Total TTC", _fmt_money(total_ttc)],
    ]
    t = Table(data, colWidths=[60 * mm, 35 * mm], hAlign="RIGHT")
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -2), "Helvetica", 10),
        ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 12),
        ("TEXTCOLOR", (0, -1), (-1, -1), BLUE),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE", (0, -1), (-1, -1), 1.5, NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _footer(cfg: dict[str, str], styles) -> Paragraph:
    forme = cfg.get("forme", "")
    capital = cfg.get("capital", "")
    rcs = cfg.get("rcs", "")
    naf = cfg.get("naf", "")
    parts = [p for p in [
        cfg.get("nom"),
        f"{forme} au capital de {capital} €" if forme and capital else None,
        rcs, f"NAF {naf}" if naf else None,
    ] if p]
    return Paragraph(" · ".join(parts), styles["small"])


def _build(
    cfg: dict[str, str],
    titre: str,
    numero: str,
    date_emission: str | None,
    date_echeance: str | None,
    validite: int | None,
    client: dict,
    vehicule: dict,
    lignes: list[dict],
    total_ht: float,
    tva_pct: float,
    total_ttc: float,
    notes: str | None,
    payment_url: str | None,
    extra_legal: str | None,
) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
        title=f"{titre} {numero}",
    )
    s = _styles()
    story: list = []

    # En-tête garage
    story.append(_header_block(cfg, s))
    story.append(Spacer(1, 4 * mm))

    # Titre + meta
    story.append(Paragraph(f"<b>{titre.upper()}</b>", s["h1"]))
    story.append(Spacer(1, 2 * mm))

    # 2 colonnes : client (+véhicule) à gauche, meta à droite
    left_blocks: list = [_client_block(client, s)]
    veh_block = _vehicule_block(vehicule, s)
    if veh_block:
        left_blocks.append(Spacer(1, 4 * mm))
        left_blocks.append(veh_block)
    meta = _meta_block(titre, numero, date_emission, date_echeance, validite, s)

    two_col = Table([[left_blocks, meta]], colWidths=[100 * mm, 80 * mm])
    two_col.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(two_col)
    story.append(Spacer(1, 8 * mm))

    # Lignes
    story.append(_lignes_table(lignes))
    story.append(Spacer(1, 4 * mm))

    # Totaux
    story.append(_totaux_table(total_ht, tva_pct, total_ttc))
    story.append(Spacer(1, 6 * mm))

    # Notes
    if notes:
        story.append(Paragraph("<b>Notes</b>", s["h2"]))
        story.append(Paragraph(notes.replace("\n", "<br/>"), s["body"]))
        story.append(Spacer(1, 4 * mm))

    # Paiement Stripe
    if payment_url:
        story.append(Paragraph(
            f'Paiement en ligne : <a color="#2563eb" href="{payment_url}">'
            f'{payment_url}</a>', s["body"],
        ))
        story.append(Spacer(1, 4 * mm))

    # Mention légale supplémentaire (ex: validité devis)
    if extra_legal:
        story.append(Paragraph(extra_legal, s["small"]))
        story.append(Spacer(1, 2 * mm))

    # Footer mentions légales
    story.append(Spacer(1, 8 * mm))
    story.append(_footer(cfg, s))

    doc.build(story)
    return buf.getvalue()


def _parse_lignes(raw: str | None) -> list[dict]:
    if not raw:
        return []
    try:
        v = json.loads(raw)
        return v if isinstance(v, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def build_facture_pdf(conn: sqlite3.Connection, facture_id: int) -> tuple[bytes, str]:
    row = conn.execute(
        "SELECT f.*, u.nom, u.prenom, u.email, u.telephone, u.adresse, "
        "v.immatriculation, v.marque, v.modele, v.kilometrage "
        "FROM factures f "
        "JOIN users u ON f.client_id=u.id "
        "LEFT JOIN vehicules v ON f.vehicule_id=v.id "
        "WHERE f.id=?", (facture_id,)
    ).fetchone()
    if not row:
        raise ValueError(f"Facture {facture_id} introuvable")

    cfg = get_garage_config(conn)
    fac = dict(row)
    pdf = _build(
        cfg=cfg,
        titre="Facture",
        numero=fac["numero"],
        date_emission=fac.get("date_facture") or fac.get("created_at", "")[:10],
        date_echeance=fac.get("date_echeance"),
        validite=None,
        client={k: fac.get(k) for k in ("nom", "prenom", "email", "telephone", "adresse")},
        vehicule={k: fac.get(k) for k in ("immatriculation", "marque", "modele", "kilometrage")},
        lignes=_parse_lignes(fac.get("lignes")),
        total_ht=fac.get("total_ht") or 0,
        tva_pct=fac.get("tva") or 20,
        total_ttc=fac.get("total_ttc") or 0,
        notes=fac.get("notes"),
        payment_url=fac.get("stripe_payment_url"),
        extra_legal=None,
    )
    return pdf, f"facture_{fac['numero']}.pdf"


def build_devis_pdf(conn: sqlite3.Connection, devis_id: int) -> tuple[bytes, str]:
    row = conn.execute(
        "SELECT d.*, u.nom, u.prenom, u.email, u.telephone, u.adresse, "
        "v.immatriculation, v.marque, v.modele, v.kilometrage "
        "FROM devis d "
        "JOIN users u ON d.client_id=u.id "
        "LEFT JOIN vehicules v ON d.vehicule_id=v.id "
        "WHERE d.id=?", (devis_id,)
    ).fetchone()
    if not row:
        raise ValueError(f"Devis {devis_id} introuvable")

    cfg = get_garage_config(conn)
    dev = dict(row)
    pdf = _build(
        cfg=cfg,
        titre="Devis",
        numero=dev["numero"],
        date_emission=dev.get("created_at", "")[:10],
        date_echeance=dev.get("date_echeance"),
        validite=dev.get("validite"),
        client={k: dev.get(k) for k in ("nom", "prenom", "email", "telephone", "adresse")},
        vehicule={k: dev.get(k) for k in ("immatriculation", "marque", "modele", "kilometrage")},
        lignes=_parse_lignes(dev.get("lignes")),
        total_ht=dev.get("total_ht") or 0,
        tva_pct=dev.get("tva") or 20,
        total_ttc=dev.get("total_ttc") or 0,
        notes=dev.get("notes"),
        payment_url=None,
        extra_legal=(
            "Devis valable {0} jours à compter de sa date d'émission. "
            "Bon pour accord à signer et à dater par le client."
        ).format(dev.get("validite") or 30),
    )
    return pdf, f"devis_{dev['numero']}.pdf"
