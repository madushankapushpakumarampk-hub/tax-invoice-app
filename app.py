import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime
import base64
import json
from num2words import num2words

# --- Page Config ---
st.set_page_config(page_title="SL Tax Invoice Generator Pro", layout="wide")

# --- Helper Functions ---
def get_month_abbr(date_obj):
    return date_obj.strftime("%b").upper()

def format_currency(value):
    return f"{value:,.2f}"

def convert_to_words(amount):
    try:
        # Convert to words in English
        words = num2words(amount, lang='en').replace(',', '').replace('-', ' ')
        return f"Rupees {words.title()} Only"
    except:
        return ""

class InvoicePDF(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 14)
        title = "TAX INVOICE"
        w = self.get_string_width(title) + 10
        self.set_x((210 - w) / 2)
        self.cell(w, 10, title, border=1, align="C", ln=1)
        self.ln(5)

    def draw_info_blocks(self, data):
        self.set_font("helvetica", "", 10)
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
        
        w_ref, w_desc, w_qty, w_price, w_amt = 25, 75, 20, 30, 40
        
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
            
        if len(items) < 5:
            for _ in range(5 - len(items)):
                self.set_x(margin)
                for w in [w_ref, w_desc, w_qty, w_price, w_amt]:
                    self.cell(w, 8, "", border=1)
                self.ln()

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
        self.set_font("helvetica", "", 9)
        self.cell(total_label_w + w_amt, 8, f"Total Amount in words:* {totals['total_in_words']}", border=1, ln=1)
        
        self.ln(2)
        self.set_x(margin)
        pay_info = f"Mode of Payment:* {totals['payment_mode']}"
        if totals['bank_details']:
            pay_info += f" ({totals['bank_details']})"
        self.cell(total_label_w + w_amt, 8, pay_info, border=1, ln=1)

# --- App UI ---
st.title("🇱🇰 SL Tax Invoice Generator Pro")

# --- Profile Management ---
st.sidebar.header("User Profile")
profile_file = st.sidebar.file_uploader("Upload Saved Profile (.json)", type=["json"])

# Default Values
initial_data = {
    "s_name": "Your Company Name",
    "s_tin": "123456789",
    "s_addr": "No. 123, Galle Road, Colombo 03",
    "s_phone": "011-2345678",
    "bank_name": "",
    "acc_no": "",
    "branch": ""
}

if profile_file:
    try:
        uploaded_data = json.load(profile_file)
        initial_data.update(uploaded_data)
        st.sidebar.success("Profile Loaded!")
    except:
        st.sidebar.error("Invalid Profile File")

# --- App Layout ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Supplier Details")
    s_name = st.text_input("Supplier's Name", initial_data["s_name"])
    s_tin = st.text_input("Supplier's TIN", initial_data["s_tin"])
    s_addr = st.text_area("Supplier's Address", initial_data["s_addr"])
    s_phone = st.text_input("Supplier's Telephone No.*", initial_data["s_phone"])
    
    st.subheader("Invoice Details")
    inv_date = st.date_input("Date of Invoice", datetime.date.today())
    suggested_no = f"{str(inv_date.year)[2:]}{get_month_abbr(inv_date)}_MAIN_1"
    inv_no = st.text_input("Tax Invoice No.", suggested_no)

with col2:
    st.subheader("Purchaser Details")
    p_name = st.text_input("Purchaser's Name", "")
    p_tin = st.text_input("Purchaser's TIN", "")
    p_addr = st.text_area("Purchaser's Address", "")
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
    with c1: item['ref'] = st.text_input(f"Ref*", item['ref'], key=f"ref_{i}")
    with c2: item['desc'] = st.text_input(f"Description", item['desc'], key=f"desc_{i}")
    with c3: item['qty'] = st.number_input(f"Qty", value=float(item['qty']), step=0.01, format="%.5f", key=f"qty_{i}")
    with c4: item['price'] = st.number_input(f"Unit Price", value=item['price'], step=0.01, key=f"price_{i}")
    with c5:
        st.write("")
        if st.button("🗑️", key=f"remove_{i}"):
            remove_item(i)
            st.rerun()

