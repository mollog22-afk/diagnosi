import os
from flask import Flask, render_template, request, send_file
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
import io
from datetime import datetime

app = Flask(__name__)

# Coefficienti TEP (Standard ARERA)
COEFF_KWH = 0.000187
COEFF_SMC = 0.00082

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/genera', methods=['POST'])
def genera():
    try:
        # Recupero dati Generali
        cliente = request.form.get('cliente', 'N.D.')
        comune = request.form.get('comune', 'N.D.')
        tecnico = request.form.get('tecnico', 'N.D.')
        
        # Elaborazione Triennio (Anni 2021, 2022, 2023)
        anni = [2021, 2022, 2023]
        dati_tabella = []
        for a in anni:
            # Usiamo 0 se il campo è vuoto per evitare errori matematici
            k = float(request.form.get(f'kwh_{a}', 0) or 0)
            s = float(request.form.get(f'smc_{a}', 0) or 0)
            tep = (k * COEFF_KWH) + (s * COEFF_SMC)
            dati_tabella.append([str(a), f"{k:,.0f}", f"{s:,.0f}", f"{tep:.3f}"])

        # Recupero Interventi (ne cerchiamo fino a 5)
        interventi_scelti = []
        for n in range(1, 6):
            val = request.form.get(f'intervento_{n}')
            if val and val.strip():
                interventi_scelti.append([f"Interv. {n}", val])

        # CREAZIONE PDF IN MEMORIA
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
        elements.append(Paragraph("Analisi dei consumi energetici e conversione in TEP (Tonnellate Equivalenti di Petrolio).", styles['Normal']))
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
        elements.append(Paragraph("2. INTERVENTI DI MIGLIORAMENTO", styles['Heading1']))
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
        style_firma = ParagraphStyle('Signature', alignment=2, fontSize=11)
        elements.append(Paragraph("IL TECNICO EGE CERTIFICATO", style_firma))
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph("__________________________", style_firma))
        elements.append(Paragraph(f"{tecnico}", style_firma))

        doc.build(elements)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=f"Diagnosi_{comune}.pdf", mimetype='application/pdf')

    except Exception as e:
        # Questo cattura l'errore e lo mostra invece del generico Internal Server Error
        return f"Si è verificato un errore: {str(e)}", 500

# Necessario per Vercel
app.debug = True
