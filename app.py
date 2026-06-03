import streamlit as st
import pandas as pd
import pdfplumber
import re
import io

# 1. ตั้งค่าหน้าเพจ
st.set_page_config(page_title="Bank Statement Analyzer", page_icon="💖", layout="wide")

# 2. 🎨 แก้ไข CSS ใหม่ (ไม่ให้ไปกวนไอคอน Upload แล้ว)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600&display=swap');
    
    /* บังคับใช้ฟอนต์ Kanit เฉพาะส่วนที่เป็นแอปหลัก ไม่ยุ่งกับไอคอน */
    .stApp { font-family: 'Kanit', sans-serif !important; }
    
    /* ตกแต่งกล่องตัวเลข */
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 2px solid #f0f2f6;
        padding: 20px;
        border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
        transition: transform 0.3s ease;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px);
        border-color: #ffb6c1;
    }
    /* ตกแต่งปุ่ม */
    .stButton>button { border-radius: 30px !important; font-weight: 500 !important; transition: all 0.3s ease !important; }
    .stButton>button:hover { transform: scale(1.02); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
</style>
""", unsafe_allow_html=True)

# ฟังก์ชันสำหรับล้างข้อมูลทั้งหมด
def reset_app():
    for key in st.session_state.keys():
        del st.session_state[key]
    st.rerun()

# ==========================================
# ส่วนหน้าจอเว็บ (UI Frontend) 💖
# ==========================================
col_title, col_reset = st.columns([4, 1])
with col_title:
    st.title("🏦✨ ระบบวิเคราะห์ Bank Statement 🐻")
    st.markdown("ผู้ช่วยสรุปยอด กรองข้อมูล และส่งออก Excel แบบง่ายๆ ฟินๆ ☁️")
with col_reset:
    st.write("") 
    # ปุ่มล้างข้อมูลด้านบน
    if st.button("🗑️ ล้างข้อมูล / อัปโหลดใหม่", use_container_width=True):
        reset_app()

st.divider()

if 'processed_df' not in st.session_state:
    with st.container():
        st.subheader("🐰 1. โยนไฟล์มาได้เลยจ้า (Upload)")
        uploaded_file = st.file_uploader("ลากไฟล์ PDF ของธนาคารมาวางตรงนี้เลย 👇", type=['pdf', 'csv', 'xlsx'])

        if uploaded_file is not None:
            file_ext = uploaded_file.name.split('.')[-1].lower()
            if file_ext == 'pdf':
                st.info("🔒 ไฟล์ PDF ธนาคารมักจะล็อคไว้ ใส่รหัสก่อนน้า (ถ้ามี)")
                col_pw, col_btn = st.columns([3, 1])
                with col_pw:
                    pdf_password = st.text_input("รหัสผ่านเปิด PDF:", type="password")
                with col_btn:
                    st.write(""); st.write("")
                    
                    if st.button("🚀 เสกแดชบอร์ดเลย! 🪄", use_container_width=True, type="primary"):
                        with st.spinner("น้องหมีกำลังควานหาตัวเลขทุกสตางค์ (รวมถึงค่าธรรมเนียมที่ซ่อนอยู่)... 🐻⏳"):
                            try:
                                parsed_data = []
                                last_seen_date = None 
                                
                                with pdfplumber.open(uploaded_file, password=pdf_password if pdf_password else None) as pdf:
                                    for page in pdf.pages:
                                        text = page.extract_text()
                                        if not text: continue
                                        
                                        lines = text.split('\n')
                                        for line in lines:
                                            line = line.strip()
                                            if not line: continue
                                            
                                            if 'หน้า' in line or 'รายการถอนทั้งหมด' in line or 'ยอดยกไป' in line or 'รายการฝากทั้งหมด' in line or 'ยอดยกมา' in line:
                                                continue
                                                
                                            date_match = re.match(r'^(\d{2}/\d{2}/\d{2})', line)
                                            if date_match:
                                                last_seen_date = date_match.group(1)
                                                
                                            money_matches = re.findall(r'(?<!\d)\d{1,3}(?:,\d{3})*\.\d{2}', line)
                                            
                                            is_txn = False
                                            if date_match and len(money_matches) >= 1: is_txn = True
                                            elif not date_match and last_seen_date and len(money_matches) >= 2: is_txn = True
                                            elif not date_match and last_seen_date and "ค่าธรรมเนียม" in line and len(money_matches) >= 1: is_txn = True
                                                
                                            if is_txn:
                                                date_str = last_seen_date
                                                time_match = re.search(r'\b\d{2}[:.]\d{2}\b', line)
                                                time_str = time_match.group(0).replace('.', ':') if time_match else '-'
                                                
                                                money_vals = [float(x.replace(',', '')) for x in money_matches]
                                                amt, balance = 0.0, 0.0
                                                
                                                if len(money_vals) >= 2:
                                                    amt, balance = money_vals[-2], money_vals[-1]
                                                elif len(money_vals) == 1:
                                                    amt, balance = money_vals[0], 0.0
                                                    
                                                desc = line.replace(date_str, '', 1) if date_match else line
                                                if time_match: desc = desc.replace(time_match.group(0), '', 1)
                                                for m in money_matches: desc = desc.replace(m, '', 1)
                                                desc = re.sub(r'\s+\d+$', '', desc) 
                                                desc = re.sub(r'\s+', ' ', desc).strip()
                                                
                                                deposit, withdraw = 0.0, 0.0
                                                if amt > 0:
                                                    if any(w in desc for w in ['เข้า', 'ฝาก', 'รับ', 'fr ', 'BSD', 'Deposit', 'IORDT', 'MORISD', 'NMIPSD', 'เงินเดือน', 'คืน']):
                                                        deposit = amt
                                                    else: withdraw = amt
                                                        
                                                parsed_data.append({
                                                    'Date': date_str, 'Time': time_str, 'Description': desc,
                                                    'Deposit': deposit, 'Withdrawal': withdraw, 'Balance': balance, 'RawAmt': amt
                                                })
                                            else:
                                                if parsed_data:
                                                    time_match = re.match(r'^(\d{2}[:.]\d{2})\b', line)
                                                    if time_match and parsed_data[-1]['Time'] == '-':
                                                        parsed_data[-1]['Time'] = time_match.group(1).replace('.', ':')
                                                        line = line.replace(time_match.group(0), '', 1).strip()
                                                    if line:
                                                        parsed_data[-1]['Description'] += " " + line
                                                        
                                if parsed_data:
                                    for i in range(1, len(parsed_data)):
                                        txn = parsed_data[i]
                                        prev = parsed_data[i-1]
                                        
                                        if txn['Balance'] > 0 and prev['Balance'] > 0:
                                            diff = round(txn['Balance'] - prev['Balance'], 2)
                                            raw_amt = round(txn['RawAmt'], 2)
                                            
                                            if raw_amt > 0:
                                                if abs(diff - raw_amt) < 0.01: 
                                                    txn['Deposit'], txn['Withdrawal'] = raw_amt, 0.0
                                                elif abs(diff - (-raw_amt)) < 0.01: 
                                                    txn['Withdrawal'], txn['Deposit'] = raw_amt, 0.0

                                    work_df = pd.DataFrame(parsed_data)
                                    work_df['Parsed_Date'] = pd.to_datetime(work_df['Date'], format='%d/%m/%y', errors='coerce')
                                    work_df = work_df.dropna(subset=['Parsed_Date'])
                                    work_df['Month_Year'] = work_df['Parsed_Date'].dt.strftime('%m/%Y')
                                    
                                    st.session_state['processed_df'] = work_df
                                    st.rerun()
                                else:
                                    st.error("❌ ไม่พบข้อมูลรายการในไฟล์นี้จ้า")
                            except Exception as e:
                                st.error(f"❌ เกิดข้อผิดพลาด: รหัสผ่านผิด หรือ ไฟล์ซับซ้อนเกินไป ({e})")
            else:
                st.info("💡 กรุณาอัปโหลดไฟล์ PDF ของธนาคารครับ")

# --- 3. แดชบอร์ด ---
if 'processed_df' in st.session_state:
    work_df = st.session_state['processed_df']
    
    st.subheader("📊 2. แดชบอร์ดสรุปข้อมูล (Dashboard) 🐶")
    
    with st.container():
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            month_list = ["ดูทั้งหมดทุกเดือน 🌟"] + sorted(work_df['Month_Year'].unique().tolist())
            selected_month = st.selectbox("📅 กรองตามเดือน/ปี", options=month_list)
        
        with filter_col2:
            search_text = st.text_input("🔍 ค้นหารายละเอียด / ชื่อคนโอน / เลขเช็ค")
            
    filtered_df = work_df.copy()
    if selected_month != "ดูทั้งหมดทุกเดือน 🌟": filtered_df = filtered_df[filtered_df['Month_Year'] == selected_month]
    if search_text: filtered_df = filtered_df[filtered_df['Description'].astype(str).str.contains(search_text, na=False, case=False)]

    total_deposit = filtered_df['Deposit'].sum()
    count_deposit = (filtered_df['Deposit'] > 0).sum()
    total_withdraw = filtered_df['Withdrawal'].sum()
    count_withdraw = (filtered_df['Withdrawal'] > 0).sum()

    st.write("")
    m1, m2 = st.columns(2)
    m1.metric(label="💚 รวมเงินเข้า (Deposit)", value=f"{total_deposit:,.2f} ฿", delta=f"มีรายการเข้า {count_deposit} ครั้ง", delta_color="normal")
    m2.metric(label="❤️ รวมเงินออก (Withdrawal)", value=f"{total_withdraw:,.2f} ฿", delta=f"มีรายการออก {count_withdraw} ครั้ง", delta_color="inverse")
    st.write("")

    st.markdown("##### 📝 รายการเดินบัญชี (เลื่อนดูได้เลยจ้า 👇)")
    
    display_df = filtered_df[['Date', 'Time', 'Description', 'Deposit', 'Withdrawal', 'Balance']].copy()
    display_df.columns = ['วันที่', 'เวลา', 'รายละเอียด', 'เงินเข้า (ฝาก)', 'เงินออก (ถอน)', 'ยอดคงเหลือ']
    
    styled_df = display_df.style.format({"เงินเข้า (ฝาก)": "{:,.2f}", "เงินออก (ถอน)": "{:,.2f}", "ยอดคงเหลือ": "{:,.2f}"})
    st.dataframe(styled_df, use_container_width=True, height=400)

    st.write("")
    
    # ปุ่มดาวน์โหลด Excel และปุ่มล้างข้อมูลด้านล่างสุด
    col_dl, col_rs = st.columns([3, 1])
    
    with col_dl:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            display_df.to_excel(writer, index=False, sheet_name='Statement')
        excel_data = output.getvalue()
        
        st.download_button(
            label="📥 โหลดตารางนี้เป็น Excel ไปใช้งานต่อเลย! 🎉",
            data=excel_data,
            file_name='bank_statement_summary.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            type="primary",
            use_container_width=True
        )
        
    with col_rs:
        if st.button("🗑️ ล้างข้อมูล", use_container_width=True):
            reset_app()