import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime
import base64

# --- Page Config ---
st.set_page_config(page_title="SL Tax Invoice Generator", layout="wide")

# --- Helper Functions ---
def get_month_abbr(date_obj):
    return date_obj.strftime("%b").upper()

def format_currency(value):
    return f"{value:,.2f}"

class InvoicePDF(FPDF):
    def header(self):
        # The title box as seen in the template
        self.set_font("helvetica", "B", 14)
        title = "TAX INVOICE"
        w = self.get_string_width(title) + 10
        self.set_x((210 - w) / 2)
        self.cell(w, 10, title, border=1, align="C", ln=1)
        self.ln(5)

    def draw_info_blocks(self, data):
        self.set_font("helvetica", "", 10)
        
        # Calculate positions
        start_y = self.get_y()
        col_width = 90
        margin = 10
        
        # Left Block: Supplier
        self.set_xy(margin, start_y)
        left_text = (
            f"Date of Invoice: {data['invoice_date']}\n"
            f"Supplier's TIN : {data['supplier_tin']}\n"
            f"Supplier's Name: {data['supplier_name']}\n"
            f"Address : {data['supplier_address']}\n\n"
            f"Telephone No.*: {data['supplier_phone']}"
        )
        self.multi_cell(col_width, 7, left_text, border=1)
        left_end_y = self.get_y()
        
        # Right Block: Purchaser
        self.set_xy(margin + col_width + 10, start_y)
        right_text = (
            f"Tax Invoice No. : {data['invoice_no']}\n"
            f"Purchaser's TIN : {data['purchaser_tin']}\n"
            f"Purchaser's Name: {data['purchaser_name']}\n"
            f"Address : {data['purchaser_address']}\n\n"
            f"Telephone No.*: {data['purchaser_phone']}"
        )
        self.multi_cell(col_width, 7, right_text, border=1)
        right_end_y = self.get_y()
        
        max_y = max(left_end_y, right_end_y)
        self.set_y(max_y + 2)
        
        # Mid Section
        self.set_x(margin)
        mid_left = f"Date of Supply : {data['supply_date']}"
        self.cell(col_width, 8, mid_left, border=1)
        
        self.set_x(margin + col_width + 10)
        mid_right = f"Place of Supply :* {data['supply_place']}"
        self.cell(col_width, 8, mid_right, border=1, ln=1)
        
        self.ln(2)
        self.set_x(margin)
        self.cell(col_width * 2 + 10, 8, f"Additional Information if any:* {data['additional_info']}", border=1, ln=1)
        self.ln(5)

    def draw_table(self, items, totals):
        margin = 10
        self.set_x(margin)
        self.set_font("helvetica", "B", 9)
        
        # Column widths
        w_ref = 25
        w_desc = 75
        w_qty = 20
        w_price = 30
        w_amt = 40
        
        # Headers
        self.cell(w_ref, 10, "Reference*", border=1, align="C")
        self.cell(w_desc, 10, "Description of Goods or Services", border=1, align="C")
        self.cell(w_qty, 10, "Quantity", border=1, align="C")
        self.cell(w_price, 10, "Unit Price", border=1, align="C")
        self.cell(w_amt, 10, "Amount (Rs.)", border=1, align="C")
        self.ln()
        
        self.set_font("helvetica", "", 9)
        for item in items:
            self.set_x(margin)
            self.cell(w_ref, 8, str(item['ref']), border=1)
            self.cell(w_desc, 8, str(item['desc']), border=1)
            self.cell(w_qty, 8, str(item['qty']), border=1, align="R")
            self.cell(w_price, 8, format_currency(item['price']), border=1, align="R")
            self.cell(w_amt, 8, format_currency(item['total']), border=1, align="R")
            self.ln()
            
        # Add some empty rows to match template feel if items are few
        if len(items) < 5:
            for _ in range(5 - len(items)):
                self.set_x(margin)
                self.cell(w_ref, 8, "", border=1)
                self.cell(w_desc, 8, "", border=1)
                self.cell(w_qty, 8, "", border=1)
                self.cell(w_price, 8, "", border=1)
                self.cell(w_amt, 8, "", border=1)
                self.ln()

        # Totals
        self.set_font("helvetica", "B", 9)
        total_label_w = w_ref + w_desc + w_qty + w_price
        
        self.set_x(margin)
        self.cell(total_label_w, 8, "Total Value of Supply:", border=1)
        self.cell(w_amt, 8, format_currency(totals['subtotal']), border=1, align="R", ln=1)
        
        self.set_x(margin)
        self.cell(total_label_w, 8, f"VAT Amount (Total Value of Supply @ {totals['vat_rate']}%):", border=1)
        self.cell(w_amt, 8, format_currency(totals['vat_amount']), border=1, align="R", ln=1)
        
        self.set_x(margin)
        self.cell(total_label_w, 8, "Total Amount/consideration including VAT:", border=1)
        self.cell(w_amt, 8, format_currency(totals['grand_total']), border=1, align="R", ln=1)
        
        self.ln(2)
        self.set_x(margin)
        self.cell(total_label_w + w_amt, 8, f"Total Amount in words:* {totals['total_in_words']}", border=1, ln=1)
        
        self.ln(2)
        self.set_x(margin)
        self.cell(total_label_w + w_amt, 8, f"Mode of Payment:* {totals['payment_mode']}", border=1, ln=1)

