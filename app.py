from flask import Flask, render_template, request, send_file
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
import io
from datetime import datetime

app = Flask(__name__)

# Coefficienti TEP (ARERA/MISE)
COEFF_KWH = 0.000187
COEFF_SMC = 0.00082

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/genera', methods=['POST'])
def genera():
    # Recupero dati Generali
    cliente = request.form['cliente']
    comune = request.form['comune']
    tecnico = request.form['tecnico']
    
    # Elaborazione Triennio
    anni = [2021, 2022, 2023]
    dati_tabella = []
    for a in anni:
        k = float(request.form.get(f'kwh_{a}', 0))
        s = float(request.form.get(f'smc_{a}', 0))
        tep = (k * COEFF_KWH) + (s * COEFF_SMC)
        dati_tabella.append([str(a), f"{k:,.0f}", f"{s:,.0f}", f"{tep:.3f}"])

    # Recupero Interventi
    interventi_scelti = []
    for n in range(1, 6):
        val = request.form.get(f'intervento_{n}')
        if val: interventi_scelti.append([f"Intervento {n}", val])

    # CREAZIONE PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    elements = []

    # -- COPERTINA --
    style_titolo = ParagraphStyle('Title', fontSize=26, leading=32, alignment=1, textColor=colors.HexColor("#1a3a5a"), spaceAfter=30)
    elements.append(Spacer(1, 4*cm))
    elements.append(Paragraph("RAPPORTO DI DIAGNOSI ENERGETICA", style_titolo))
    elements.append(HRFlowable(width="80%", thickness=2, color=colors.HexColor("#27ae60")))
    elements.append(Spacer(1, 2*cm))
    elements.append(Paragraph(f"<b>CLIENTE:</b> {cliente.upper()}", styles['Heading2']))
    elements.append(Paragraph(f"<b>SITO:</b> Comune di {comune}", styles['Heading3']))
    elements.append(Spacer(1, 8*cm))
    elements.append(Paragraph(f"Tecnico Auditor (EGE): {tecnico}", styles['Normal']))
    elements.append(Paragraph(f"Data di emissione: {datetime.now().strftime('%d/%m/%Y')}", styles['Normal']))
    elements.append(PageBreak())

    # -- ANALISI CONSUMI --
    elements.append(Paragraph("1. QUADRO STORICO DEI CONSUMI", styles['Heading1']))
    elements.append(Paragraph("Si riporta la sintesi dei consumi energetici del triennio analizzato e la relativa conversione in Tonnellate Equivalenti di Petrolio (TEP).", styles['Normal']))
    elements.append(Spacer(1, 0.5*cm))

    header_cons = ["Anno", "Elettrico [kWh]", "Termico [Smc]", "Totale [TEP]"]
    t_cons = Table([header_cons] + dati_tabella, colWidths=[3*cm, 4*cm, 4*cm, 4*cm])
    t_cons.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1a3a5a")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(t_cons)
    
    # -- INTERVENTI --
    elements.append(Spacer(1, 1.5*cm))
    elements.append(Paragraph("2. INTERVENTI DI MIGLIORAMENTO INDIVIDUATI", styles['Heading1']))
    elements.append(Paragraph("In base all'analisi energetica, sono stati ipotizzati i seguenti interventi di efficienza:", styles['Normal']))
    elements.append(Spacer(1, 0.5*cm))

    if interventi_scelti:
        t_int = Table([["ID", "Categoria Intervento"]] + interventi_scelti, colWidths=[3*cm, 12*cm])
        t_int.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#27ae60")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        elements.append(t_int)
    else:
        elements.append(Paragraph("Nessun intervento selezionato.", styles['Italic']))

    # -- FIRMA --
    elements.append(Spacer(1, 4*cm))
    elements.append(Paragraph("IL TECNICO EGE CERTIFICATO", ParagraphStyle('Signature', alignment=2)))
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph("__________________________", ParagraphStyle('Line', alignment=2)))
    elements.append(Paragraph(f"Ing./Arch. {tecnico}", ParagraphStyle('Name', alignment=2)))

    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"Diagnosi_Energetica_{comune}.pdf")

if __name__ == '__main__':
    app.run(debug=True)
