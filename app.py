from flask import Flask, render_template, request, send_file
import matplotlib.pyplot as plt
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, HRFlowable, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

app = Flask(__name__)

# Coefficienti Ufficiali TEP
COEFF_KWH = 0.000187
COEFF_SMC = 0.00082

def crea_grafico_torta(val_el, val_gas, anno):
    # Calcolo TEP per il grafico
    tep_el = val_el * COEFF_KWH
    tep_gas = val_gas * COEFF_SMC
    
    labels = ['Elettrico', 'Termico']
    sizes = [tep_el, tep_gas]
    colors_pie = ['#3498db', '#e67e22']
    
    plt.figure(figsize=(4, 4))
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors_pie)
    plt.title(f"Ripartizione TEP {anno}")
    
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', bbox_inches='tight')
    plt.close()
    img_buffer.seek(0)
    return img_buffer

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/genera', methods=['POST'])
def genera():
    try:
        f = request.form
        cliente = f.get('cliente', 'N.D.')
        comune = f.get('comune', 'N.D.')
        tecnico = f.get('tecnico', 'N.D.')

        # Parametri per Baseline
        mq_risc = float(f.get('mq_risc') or 1)
        mq_raff = float(f.get('mq_raff') or 1)
        gg_risc = float(f.get('gg_risc') or 1)
        gg_raff = float(f.get('gg_raff') or 1)
        gg_lav = float(f.get('gg_lav') or 1)

        def elabora_anno(anno):
            # Input puri
            el_tot = float(f.get(f'raff_kwh_{anno}',0) or 0) + float(f.get(f'illu_kwh_{anno}',0) or 0) + float(f.get(f'altro_kwh_{anno}',0) or 0) + float(f.get(f'risc_kwh_{anno}',0) or 0)
            gas_smc = float(f.get(f'risc_smc_{anno}',0) or 0)
            # Calcolo TEP Corretto
            tep_el = el_tot * COEFF_KWH
            tep_gas = gas_smc * COEFF_SMC
            tep_tot = tep_el + tep_gas
            # Calcolo kWh eq (1 TEP = 11628 kWh primari)
            kwh_eq = tep_tot * 11628
            return {'el': el_tot, 'gas': gas_smc, 'tep': tep_tot, 'kwh_eq': kwh_eq, 
                    'risc_tot_kwh': (float(f.get(f'risc_kwh_{anno}',0) or 0) + gas_smc * 10.7),
                    'raff_kwh': float(f.get(f'raff_kwh_{anno}',0) or 0),
                    'illu_kwh': float(f.get(f'illu_kwh_{anno}',0) or 0)}

        res23 = elabora_anno(2023)
        res24 = elabora_anno(2024)

        # Baseline 2024 (Consumo / (mq * GG))
        b_risc = res24['risc_tot_kwh'] / (mq_risc * gg_risc) if (mq_risc * gg_risc) > 0 else 0
        b_raff = res24['raff_kwh'] / (mq_raff * gg_raff) if (mq_raff * gg_raff) > 0 else 0
        b_illu = res24['illu_kwh'] / (mq_risc * gg_lav) if (mq_risc * gg_lav) > 0 else 0

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, margin=1.5*cm)
        styles = getSampleStyleSheet()
        elements = []

        # 1. COPERTINA
        t_style = ParagraphStyle('T', fontSize=24, textColor=colors.HexColor("#1a3a5a"), alignment=1, spaceAfter=40)
        elements.append(Spacer(1, 3*cm))
        elements.append(Paragraph("SOPRALLUOGO DIAGNOSI ENERGETICA", t_style))
        elements.append(HRFlowable(width="100%", color=colors.HexColor("#27ae60")))
        elements.append(Spacer(1, 2*cm))
        elements.append(Paragraph(f"<b>CLIENTE:</b> {cliente.upper()}", styles['Heading2']))
        elements.append(Paragraph(f"<b>SITO:</b> Comune di {comune}", styles['Heading3']))
        elements.append(Spacer(1, 7*cm))
        elements.append(Paragraph(f"<b>Referente:</b> {f.get('referente')} | {f.get('telefono')}", styles['Normal']))
        elements.append(Paragraph(f"<b>Tecnico EGE:</b> {tecnico}", styles['Normal']))
        elements.append(PageBreak())

        # 2. DATI GENERALI E INQUADRAMENTO
        elements.append(Paragraph("1. DATI GENERALI E INQUADRAMENTO", styles['Heading1']))
        elements.append(Paragraph(f"""<b>Organizzazione:</b> {cliente}<br/>
        <b>Attività:</b> {f.get('attivita')}<br/>
        <b>Obiettivi:</b> Definizione dei confini energetici e calcolo Baseline triennale.<br/>
        <b>Criteri:</b> Conversione in TEP secondo standard ARERA (El: {COEFF_KWH} | Gas: {COEFF_SMC}).""", styles['Normal']))
        
        # 3. STATO DEI LUOGHI
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph("2. SISTEMA EDIFICIO-IMPIANTO", styles['Heading1']))
        edif_data = [
            ["Elemento", "Dati e Stratigrafie"],
            ["Mq Riscaldati/Raffr.", f"{mq_risc} / {mq_raff} mq"],
            ["Generatori", f.get('gen_info')],
            ["Murature", f.get('strat_muri')],
            ["Copertura", f.get('strat_solaio')],
            ["Pavimento", f.get('strat_pav')]
        ]
        t_edif = Table(edif_data, colWidths=[5*cm, 13*cm])
        t_edif.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.5,colors.grey),('BACKGROUND',(0,0),(-1,0),colors.lightgrey)]))
        elements.append(t_edif)

        # 4. DATI DI INPUT (TRASPARENZA)
        elements.append(PageBreak())
        elements.append(Paragraph("3. ANALISI DEI CONSUMI (DATI DI INPUT)", styles['Heading1']))
        input_data = [
            ["Vettore", "Anno 2023", "Anno 2024"],
            ["Energia Elettrica [kWh]", f"{res23['el']:,.0f}", f"{res24['el']:,.0f}"],
            ["Metano [Smc]", f"{res23['gas']:,.0f}", f"{res24['gas']:,.0f}"]
        ]
        t_in = Table(input_data, colWidths=[6*cm, 6*cm, 6*cm])
        t_in.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.5,colors.black),('BACKGROUND',(0,0),(-1,0),colors.HexColor("#f1f1f1"))]))
        elements.append(t_in)

        # 5. BILANCIO TEP E GRAFICI
        elements.append(Spacer(1, 1*cm))
        elements.append(Paragraph("4. BILANCIO ENERGETICO [TEP]", styles['Heading1']))
        bil_data = [
            ["Anno", "Consumo [kWh eq]", "Consumo [TEP]"],
            ["2023", f"{res23['kwh_eq']:,.0f}", f"{res23['tep']:.4f}"],
            ["2024", f"{res24['kwh_eq']:,.0f}", f"{res24['tep']:.4f}"]
        ]
        t_bil = Table(bil_data, colWidths=[6*cm, 6*cm, 6*cm])
        t_bil.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor("#1a3a5a")),('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),('GRID',(0,0),(-1,-1),0.5,colors.grey)]))
        elements.append(t_bil)

        # Inserimento Grafici
        elements.append(Spacer(1, 1*cm))
        chart23 = crea_grafico_torta(res23['el'], res23['gas'], 2023)
        chart24 = crea_grafico_torta(res24['el'], res24['gas'], 2024)
        
        t_charts = Table([[Image(chart23, width=7*cm, height=7*cm), Image(chart24, width=7*cm, height=7*cm)]])
        elements.append(t_charts)

        # 6. BASELINE
        elements.append(Spacer(1, 1*cm))
        elements.append(Paragraph("5. INDICATORI DI PRESTAZIONE (BASELINE 2024)", styles['Heading1']))
        base_data = [
            ["Servizio", "Formula", "Risultato [kWh/(mq*GG)]"],
            ["Riscaldamento", "Cons. Risc / (Mq * GG risc)", f"{base_risc:.5f}"],
            ["Raffrescamento", "Cons. Raffr / (Mq * GG raff)", f"{base_raff:.5f}"],
            ["Illuminazione", "Cons. Illu / (Mq * GG lav)", f"{base_illu:.5f}"]
        ]
        t_base = Table(base_data, colWidths=[5*cm, 6*cm, 7*cm])
        t_base.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.5,colors.grey),('BACKGROUND',(0,0),(-1,0),colors.HexColor("#27ae60")),('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke)]))
        elements.append(t_base)

        doc.build(elements)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=f"Sopralluogo_{comune}.pdf")

    except Exception as e: return f"Errore nel calcolo: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
