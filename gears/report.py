"""
Esportazione report in formato PDF e CSV.
PDF usa reportlab; CSV usa il modulo builtin.
"""

import csv
import datetime


def export_csv(filepath: str, gear_params: dict, pair_results: dict = None,
               strength_results: dict = None) -> None:
    """
    Esporta i risultati di calcolo in un file CSV.

    Parametri:
        filepath        : percorso file di destinazione
        gear_params     : dict da calculate_gear_parameters()
        pair_results    : dict da calculate_gear_pair() (opzionale)
        strength_results: dict da calculate_lewis_bending() + calculate_hertz_contact() (opzionale)
    """
    rows = [
        ["Sezione", "Parametro", "Valore", "Unità"],
        ["Geometria", "Modulo", gear_params.get("m", ""), "mm"],
        ["Geometria", "Numero denti", gear_params.get("z", ""), ""],
        ["Geometria", "Angolo pressione", gear_params.get("alpha", ""), "°"],
        ["Geometria", "Spostamento profilo x", gear_params.get("x_shift", ""), ""],
        ["Geometria", "Diametro primitivo d", gear_params.get("d", ""), "mm"],
        ["Geometria", "Diametro base db", gear_params.get("db", ""), "mm"],
        ["Geometria", "Diametro punta da", gear_params.get("da", ""), "mm"],
        ["Geometria", "Diametro piede df", gear_params.get("df", ""), "mm"],
        ["Geometria", "Spessore dente s", gear_params.get("s", ""), "mm"],
    ]

    if pair_results:
        rows += [
            ["Coppia", "Rapporto trasmissione i", pair_results.get("i", ""), ""],
            ["Coppia", "Interasse standard a", pair_results.get("a_std", ""), "mm"],
            ["Coppia", "Interasse di lavoro a_w", pair_results.get("a_w", ""), "mm"],
            ["Coppia", "Angolo pressione lavoro α_wt", pair_results.get("alpha_wt", ""), "°"],
            ["Coppia", "Rapporto di contatto ε_α", pair_results.get("epsilon_alpha", ""), ""],
            ["Coppia", "Rischio sottosquadro pignone", pair_results.get("undercut_risk_1", ""), ""],
            ["Coppia", "Rischio sottosquadro ruota", pair_results.get("undercut_risk_2", ""), ""],
        ]

    if strength_results:
        bend = strength_results.get("bending", {})
        contact = strength_results.get("contact", {})
        rows += [
            ["Resistenza", "Tensione flessione σ_F", bend.get("sigma_F", ""), "MPa"],
            ["Resistenza", "Tensione ammiss. flessione", bend.get("sigma_F_perm", ""), "MPa"],
            ["Resistenza", "Sicurezza flessione SF", bend.get("SF", ""), ""],
            ["Resistenza", "Tensione contatto σ_H", contact.get("sigma_H", ""), "MPa"],
            ["Resistenza", "Tensione ammiss. contatto", contact.get("sigma_H_perm", ""), "MPa"],
            ["Resistenza", "Sicurezza contatto SH", contact.get("SH", ""), ""],
        ]

    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerows(rows)


def export_pdf(filepath: str, gear_params: dict, pair_results: dict = None,
               strength_results: dict = None, material_name: str = "") -> None:
    """
    Esporta un report tecnico in PDF usando reportlab.

    Parametri:
        filepath        : percorso file di destinazione
        gear_params     : dict da calculate_gear_parameters()
        pair_results    : dict da calculate_gear_pair() (opzionale)
        strength_results: dict con chiavi 'bending' e 'contact' (opzionale)
        material_name   : nome del materiale selezionato
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    except ImportError:
        raise ImportError("reportlab non installato. Eseguire: pip install reportlab")

    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    story = []

    # Intestazione
    story.append(Paragraph("Relazione Tecnica — Calcolo Ingranaggi", styles['Title']))
    story.append(Paragraph(f"Data: {datetime.date.today().strftime('%d/%m/%Y')}", styles['Normal']))
    if material_name:
        story.append(Paragraph(f"Materiale: {material_name}", styles['Normal']))
    story.append(Spacer(1, 6*mm))

    def make_table(title, data_rows, col_widths=None):
        story.append(Paragraph(title, styles['Heading2']))
        table_data = [["Parametro", "Valore", "Unità"]] + data_rows
        t = Table(table_data, colWidths=col_widths or [90*mm, 50*mm, 25*mm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f2f2f2')]),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ]))
        story.append(t)
        story.append(Spacer(1, 4*mm))

    # Geometria
    geom_rows = [
        ["Modulo (m)", f"{gear_params.get('m', ''):.3f}", "mm"],
        ["Numero denti (z)", str(gear_params.get('z', '')), ""],
        ["Angolo pressione (α)", f"{gear_params.get('alpha', ''):.1f}", "°"],
        ["Spostamento profilo (x)", f"{gear_params.get('x_shift', ''):.3f}", ""],
        ["Diametro primitivo (d)", f"{gear_params.get('d', ''):.3f}", "mm"],
        ["Diametro base (db)", f"{gear_params.get('db', ''):.3f}", "mm"],
        ["Diametro punta (da)", f"{gear_params.get('da', ''):.3f}", "mm"],
        ["Diametro piede (df)", f"{gear_params.get('df', ''):.3f}", "mm"],
        ["Spessore dente (s)", f"{gear_params.get('s', ''):.4f}", "mm"],
    ]
    make_table("1. Geometria Ingranaggio", geom_rows)

    # Coppia
    if pair_results:
        def _flag(v): return "SI ⚠" if v else "No"
        pair_rows = [
            ["Rapporto trasmissione (i)", f"{pair_results.get('i', ''):.3f}", ""],
            ["Interasse standard (a)", f"{pair_results.get('a_std', ''):.3f}", "mm"],
            ["Interasse di lavoro (a_w)", f"{pair_results.get('a_w', ''):.3f}", "mm"],
            ["Angolo pressione lavoro (α_wt)", f"{pair_results.get('alpha_wt', ''):.3f}", "°"],
            ["Rapporto di contatto (ε_α)", f"{pair_results.get('epsilon_alpha', ''):.3f}", ""],
            ["Rischio sottosquadro pignone", _flag(pair_results.get('undercut_risk_1')), ""],
            ["Rischio sottosquadro ruota", _flag(pair_results.get('undercut_risk_2')), ""],
        ]
        make_table("2. Analisi Coppia", pair_rows)

    # Resistenza
    if strength_results:
        bend = strength_results.get("bending", {})
        contact = strength_results.get("contact", {})
        str_rows = [
            ["Forza tangenziale (Ft)", f"{strength_results.get('Ft', ''):.1f}", "N"],
            ["--- FLESSIONE ---", "", ""],
            ["Tensione flessione (σ_F)", f"{bend.get('sigma_F', ''):.2f}", "MPa"],
            ["Tensione ammiss. flessione", f"{bend.get('sigma_F_perm', ''):.2f}", "MPa"],
            ["Sicurezza flessione (SF)", f"{bend.get('SF', ''):.3f}", ""],
            ["--- CONTATTO ---", "", ""],
            ["Tensione contatto (σ_H)", f"{contact.get('sigma_H', ''):.2f}", "MPa"],
            ["Tensione ammiss. contatto", f"{contact.get('sigma_H_perm', ''):.2f}", "MPa"],
            ["Sicurezza contatto (SH)", f"{contact.get('SH', ''):.3f}", ""],
        ]
        make_table("3. Analisi Resistenza (ISO 6336 semplificato)", str_rows)

    doc.build(story)