# --- App UI ---
st.title("🇱🇰 SL Tax Invoice Generator")
st.markdown("Generate official-format VAT Tax Invoices as per Sri Lanka Gazette specifications.")

with st.expander("ℹ️ About Serial Number Format", expanded=False):
    st.write("Recommended Format: `YYMMM_QQQQ_XXXXX`")
    st.write("Example: `26JUL_BR03_1` (Year 2026, July, Branch 03, Serial 1)")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Supplier Details")
    s_name = st.text_input("Supplier's Name", "Your Company Name")
    s_tin = st.text_input("Supplier's TIN (9 digits)", "123456789")
    s_addr = st.text_area("Supplier's Address", "No. 123, Galle Road, Colombo 03")
    s_phone = st.text_input("Supplier's Telephone No.*", "011-2345678")
    
    st.subheader("Invoice Details")
    inv_date = st.date_input("Date of Invoice", datetime.date.today())
    # Auto-generate serial number suggestion
    suggested_no = f"{str(inv_date.year)[2:]}{get_month_abbr(inv_date)}_MAIN_1"
    inv_no = st.text_input("Tax Invoice No.", suggested_no)
    
with col2:
    st.subheader("Purchaser Details")
    p_name = st.text_input("Purchaser's Name", "Client Company Name")
    p_tin = st.text_input("Purchaser's TIN (9 digits)", "987654321")
    p_addr = st.text_area("Purchaser's Address", "Client Address")
    p_phone = st.text_input("Purchaser's Telephone No.*", "")
    
    st.subheader("Supply Details")
    sup_date = st.date_input("Date of Supply", inv_date)
    sup_place = st.text_input("Place of Supply*", "Colombo")
    add_info = st.text_input("Additional Information*", "")

st.divider()
st.subheader("Items")

if 'invoice_items' not in st.session_state:
    st.session_state.invoice_items = [{'ref': '', 'desc': '', 'qty': 1, 'price': 0.0}]

def add_item():
    st.session_state.invoice_items.append({'ref': '', 'desc': '', 'qty': 1, 'price': 0.0})

def remove_item(idx):
    if len(st.session_state.invoice_items) > 1:
        st.session_state.invoice_items.pop(idx)

for i, item in enumerate(st.session_state.invoice_items):
    c1, c2, c3, c4, c5 = st.columns([1, 3, 1, 1, 0.5])
    with c1:
        item['ref'] = st.text_input(f"Ref*", item['ref'], key=f"ref_{i}")
    with c2:
        item['desc'] = st.text_input(f"Description", item['desc'], key=f"desc_{i}")
    with c3:
        item['qty'] = st.number_input(f"Qty", value=item['qty'], step=1, key=f"qty_{i}")
    with c4:
        item['price'] = st.number_input(f"Unit Price", value=item['price'], step=0.01, key=f"price_{i}")
    with c5:
        st.write("") # Spacer
        if st.button("🗑️", key=f"remove_{i}"):
            remove_item(i)
            st.rerun()

st.button("➕ Add Item", on_click=add_item)

st.divider()
st.subheader("Totals & Payment")
tc1, tc2, tc3 = st.columns(3)

with tc1:
    vat_rate = st.number_input("VAT Rate (%)", value=18.0, step=0.1)

# Calculations
items_data = []
subtotal = 0
for item in st.session_state.invoice_items:
    line_total = item['qty'] * item['price']
    subtotal += line_total
    items_data.append({
        'ref': item['ref'],
        'desc': item['desc'],
        'qty': item['qty'],
        'price': item['price'],
        'total': line_total
    })

vat_amount = subtotal * (vat_rate / 100)
grand_total = subtotal + vat_amount

with tc2:
    pay_mode = st.text_input("Mode of Payment*", "Bank Transfer")
with tc3:
    words = st.text_input("Total Amount in words*", "")

st.markdown(f"### Summary: LKR {format_currency(grand_total)}")

if st.button("🚀 Generate PDF Invoice"):
    data = {
        'invoice_date': inv_date.strftime("%m/%d/%Y"),
        'supplier_tin': s_tin,
        'supplier_name': s_name,
        'supplier_address': s_addr,
        'supplier_phone': s_phone,
        'invoice_no': inv_no,
        'purchaser_tin': p_tin,
        'purchaser_name': p_name,
        'purchaser_address': p_addr,
        'purchaser_phone': p_phone,
        'supply_date': sup_date.strftime("%m/%d/%Y"),
        'supply_place': sup_place,
        'additional_info': add_info
    }
    
    totals = {
        'subtotal': subtotal,
        'vat_rate': vat_rate,
        'vat_amount': vat_amount,
        'grand_total': grand_total,
        'total_in_words': words,
        'payment_mode': pay_mode
    }
    
    pdf = InvoicePDF()
    pdf.add_page()
    pdf.draw_info_blocks(data)
    pdf.draw_table(items_data, totals)
    
    # fpdf2 output('S') returns bytes/bytearray directly in newer versions
    pdf_output = pdf.output(dest='S')
    if isinstance(pdf_output, str):
        pdf_output = pdf_output.encode('latin-1')
        
    b64 = base64.b64encode(pdf_output).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="Invoice_{inv_no}.pdf">Download PDF Invoice</a>'
    st.markdown(href, unsafe_allow_html=True)
    st.success("Invoice generated successfully! Click the link above to download.")
