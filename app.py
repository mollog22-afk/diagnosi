from flask import Flask, render_template, request, send_file
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
import io

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/genera', methods=['POST'])
def genera():
    try:
        # Recupero Dati Form
        d = request.form
        cliente = d.get('cliente')
        referente = d.get('referente')
        
        # Dati per calcolo Baseline
        mq_risc = float(d.get('mq_risc', 1))
        mq_raff = float(d.get('mq_raff', 1))
        gg_risc = float(d.get('gg_risc', 1))
        gg_raff = float(d.get('gg_raff', 1))
        gg_lav = float(d.get('gg_lav', 1))

        # Consumi
        c_risc = float(d.get('val_risc', 0))
        c_raff = float(d.get('val_raff', 0))
        c_illu = float(d.get('val_illu', 0))

        # CALCOLO BASELINE (EnPI)
        # Formula: Consumo / (Mq * Giorni)
        base_risc = c_risc / (mq_risc * gg_risc) if (mq_risc * gg_risc) > 0 else 0
        base_raff = c_raff / (mq_raff * gg_raff) if (mq_raff * gg_raff) > 0 else 0
        base_illu = c_illu / (mq_risc * gg_lav) if (mq_risc * gg_lav) > 0 else 0 # Illuminazione basata su mq totali e gg lavorativi

        # --- GENERAZIONE PDF ---
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        # Copertina e Inquadramento (come richiesto)
        elements.append(Paragraph("RAPPORTO DI DIAGNOSI ENERGETICA", styles['Title']))
        elements.append(Spacer(1, 1*cm))
        
        info_org = f"""<b>1. DATI GENERALI E INQUADRAMENTO</b><br/><br/>
        <b>Organizzazione:</b> {cliente}<br/>
        <b>Referente:</b> {referente} - Tel: {d.get('telefono')} - Mail: {d.get('mail')}<br/>
        <b>Destinazione d'uso:</b> {d.get('destinazione')}<br/>
        <b>Attività:</b> {d.get('attivita')}<br/>
        """
        elements.append(Paragraph(info_org, styles['Normal']))
        elements.append(Spacer(1, 1*cm))

        # TABELLA BASELINE E INDICATORI
        elements.append(Paragraph("<b>2. INDICATORI DI PRESTAZIONE ENERGETICA (BASELINE)</b>", styles['Normal']))
        elements.append(Spacer(1, 0.5*cm))

        data_enpi = [
            ["Vettore/Servizio", "Consumo [kWh]", "Parametro Rif.", "Baseline [kWh/(mq*GG)]"],
            ["Riscaldamento", f"{c_risc:,.0f}", f"{mq_risc}mq | {gg_risc}gg", f"{base_risc:.4f}"],
            ["Raffrescamento", f"{c_raff:,.0f}", f"{mq_raff}mq | {gg_raff}gg", f"{base_raff:.4f}"],
            ["Illuminazione", f"{c_illu:,.0f}", f"{mq_risc}mq | {gg_lav}gg", f"{base_illu:.4f}"]
        ]

        t = Table(data_enpi, colWidths=[4*cm, 3.5*cm, 4.5*cm, 4.5*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1a3a5a")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('ALIGN', (0,0), (-1,-1), 'CENTER')
        ]))
        elements.append(t)

        doc.build(elements)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name="Diagnosi_Tecnica.pdf")

    except Exception as e:
        return f"Errore: {e}"

if __name__ == '__main__':
    app.run(debug=True)
