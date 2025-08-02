# ✅ Updated invoice.py to include logo in invoice
from fpdf import FPDF
import os
import requests

def generate_invoice(data, filename="invoice.pdf"):
    os.makedirs("invoices", exist_ok=True)
    full_path = os.path.join("invoices", filename)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Logo (top-left corner)
    logo_path = "logo.png"  # Ensure this file exists in your project root
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=10, y=8, w=30)

    # Title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "DHANVANTH TOURS AND TRAVELS", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(200, 10, f"DATE: {data.get('date', '10/06/2025')}", ln=True, align='C')
    pdf.ln(10)

    # Bill To
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(100, 10, f"INVOICE NO: {data['invoice_no']}")
    pdf.ln(5)
    pdf.set_font("Arial", '', 10)
    pdf.cell(100, 10, f"Bill To: {data['customer_name']}", ln=True)
    # FIX: Removed ln=True from multi_cell and replaced '→' with '->'
    pdf.multi_cell(100, 5, f"Address: {data.get('customer_address', 'N/A')}")
    pdf.ln(10)

    # Table Header
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(120, 10, "Description", 1, 0, 'C')
    pdf.cell(40, 10, "Amount (INR)", 1, 1, 'C')

    # Table Rows
    pdf.set_font("Arial", '', 10)
    for item in data['trips']:
        # FIX: Replaced '→' with '->' for Unicode compatibility
        description = item['description'].replace('→', '->')
        pdf.cell(120, 10, description, 1, 0)
        pdf.cell(40, 10, f"INR {item['amount']:.2f}", 1, 1, 'R')

    pdf.ln(5)

    # Summary
    pdf.set_font("Arial", '', 10)
    pdf.cell(120, 10, "Subtotal:", 0, 0, 'R')
    pdf.cell(40, 10, f"INR {data['subtotal']:.2f}", 0, 1, 'R')

    if data.get('discount', 0) > 0:
        pdf.cell(120, 10, f"Discount ({data.get('coupon_code', '')}):", 0, 0, 'R')
        pdf.cell(40, 10, f"- INR {data['discount']:.2f}", 0, 1, 'R')

    pdf.cell(120, 10, "Tax (5%):", 0, 0, 'R')
    pdf.cell(40, 10, f"INR {data['tax']:.2f}", 0, 1, 'R')

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(120, 10, "TOTAL:", 0, 0, 'R')
    pdf.cell(40, 10, f"INR {data['total']:.2f}", 0, 1, 'R')

    pdf.ln(15)
    pdf.set_font("Arial", 'I', 8)
    pdf.multi_cell(0, 5, """
DHANVANTH TOURS AND TRAVELS
(Proprietor: Bejjavarapu Sundhar Reddy J, 9743417444)
Saigardens, Hosakote Main Road, Seegehalli, Bangalore - 560067
GSTIN: 29AEEPH0967F2ZH
""")

    pdf.output(full_path)
    return full_path

def upload_media_to_whatsapp(filepath, phone_number_id, access_token):
    url = f"https://graph.facebook.com/v18.0/{phone_number_id}/media"
    headers = {"Authorization": f"Bearer {access_token}"}
    with open(filepath, 'rb') as f:
        files = {
            'file': (os.path.basename(filepath), f, 'application/pdf')
        }
        data = {
            "messaging_product": "whatsapp",
            "type": "document"
        }
        response = requests.post(url, headers=headers, files=files, data=data)
        result = response.json()
        print(f"📦 Uploaded Media Response: {result}")
        return result.get("id")

def send_invoice_pdf(to, media_id, filename, phone_number_id, access_token):
    url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "document",
        "document": {
            "id": media_id,
            "filename": filename
        }
    }
    response = requests.post(url, headers=headers, json=data)
    print(f"📄 Sent Invoice PDF Response: {response.json()}")
    return response.json()
