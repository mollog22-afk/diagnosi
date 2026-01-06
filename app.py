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

def safe_float(value):
    """Converte in float in modo sicuro, gestendo stringhe vuote o None"""
    try:
        if not value or value.strip() == "":
            return 0.0
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def crea_grafico_torta(val_el, val_gas, anno):
    tep_el = val_el * COEFF_KWH
    tep_gas = val_gas * COEFF_SMC
    
    # Se entrambi sono zero, creiamo un grafico 'vuoto' per evitare errori
    if tep_el == 0 and tep_gas == 0:
        sizes = [1]
        labels = ['Nessun dato']
        colors_pie = ['#bdc3c7']
    else:
        sizes = [tep_el, tep_gas]
        labels = ['Elettrico', 'Termico']
        colors_pie = ['#3498db', '#e67e22']
    
    plt.figure(figsize=(4, 4))
    plt.pie(sizes, labels=labels, autopct='%1.1f%%' if tep_el+tep_gas > 0 else '', startangle=140, colors=colors_pie)
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
        
        # Recupero parametri dimensionali con safe_float
        mq_risc = safe_float(f.get('mq_risc')) or 1.0
        mq_raff = safe_float(f.get('mq_raff')) or 1.0
        gg_risc = safe_float(f.get('gg_risc')) or 1.0
        gg_raff = safe_float(f.get('gg_raff')) or 1.0
        gg_lav = safe_float(f.get('gg_lav')) or 1.0

        def elabora_anno(anno):
            # Recupero dati con funzione di sicurezza
            r_kwh = safe_float(f.get(f'risc_kwh_{anno}'))
            r_smc = safe_float(f.get(f'risc_smc_{anno}'))
            ra_kwh = safe_float(f.get(f'raff_kwh_{anno}'))
            il_kwh = safe_float(f.get(f'illu_kwh_{anno}'))
            al_kwh = safe_float(f.get(f'altro_kwh_{anno}'))

            el_tot = r_kwh + ra_kwh + il_kwh + al_kwh
            gas_smc = r_smc
            
            tep_tot = (el_tot * COEFF_KWH) + (gas_smc * COEFF_SMC)
            kwh_eq = tep_tot * 11628
            
            return {
                'el': el_tot, 'gas': gas_smc, 'tep': tep_tot, 'kwh_eq': kwh_eq, 
                'risc_tot_kwh': r_kwh + (gas_smc * 10.7),
                'raff_kwh': ra_kwh,
                'illu_kwh': il_kwh
            }

        res23 = elabora_anno(2023)
        res24 = elabora_anno(2024)

        # Calcolo Baseline
        b_risc = res24['risc_tot_kwh'] / (mq_risc * gg_risc) if (mq_risc * gg_risc) > 0 else 0
        b_raff = res24['raff_kwh'] / (mq_raff * gg_raff) if (mq_raff * gg_raff) > 0 else 0
        b_illu = res24['illu_kwh'] / (mq_risc * gg_lav) if (mq_risc * gg_lav) > 0 else 0

        # --- Generazione PDF (Resto del codice invariato) ---
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, margin=1.5*cm)
        styles = getSampleStyleSheet()
        elements = []

        # (Inserire qui la logica di costruzione PDF precedentemente fornita...)
        # ... (Copertina, Tabelle, Grafici, Baseline) ...
        # Assicurati di includere la parte dei grafici e degli interventi scelti!
        
        # [Aggiungere qui gli interventi di miglioramento come richiesto prima]
        interventi = [f.get(f'intervento_{i}') for i in range(1,6) if f.get(f'intervento_{i}')]
        
        # Esempio rapido di aggiunta interventi nel PDF
        elements.append(Paragraph("<b>INTERVENTI DI MIGLIORAMENTO IPOTIZZATI</b>", styles['Heading3']))
        if interventi:
            for i in interventi: elements.append(Paragraph(f"• {i}", styles['Normal']))
        else:
            elements.append(Paragraph("Nessun intervento selezionato.", styles['Italic']))

        # Bilancio e Grafici
        elements.append(PageBreak())
        elements.append(Paragraph("BILANCIO ENERGETICO E GRAFICI", styles['Heading1']))
        chart23 = crea_grafico_torta(res23['el'], res23['gas'], 2023)
        chart24 = crea_grafico_torta(res24['el'], res24['gas'], 2024)
        elements.append(Table([[Image(chart23, 7*cm, 7*cm), Image(chart24, 7*cm, 7*cm)]]))

        doc.build(elements)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=f"Sopralluogo_{f.get('comune','Report')}.pdf")

    except Exception as e:
        return f"Errore: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
