from flask import Flask, render_template, request, send_file
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
import io

app = Flask(__name__)

COEFF_KWH = 0.000187
COEFF_SMC = 0.00082

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/genera', methods=['POST'])
def genera():
    try:
        f = request.form
        mq_risc = float(f.get('mq_risc', 1) or 1)
        mq_raff = float(f.get('mq_raff', 1) or 1)
        gg_risc = float(f.get('gg_risc', 1) or 1)
        gg_raff = float(f.get('gg_raff', 1) or 1)
        gg_lav = float(f.get('gg_lav', 1) or 1)

        def get_dati(anno):
            rk = float(f.get(f'risc_kwh_{anno}', 0) or 0)
            rs = float(f.get(f'risc_smc_{anno}', 0) or 0)
            ra = float(f.get(f'raff_kwh_{anno}', 0) or 0)
            il = float(f.get(f'illu_kwh_{anno}', 0) or 0)
            al = float(f.get(f'altro_kwh_{anno}', 0) or 0)
            tep = ((rk + ra + il + al) * COEFF_KWH) + (rs * COEFF_SMC)
            return {'tep': tep, 'risc': (rk + rs*10.7), 'raff': ra, 'illu': il, 'tot_kwh': (rk + ra + il + al + rs*10.7)}

        d23 = get_dati(2023)
        d24 = get_dati(2024)

        # Baseline 2024
        b_risc = d24['risc'] / (mq_risc * gg_risc) if (mq_risc * gg_risc) > 0 else 0
        b_raff = d24['raff'] / (mq_raff * gg_raff) if (mq_raff * gg_raff) > 0 else 0
        b_illu = d24['illu'] / (mq_risc * gg_lav) if (mq_risc * gg_lav) > 0 else 0

        # Recupero Interventi
        interventi = [f.get(f'intervento_{i}') for i in range(1,6) if f.get(f'intervento_{i}')]

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        # Grafica PDF
        title_style = ParagraphStyle('T', fontSize=22, textColor=colors.HexColor("#1a3a5a"), alignment=1)
        elements.append(Paragraph("SOPRALLUOGO DIAGNOSI ENERGETICA", title_style))
        elements.append(HRFlowable(width="100%", color=colors.HexColor("#27ae60")))
        elements.append(Spacer(1, 0.5*cm))

        # 1. Dati Generali e Inquadramento
        elements.append(Paragraph("<b>1. DATI GENERALI E INQUADRAMENTO</b>", styles['Heading3']))
        elements.append(Paragraph(f"Organizzazione: {f.get('cliente')} - Comune: {f.get('comune')}<br/>Referente: {f.get('referente')} - Contatto: {f.get('telefono')}<br/>Attività: {f.get('attivita')}", styles['Normal']))
        
        # 2. Edificio Impianto
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph("<b>2. SISTEMA EDIFICIO-IMPIANTO</b>", styles['Heading3']))
        dati_ed = [
            ["Elemento", "Descrizione"],
            ["Murature", f.get('strat_muri')],
            ["Solaio", f.get('strat_solaio')],
            ["Pavimento", f.get('strat_pav')],
            ["Generatori", f.get('gen_info')]
        ]
        t_ed = Table(dati_ed, colWidths=[4*cm, 14*cm])
        t_ed.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.5,colors.grey),('BACKGROUND',(0,0),(-1,0),colors.whitesmoke)]))
        elements.append(t_ed)

        # 3. Interventi
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph("<b>3. INTERVENTI DI MIGLIORAMENTO IPOTIZZATI</b>", styles['Heading3']))
        if interventi:
            for i in interventi: elements.append(Paragraph(f"• {i}", styles['Normal']))
        else: elements.append(Paragraph("Nessun intervento selezionato.", styles['Italic']))

        # 4. Bilancio TEP e Baseline
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph("<b>4. BILANCIO ENERGETICO E BASELINE</b>", styles['Heading3']))
        tab_tep = [
            ["Anno", "Consumo Tot [kWh eq]", "Consumo Tot [TEP]"],
            ["2023", f"{d23['tot_kwh']:,.0f}", f"{d23['tep']:.4f}"],
            ["2024", f"{d24['tot_kwh']:,.0f}", f"{d24['tep']:.4f}"]
        ]
        t_tep = Table(tab_tep, colWidths=[6*cm, 6*cm, 6*cm])
        t_tep.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor("#1a3a5a")),('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),('GRID',(0,0),(-1,-1),0.5,colors.grey)]))
        elements.append(t_tep)

        elements.append(Spacer(1, 0.3*cm))
        tab_base = [
            ["Servizio", "Baseline 2024 [kWh/(mq*GG)]"],
            ["Riscaldamento", f"{b_risc:.5f}"],
            ["Raffrescamento", f"{b_raff:.5f}"],
            ["Illuminazione", f"{b_illu:.5f}"]
        ]
        t_base = Table(tab_base, colWidths=[9*cm, 9*cm])
        t_base.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor("#27ae60")),('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),('GRID',(0,0),(-1,-1),0.5,colors.grey)]))
        elements.append(t_base)

        doc.build(elements)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=f"Sopralluogo_Diagnosi_{f.get('comune')}.pdf")
    except Exception as e: return f"Errore: {e}"

if __name__ == '__main__':
    app.run(debug=True)
