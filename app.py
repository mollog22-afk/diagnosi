from flask import Flask, render_template, request, send_file
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
import io
from datetime import datetime

app = Flask(__name__)

# Coefficienti
COEFF_KWH = 0.000187
COEFF_SMC = 0.00082

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/genera', methods=['POST'])
def genera():
    try:
        f = request.form
        
        # --- CALCOLI BASELINE E TEP PER 2024 ---
        # Per semplicità mostriamo il calcolo baseline sull'ultimo anno
        mq_risc = float(f.get('mq_risc', 1) or 1)
        mq_raff = float(f.get('mq_raff', 1) or 1)
        gg_risc = float(f.get('gg_risc', 1) or 1)
        gg_raff = float(f.get('gg_raff', 1) or 1)
        gg_lav = float(f.get('gg_lav', 1) or 1)

        def get_tep_anno(anno):
            rk = float(f.get(f'risc_kwh_{anno}', 0) or 0)
            rs = float(f.get(f'risc_smc_{anno}', 0) or 0)
            ra = float(f.get(f'raff_kwh_{anno}', 0) or 0)
            il = float(f.get(f'illu_kwh_{anno}', 0) or 0)
            al = float(f.get(f'altro_kwh_{anno}', 0) or 0)
            
            # Conversione TEP
            tep = ((rk + ra + il + al) * COEFF_KWH) + (rs * COEFF_SMC)
            tot_kwh_eq = rk + ra + il + al + (rs * 10.7) # approx smc to kwh
            return {'tep': tep, 'kwh_eq': tot_kwh_eq, 'risc': (rk + rs*10.7), 'raff': ra, 'illu': il}

        dati_2023 = get_tep_anno(2023)
        dati_2024 = get_tep_anno(2024)

        # Baseline 2024
        base_risc = dati_2024['risc'] / (mq_risc * gg_risc) if (mq_risc * gg_risc) > 0 else 0
        base_raff = dati_2024['raff'] / (mq_raff * gg_raff) if (mq_raff * gg_raff) > 0 else 0
        base_illu = dati_2024['illu'] / (mq_risc * gg_lav) if (mq_risc * gg_lav) > 0 else 0

        # --- PDF ---
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5*cm)
        styles = getSampleStyleSheet()
        elements = []

        # Header Professionale
        header_style = ParagraphStyle('H', fontSize=22, textColor=colors.HexColor("#1a3a5a"), alignment=1, spaceAfter=20)
        elements.append(Paragraph("SOPRALLUOGO DIAGNOSI ENERGETICA", header_style))
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#27ae60")))
        elements.append(Spacer(1, 1*cm))

        # 1. Inquadramento
        elements.append(Paragraph("<b>1. DATI GENERALI</b>", styles['Heading3']))
        info = [
            [f"Cliente: {f.get('cliente')}", f"Comune: {f.get('comune')}"],
            [f"Referente: {f.get('referente')}", f"Contatto: {f.get('telefono')}"],
            [f"Destinazione: {f.get('destinazione')}", f"Email: {f.get('mail')}"]
        ]
        t1 = Table(info, colWidths=[9*cm, 9*cm])
        t1.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('FONTSIZE', (0,0), (-1,-1), 9)]))
        elements.append(t1)

        # 2. Strutture e Impianti
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph("<b>2. SISTEMA EDIFICIO-IMPIANTO</b>", styles['Heading3']))
        strutture = [
            ["Elemento", "Descrizione Stratigrafica / Info"],
            ["Murature", f.get('strat_muri')],
            ["Pavimento", f.get('strat_pav')],
            ["Copertura", f.get('strat_solaio')],
            ["Generatori", f.get('gen_info')]
        ]
        t2 = Table(strutture, colWidths=[4*cm, 14*cm])
        t2.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), colors.HexColor("#f1f1f1")), ('GRID',(0,0),(-1,-1), 0.5, colors.grey)]))
        elements.append(t2)

        # 3. Bilancio TEP Biennale
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph("<b>3. BILANCIO ENERGETICO BIENNALE [TEP]</b>", styles['Heading3']))
        bilancio = [
            ["Anno", "Totale kWh eq.", "Totale TEP"],
            ["2023", f"{dati_2023['kwh_eq']:,.0f}", f"{dati_2023['tep']:.4f}"],
            ["2024", f"{dati_2024['kwh_eq']:,.0f}", f"{dati_2024['tep']:.4f}"]
        ]
        t3 = Table(bilancio, colWidths=[6*cm, 6*cm, 6*cm])
        t3.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), colors.HexColor("#1a3a5a")), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke), ('GRID',(0,0),(-1,-1), 0.5, colors.grey)]))
        elements.append(t3)

        # 4. Baseline 2024
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph("<b>4. INDICATORI DI PRESTAZIONE (BASELINE 2024)</b>", styles['Heading3']))
        baselines = [
            ["Servizio", "Baseline [kWh/(mq*GG)]"],
            ["Riscaldamento", f"{base_risc:.5f}"],
            ["Raffrescamento", f"{base_raff:.5f}"],
            ["Illuminazione", f"{base_illu:.5f}"]
        ]
        t4 = Table(baselines, colWidths=[9*cm, 9*cm])
        t4.setStyle(TableStyle([('GRID',(0,0),(-1,-1), 0.5, colors.grey), ('BACKGROUND',(0,0),(-1,0), colors.HexColor("#27ae60")), ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke)]))
        elements.append(t4)

        doc.build(elements)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=f"Sopralluogo_Diagnosi_{f.get('comune')}.pdf")

    except Exception as e:
        return f"Errore: {e}"

if __name__ == '__main__':
    app.run(debug=True)
