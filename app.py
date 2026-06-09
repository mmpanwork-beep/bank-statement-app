import streamlit as st
import pandas as pd
import pdfplumber
import re
import io

# 1. ตั้งค่าหน้าเพจ
st.set_page_config(page_title="Bank Statement Analyzer", page_icon="💖", layout="wide")

# 2. 🎨 CSS ตกแต่ง
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600&display=swap');
    .stApp { font-family: 'Kanit', sans-serif !important; }
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
    .stButton>button { border-radius: 30px !important; font-weight: 500 !important; transition: all 0.3s ease !important; }
    .stButton>button:hover { transform: scale(1.02); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
</style>
""", unsafe_allow_html=True)

def reset_app():
    for key in st.session_state.keys():
        del st.session_state[key]
    st.rerun()

# ==========================================
# ส่วนหน้าจอเว็บ (UI Frontend) 💖
# ==========================================
col_title, col_reset = st.columns([4, 1])
with col_title:
    st.title("🏦✨ ระบบวิเคราะห์ Bank Statement 🐻 (v4.0)")
    st.markdown("ผู้ช่วยสรุปยอด กรองข้อมูล และส่งออก Excel (รองรับ กสิกรไทย, กรุงไทย และ ออมสิน 100%)")
with col_reset:
    st.write("") 
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
                st.info("⚙️ กำหนดการตั้งค่าไฟล์ PDF")
                
                col_bank, col_pw = st.columns(2)
                with col_bank:
                    # 💡 อัปเดต: เพิ่มธนาคารออมสินลงในตัวเลือก
                    bank_choice = st.selectbox(
                        "🏦 เลือกธนาคารของไฟล์นี้:", 
                        [
                            "🟢 ธนาคารกสิกรไทย (KBank)", 
                            "🟢 ธนาคารกรุงไทย (Krungthai)",
                            "🟢 ธนาคารออมสิน (GSB)"
                        ] 
                    )
                with col_pw:
                    pdf_password = st.text_input("🔒 รหัสผ่านเปิด PDF (ถ้ามี):", type="password")
                
                st.write("")
                if st.button("🚀 เสกแดชบอร์ดเลย! 🪄", use_container_width=True, type="primary"):
                    with st.spinner(f"น้องหมีกำลังสแกนพิกัดแกน X แกน Y เพื่อหาข้อมูลของ {bank_choice.split(' ')[1]}... 🐻⏳"):
                        try:
                            parsed_data = []
                            last_seen_date = None 
                            opening_balance = 0.0
                            raw_text_debug = "" 
                            current_txn = None
                            
                            with pdfplumber.open(uploaded_file, password=pdf_password if pdf_password else None) as pdf:
                                for page in pdf.pages:
                                    
                                    # ระบบสแกนพิกัด (Coordinate-based Scanning)
                                    words = page.extract_words(x_tolerance=2, y_tolerance=3, keep_blank_chars=False)
                                    if not words: continue
                                    
                                    # จัดกลุ่มคำที่อยู่บรรทัดเดียวกัน (พิกัดแกน Y ตรงกัน)
                                    lines_dict = {}
                                    for w in words:
                                        top = round(w['top'] / 4) * 4 # เผื่อความคลาดเคลื่อน 4 pixel
                                        if top not in lines_dict: lines_dict[top] = []
                                        lines_dict[top].append(w)
                                        
                                    for top in sorted(lines_dict.keys()):
                                        # เรียงคำในบรรทัดจากซ้ายไปขวา (แกน X)
                                        row_words = sorted(lines_dict[top], key=lambda w: w['x0'])
                                        line = " ".join([w['text'] for w in row_words]).strip()
                                        
                                        if not line: continue
                                        raw_text_debug += line + "\n"
                                        
                                        # จับยอดยกมา
                                        if "ยอดยกมา" in line or "B/F" in line:
                                            m = re.findall(r'(?<!\d)(?:\d{1,3}(?:,\d{3})*|\d+)\.\d{2}', line)
                                            if m: opening_balance = float(m[-1].replace(',', ''))
                                            continue
                                        
                                        # 💡 อัปเดต: แยกคำสั่งข้ามหัวตาราง/ท้ายกระดาษตามธนาคาร
                                        if bank_choice == "🟢 ธนาคารกสิกรไทย (KBank)":
                                            skip_keywords = ['รวมถอนเงิน', 'รวมฝากเงิน', 'ยอดยกไป', 'C/F', 'เลขที่อ้างอิง', 'รอบระหว่างวันที่', 'PAGE/OF', 'หน้าที่', 'รายการเดินบัญชี', 'วันที่ เวลา', 'รายละเอียด']
                                        elif bank_choice == "🟢 ธนาคารกรุงไทย (Krungthai)":
                                            skip_keywords = ['รายการถอนทั้งหมด', 'รายการฝากทั้งหมด', 'ยอดยกไป', 'C/F', 'PAGE/OF', 'หน้าที่', 'วันที่ เวลา', 'รายละเอียด']
                                        else: # ออมสิน (GSB)
                                            skip_keywords = ['ยอดยกไป', 'รวมรายการถอน', 'รวมรายการฝาก', 'หน้าที่', 'วันที่พิมพ์', 'ชื่อบัญชี', 'สาขา', 'เลขที่บัญชี', 'รายการถอน', 'รายการฝาก', 'ยอดคงเหลือ']
                                            
                                        if any(word in line for word in skip_keywords):
                                            continue
                                            
                                        # 1. หาวันที่ และ ตัวเลขทางการเงิน
                                        date_match = re.search(r'(\d{2}\s*[-/]\s*\d{2}\s*[-/]\s*(?:\d{4}|\d{2}))', line)
                                        money_matches = re.findall(r'(?<!\d)(?:\d{1,3}(?:,\d{3})*|\d+)\.\d{2}', line)
                                        
                                        # 2. จำแนกสถานะบรรทัด
                                        is_txn = False
                                        if date_match and len(money_matches) >= 1: is_txn = True
                                        elif not date_match and last_seen_date and len(money_matches) >= 2: is_txn = True
                                        elif not date_match and last_seen_date and any(w in line for w in ['ค่าธรรมเนียม', 'ภาษี', 'Fee', 'Tax']) and len(money_matches) >= 1: is_txn = True
                                        
                                        if is_txn:
                                            # --- เป็นรายการหลัก ---
                                            if current_txn:
                                                parsed_data.append(current_txn) # เซฟรายการก่อนหน้า
                                                
                                            date_str = last_seen_date
                                            if date_match:
                                                date_str = date_match.group(1).replace('-', '/').replace(' ', '')
                                                last_seen_date = date_str
                                            
                                            time_match = re.search(r'(\d{2}[:.]\d{2})', line)
                                            time_str = time_match.group(1).replace('.', ':') if time_match else '-'
                                            
                                            money_vals = [float(x.replace(',', '')) for x in money_matches]
                                            amt = money_vals[-2] if len(money_vals) >= 2 else money_vals[0]
                                            balance = money_vals[-1] if len(money_vals) >= 2 else 0.0
                                                
                                            desc = line
                                            if date_match: desc = desc.replace(date_match.group(0), '', 1)
                                            if time_match: desc = desc.replace(time_match.group(0), '', 1)
                                            for m in money_matches: desc = desc.replace(m, '', 1)
                                            desc = re.sub(r'\s+', ' ', desc).strip()
                                            desc = re.sub(r'\d+$', '', desc).strip() # ลบเลขสาขา
                                            
                                            # 💡 อัปเดต: การแยกฝาก/ถอนเบื้องต้น (ตามธนาคาร)
                                            deposit, withdraw = 0.0, 0.0
                                            if amt > 0:
                                                if bank_choice == "🟢 ธนาคารกรุงไทย (Krungthai)":
                                                    in_keywords = ['เข้า', 'ฝาก', 'รับ', 'fr ', 'BSD', 'Deposit', 'IORDT', 'MORISD', 'NMIPSD', 'เงินเดือน', 'คืน']
                                                elif bank_choice == "🟢 ธนาคารกสิกรไทย (KBank)": 
                                                    in_keywords = ['รับโอน', 'ฝาก', 'รับเงิน', 'ดอกเบี้ย', 'เงินเข้า', 'คืนเงิน']
                                                else: # ออมสิน (GSB)
                                                    in_keywords = ['ฝาก', 'รับโอน', 'โอนเข้า', 'ดอกเบี้ย', 'เงินเข้า', 'คืน', 'SD', 'DEP']
                                                    
                                                if any(w in desc for w in in_keywords): deposit = amt
                                                else: withdraw = amt
                                                    
                                            current_txn = {
                                                'Date': date_str, 'Time': time_str, 'Description': desc,
                                                'Deposit': deposit, 'Withdrawal': withdraw, 'Balance': balance, 'RawAmt': amt
                                            }
                                            
                                        elif not date_match and last_seen_date and current_txn:
                                            # --- เป็นส่วนขยายบรรทัดของรายการก่อนหน้า ---
                                            if money_matches:
                                                parsed_data.append(current_txn)
                                                amt = float(money_matches[0].replace(',', ''))
                                                balance = float(money_matches[-1].replace(',', '')) if len(money_matches) > 1 else 0.0
                                                desc = line
                                                for m in money_matches: desc = desc.replace(m, '', 1)
                                                current_txn = {
                                                    'Date': last_seen_date, 'Time': '-', 'Description': re.sub(r'\s+', ' ', desc).strip(),
                                                    'Deposit': 0.0, 'Withdrawal': amt, 'Balance': balance, 'RawAmt': amt
                                                }
                                            else:
                                                time_match = re.search(r'(\d{2}[:.]\d{2})', line)
                                                if time_match and current_txn['Time'] == '-':
                                                    current_txn['Time'] = time_match.group(1).replace('.', ':')
                                                    line = line.replace(time_match.group(0), '', 1)
                                                current_txn['Description'] += " " + re.sub(r'\s+', ' ', line).strip()
                                                
                                    if current_txn:
                                        parsed_data.append(current_txn)
                                        current_txn = None
                                        
                            if parsed_data:
                                # พิสูจน์ยอดด้วยสมการคณิตศาสตร์ 100% (กันเหนียวให้ทุกธนาคาร)
                                for i in range(len(parsed_data)):
                                    txn = parsed_data[i]
                                    prev_balance = parsed_data[i-1]['Balance'] if i > 0 else opening_balance
                                    
                                    if txn['Balance'] > 0 and prev_balance > 0:
                                        diff = round(txn['Balance'] - prev_balance, 2)
                                        raw_amt = round(txn['RawAmt'], 2)
                                        
                                        if raw_amt > 0:
                                            if abs(diff - raw_amt) < 0.02: 
                                                txn['Deposit'], txn['Withdrawal'] = raw_amt, 0.0
                                            elif abs(diff - (-raw_amt)) < 0.02: 
                                                txn['Withdrawal'], txn['Deposit'] = raw_amt, 0.0

                                work_df = pd.DataFrame(parsed_data)
                                work_df['Parsed_Date'] = pd.to_datetime(work_df['Date'], dayfirst=True, errors='coerce')
                                work_df = work_df.dropna(subset=['Parsed_Date'])
                                work_df['Month_Year'] = work_df['Parsed_Date'].dt.strftime('%m/%Y')
                                
                                st.session_state['processed_df'] = work_df
                                st.rerun()
                            else:
                                st.error("❌ ไม่พบข้อมูลรายการจ้า (ไฟล์อาจมีโครงสร้างซับซ้อนมาก)")
                                with st.expander("👀 คลิกดูข้อความดิบที่ AI มองเห็น (เช็คว่ามีตัวหนังสือถูกดึงมาไหม)"):
                                    st.text(raw_text_debug[:5000] if raw_text_debug else "ไม่พบตัวหนังสือใดๆ (ไฟล์อาจเป็นรูปภาพสแกน)")
                        except Exception as e:
                            st.error(f"❌ เกิดข้อผิดพลาด: {e}")
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