st.button("➕ Add Item", on_click=add_item)

st.divider()
st.subheader("Totals & Payment")
tc1, tc2 = st.columns(2)

with tc1:
    vat_rate = st.number_input("VAT Rate (%)", value=18.0, step=0.1)
    pay_mode = st.selectbox("Mode of Payment*", ["Bank Transfer", "Cash", "Cheque", "Credit Card", "Online Payment", "Credit"])
    
    bank_details_str = ""
    if pay_mode == "Bank Transfer":
        st.info("Enter Bank Details for Invoice")
        bc1, bc2 = st.columns(2)
        with bc1:
            b_name = st.text_input("Bank Name", initial_data["bank_name"])
            b_branch = st.text_input("Branch", initial_data["branch"])
        with bc2:
            b_acc = st.text_input("Account Number", initial_data["acc_no"])
        bank_details_str = f"{b_name}, Acc: {b_acc}, Branch: {b_branch}"

# Calculations
subtotal = sum(item['qty'] * item['price'] for item in st.session_state.invoice_items)
vat_amount = subtotal * (vat_rate / 100)
grand_total = subtotal + vat_amount
auto_words = convert_to_words(round(grand_total, 2))

with tc2:
    st.markdown(f"### Subtotal: LKR {format_currency(subtotal)}")
    st.markdown(f"### VAT ({vat_rate}%): LKR {format_currency(vat_amount)}")
    st.markdown(f"## Total: LKR {format_currency(grand_total)}")
    words = st.text_input("Total Amount in words*", auto_words)

# --- Sidebar Save Profile ---
st.sidebar.divider()
st.sidebar.subheader("Save Your Details")
if st.sidebar.button("💾 Export Profile"):
    profile_data = {
        "s_name": s_name, "s_tin": s_tin, "s_addr": s_addr, "s_phone": s_phone,
        "bank_name": b_name if pay_mode == "Bank Transfer" else initial_data["bank_name"],
        "acc_no": b_acc if pay_mode == "Bank Transfer" else initial_data["acc_no"],
        "branch": b_branch if pay_mode == "Bank Transfer" else initial_data["branch"]
    }
    b64_profile = base64.b64encode(json.dumps(profile_data).encode()).decode()
    st.sidebar.markdown(f'<a href="data:application/json;base64,{b64_profile}" download="my_invoice_profile.json">Download Profile File</a>', unsafe_allow_html=True)

if st.button("🚀 Generate PDF Invoice"):
    items_data = [{'ref': i['ref'], 'desc': i['desc'], 'qty': i['qty'], 'price': i['price'], 'total': i['qty']*i['price']} for i in st.session_state.invoice_items]
    
    data = {
        'invoice_date': inv_date.strftime("%m/%d/%Y"), 'supplier_tin': s_tin, 'supplier_name': s_name,
        'supplier_address': s_addr, 'supplier_phone': s_phone, 'invoice_no': inv_no,
        'purchaser_tin': p_tin, 'purchaser_name': p_name, 'purchaser_address': p_addr, 'purchaser_phone': p_phone,
        'supply_date': sup_date.strftime("%m/%d/%Y"), 'supply_place': sup_place, 'additional_info': add_info
    }
    
    totals = {
        'subtotal': subtotal, 'vat_rate': vat_rate, 'vat_amount': vat_amount,
        'grand_total': grand_total, 'total_in_words': words, 'payment_mode': pay_mode,
        'bank_details': bank_details_str if pay_mode == "Bank Transfer" else ""
    }
    
    pdf = InvoicePDF()
    pdf.add_page()
    pdf.draw_info_blocks(data)
    pdf.draw_table(items_data, totals)
    
    pdf_output = pdf.output(dest='S')
    if isinstance(pdf_output, str): pdf_output = pdf_output.encode('latin-1')
        
    b64 = base64.b64encode(pdf_output).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="Invoice_{inv_no}.pdf">Download PDF Invoice</a>'
    st.markdown(href, unsafe_allow_html=True)
    st.success("Invoice generated successfully!")
