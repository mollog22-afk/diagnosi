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

# Coefficienti Ufficiali
COEFF_KWH = 0.000187
COEFF_SMC = 0.00082

def safe_float(value):
    try:
        if not value or str(value).strip() == "": return 0.0
        return float(str(value).replace(',', '.'))
    except: return 0.0

def crea_grafico_torta(val_el, val_gas, anno):
    tep_el = val_el * COEFF_KWH
    tep_gas = val_gas * COEFF_SMC
    if tep_el <= 0 and tep_gas <= 0:
        plt.figure(figsize=(3, 3))
        plt.text(0.5, 0.5, 'Nessun dato', ha='center')
    else:
        plt.figure(figsize=(3, 3))
        plt.pie([tep_el, tep_gas], labels=['Elettrico', 'Termico'], autopct='%1.1f%%', colors=['#3498db', '#e67e22'])
    plt.title(f"Ripartizione TEP {anno}", fontsize=10)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close()
    buf.seek(0)
    return buf

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/genera', methods=['POST'])
def genera():
    try:
        f = request.form
        
        # --- DATI GENERALI ---
        cliente = f.get('cliente', '')
        comune = f.get('comune', '')
        referente = f.get('referente', '')
        telefono = f.get('telefono', '')
        mail = f.get('mail', '')
        destinazione = f.get('destinazione', '')
        attivita = f.get('attivita', '')

        # --- DATI TECNICI ---
        mq_risc = safe_float(f.get('mq_risc')) or 1.0
        mq_raff = safe_float(f.get('mq_raff')) or 1.0
        gg_risc = safe_float(f.get('gg_risc')) or 1.0
        gg_raff = safe_float(f.get('gg_raff')) or 1.0
        gg_lav = safe_float(f.get('gg_lav')) or 1.0
        gen_info = f.get('gen_info', '')
        strat_muri = f.get('strat_muri', '')
        strat_pav = f.get('strat_pav', '')
        strat_solaio = f.get('strat_solaio', '')

        # --- ELABORAZIONE CONSUMI ---
        def elabora(anno):
            rk = safe_float(f.get(f'risc_kwh_{anno}'))
            rs = safe_float(f.get(f'risc_smc_{anno}'))
            ra = safe_float(f.get(f'raff_kwh_{anno}'))
            il = safe_float(f.get(f'illu_kwh_{anno}'))
            al = safe_float(f.get(f'altro_kwh_{anno}'))
            
            el_tot = rk + ra + il + al
            gas_tot = rs
            tep = (el_tot * COEFF_KWH) + (gas_tot * COEFF_SMC)
            return {'el': el_tot, 'gas': gas_tot, 'tep': tep, 'rk_tot': rk + (rs*10.7), 'ra': ra, 'il': il}

        d23 = elabora(2023)
        d24 = elabora(2024)

        # Baseline 2024
        b_risc = d24['rk_tot'] / (mq_risc * gg_risc) if (mq_risc * gg_risc) > 0 else 0
        b_raff = d24['ra'] / (mq_raff * gg_raff) if (mq_raff * gg_raff) > 0 else 0
        b_illu = d24['il'] / (mq_risc * gg_lav) if (mq_risc * gg_lav) > 0 else 0

        # --- COSTRUZIONE PDF ---
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
        styles = getSampleStyleSheet()
        elements = []

        # Intestazione
        title_st = ParagraphStyle('T', fontSize=22, textColor=colors.HexColor("#1a3a5a"), alignment=1)
        elements.append(Paragraph("SOPRALLUOGO DIAGNOSI ENERGETICA", title_st))
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#27ae60")))
        elements.append(Spacer(1, 1*cm))

        # 1. Anagrafica
        elements.append(Paragraph("<b>1. DATI GENERALI E REFERENTI</b>", styles['Heading2']))
        data_ana = [
            ["Cliente:", cliente, "Comune:", comune],
            ["Referente:", referente, "Telefono:", telefono],
            ["Email:", mail, "Uso:", destinazione],
            ["Attività:", attivita, "", ""]
        ]
        t_ana = Table(data_ana, colWidths=[3*cm, 6*cm, 3*cm, 6*cm])
        t_ana.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('FONTSIZE',(0,0),(-1,-1), 9)]))
        elements.append(t_ana)

        # 2. Involucro e Impianti
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph("<b>2. SISTEMA EDIFICIO-IMPIANTO</b>", styles['Heading2']))
        data_tec = [
            ["Mq Riscaldati:", f"{mq_risc}", "Mq Raffrescati:", f"{mq_raff}"],
            ["GG Risc:", f"{gg_risc}", "GG Raffr:", f"{gg_raff}"],
            ["Generatori:", gen_info, "GG Lavorativi:", f"{gg_lav}"],
            ["Murature:", strat_muri, "", ""],
            ["Pavimento:", strat_pav, "Copertura:", strat_solaio]
        ]
        t_tec = Table(data_tec, colWidths=[4*cm, 5*cm, 4*cm, 5*cm])
        t_tec.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('FONTSIZE',(0,0),(-1,-1), 9)]))
        elements.append(t_tec)

        # 3. Interventi
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph("<b>3. INTERVENTI DI MIGLIORAMENTO IPOTIZZATI</b>", styles['Heading2']))
        for i in range(1,6):
            val = f.get(f'intervento_{i}')
            if val: elements.append(Paragraph(f"• {val}", styles['Normal']))

        # 4. Consumi di Input e Grafici
        elements.append(PageBreak())
        elements.append(Paragraph("<b>4. ANALISI DEI CONSUMI E BILANCIO TEP</b>", styles['Heading2']))
        
        # Tabella Input
        data_in = [
            ["Vettore", "Anno 2023", "Anno 2024"],
            ["Elettrico Totale [kWh]", f"{d23['el']:,.0f}", f"{d24['el']:,.0f}"],
            ["Gas Metano [Smc]", f"{d23['gas']:,.0f}", f"{d24['gas']:,.0f}"],
            ["TOTALE [TEP]", f"{d23['tep']:.4f}", f"{d24['tep']:.4f}"]
        ]
        t_in = Table(data_in, colWidths=[6*cm, 6*cm, 6*cm])
        t_in.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor("#1a3a5a")), ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke), ('GRID', (0,0),(-1,-1), 0.5, colors.grey)]))
        elements.append(t_in)
        
        # Grafici
        elements.append(Spacer(1, 1*cm))
        g23 = crea_grafico_torta(d23['el'], d23['gas'], 2023)
        g24 = crea_grafico_torta(d24['el'], d24['gas'], 2024)
        elements.append(Table([[Image(g23, 7*cm, 7*cm), Image(g24, 7*cm, 7*cm)]], colWidths=[9*cm, 9*cm]))

        # 5. Baseline
        elements.append(Spacer(1, 1*cm))
        elements.append(Paragraph("<b>5. INDICATORI DI PRESTAZIONE (BASELINE 2024)</b>", styles['Heading2']))
        data_b = [
            ["Servizio", "Formula di calcolo", "Valore [kWh/(mq*GG)]"],
            ["Riscaldamento", "Cons.Risc / (Mq * GG risc)", f"{b_risc:.5f}"],
            ["Raffrescamento", "Cons.Raffr / (Mq * GG raff)", f"{b_raff:.5f}"],
            ["Illuminazione", "Cons.Illu / (Mq * GG lav)", f"{b_illu:.5f}"]
        ]
        t_b = Table(data_b, colWidths=[5*cm, 7*cm, 6*cm])
        t_b.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor("#27ae60")), ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke), ('GRID', (0,0),(-1,-1), 0.5, colors.grey)]))
        elements.append(t_b)

        doc.build(elements)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=f"Sopralluogo_{comune}.pdf")

    except Exception as e:
        return f"Errore critico: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
