from flask import Flask, render_template, request, send_file
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
import io
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/genera', methods=['POST'])
def genera():
    # 1. Recupero dati dal web form
    cliente = request.form['cliente']
    tecnico = request.form['tecnico']
    kwh = float(request.form['kwh'])
    smc = float(request.form['smc'])

    # 2. Calcolo TEP (Coefficienti standard)
    tep_elettrico = kwh * 0.000187
    tep_termico = smc * 0.00082
    tep_totale = tep_elettrico + tep_termico

    # 3. Creazione PDF
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Intestazione
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width/2, height - 2*cm, "RAPPORTO DI DIAGNOSI ENERGETICA")
    
    c.setFont("Helvetica", 10)
    c.drawString(2*cm, height - 3.5*cm, f"Cliente: {cliente}")
    c.drawString(2*cm, height - 4*cm, f"Data Report: {datetime.now().strftime('%d/%m/%Y')}")

    # Sezione Calcolo Energetico
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2*cm, height - 6*cm, "Analisi dei Consumi e Bilancio in TEP")
    
    c.setFont("Helvetica", 12)
    y = height - 7*cm
    c.drawString(2.5*cm, y, f"• Consumo Elettrico: {kwh:,.2f} kWh  =>  {tep_elettrico:.4f} TEP")
    y -= 0.8*cm
    c.drawString(2.5*cm, y, f"• Consumo Termico: {smc:,.2f} Sm3  =>  {tep_termico:.4f} TEP")
    
    # Risultato Totale evidenziato
    y -= 1.2*cm
    c.setFont("Helvetica-Bold", 13)
    c.setFillColor(colors.darkgreen)
    c.drawString(2.5*cm, y, f"CONSUMO TOTALE: {tep_totale:.4f} TEP")
    
    # Piè di pagina e Firma
    c.setFillColor(colors.black)
    c.setDash(1, 2)
    c.line(width - 9*cm, 4*cm, width - 2*cm, 4*cm)
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(width - 8*cm, 3.5*cm, "Firma del Tecnico EGE")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(width - 8*cm, 3*cm, tecnico)

    c.showPage()
    c.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name=f"Diagnosi_TEP_{cliente}.pdf")

if __name__ == '__main__':
    app.run(debug=True)