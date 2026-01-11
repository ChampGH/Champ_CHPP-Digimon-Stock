import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import time

# --- ⚙️ CONFIG ---
PAGE_TITLE = "Digimon Card Shop & Stock"
ADMIN_PASSWORD = "1234"  # 🔑 รหัสผ่าน Admin
CARDS_PER_ROW = 5

st.set_page_config(page_title=PAGE_TITLE, layout="wide", page_icon="🦖")

# --- 🛠️ CSS STYLING ---
st.markdown("""
<style>
    .card-container {
        background-color: white; border: 1px solid #ddd;
        border-radius: 10px; padding: 10px; text-align: center;
        margin-bottom: 10px; height: 100%; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .stock-badge {
        background-color: #e3f2fd; color: #1565c0;
        padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: bold;
        margin-bottom: 5px; display: inline-block;
    }
    
    /* Hide Streamlit components */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 🔌 CONNECTION ---
# เชื่อมต่อ Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    """โหลดข้อมูลจากแผ่นแรกสุด (ไม่ต้องระบุชื่อ Sheet)"""
    try:
        # อ่านข้อมูลโดยไม่ระบุ worksheet (มันจะเอาใบแรกสุดเสมอ)
        df = conn.read(ttl=0) 
        
        # ✅ สร้างคอลัมน์ Quantity ถ้ายังไม่มี (กรณีเพิ่ง Import CSV มาใหม่ๆ)
        if 'Quantity' not in df.columns:
            st.toast("⚠️ ไม่พบคอลัมน์ Quantity -> กำลังสร้างใหม่ให้...", icon="🔧")
            df['Quantity'] = 0
            
        # แปลง Data Type ให้ถูกต้อง
        df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0).astype(int)
        df['Code'] = df['Code'].astype(str)
        
        # ตรวจสอบว่ามีคอลัมน์สำคัญไหม
        if 'UID' not in df.columns:
            st.error("❌ ไม่พบคอลัมน์ UID! กรุณาตรวจสอบไฟล์ Google Sheet")
            return pd.DataFrame()
            
        return df
    except Exception as e:
        st.error(f"❌ โหลดข้อมูลไม่ได้: {e}")
        return pd.DataFrame()

def save_data(df):
    """บันทึกข้อมูลกลับลง Google Sheets"""
    try:
        # ใช้การบันทึกแบบไม่ระบุ worksheet (ลงใบแรกสุดเหมือนกัน)
        conn.update(data=df)
        st.toast("บันทึกข้อมูลลง Cloud เรียบร้อย!", icon="☁️")
        time.sleep(1) 
        st.rerun()
    except Exception as e:
        st.error(f"❌ บันทึกไม่สำเร็จ: {e}")

# --- 🛒 CART FUNCTIONS ---
def add_to_cart(card_row, qty_add):
    if 'cart' not in st.session_state: st.session_state.cart = {}
    uid = card_row['UID']
    
    current_in_cart = st.session_state.cart.get(uid, {'qty': 0})['qty']
    # ถ้าไม่มีของในสต็อก ให้ถือว่าเป็น 0
    max_stock = card_row['Quantity'] if card_row['Quantity'] > 0 else 0
    
    if current_in_cart + qty_add <= max_stock:
        st.session_state.cart[uid] = {
            'code': card_row['Code'],
            'name': card_row['Name_JP'],
            'qty': current_in_cart + qty_add,
            'img': card_row.get('Image_URL_JP', ''),
            'art': card_row.get('Art_Type', 'Normal')
        }
        st.toast(f"ใส่ตะกร้า: {card_row['Code']} x{qty_add}", icon="🛒")
    else:
        st.toast(f"⚠️ สินค้าไม่พอ (เหลือ {max_stock})", icon="❌")

def clear_cart():
    st.session_state.cart = {}

# --- 🖥️ MAIN APP ---
def main():
    # Load Data
    if 'data' not in st.session_state:
        st.session_state.data = load_data()
        
    df = st.session_state.data
    if df.empty:
        st.warning("⚠️ ยังไม่มีข้อมูล หรือ เชื่อมต่อไม่ได้")
        if st.button("ลองโหลดใหม่"):
            st.cache_data.clear()
            st.rerun()
        return

    # Refresh Button
    if st.sidebar.button("🔄 รีเฟรชข้อมูล"):
        st.cache_data.clear()
        st.session_state.data = load_data()
        st.rerun()

    # --- 🔐 LOGIN SYSTEM ---
    with st.sidebar:
        st.title("🦖 Digimon Store")
        
        # Toggle Admin Mode
        is_admin = False
        with st.expander("🔐 สำหรับเจ้าของร้าน (Admin)"):
            pwd = st.text_input("รหัสผ่าน Admin", type="password")
            if pwd == ADMIN_PASSWORD:
                is_admin = True
                st.success("Admin Access: GRANTED")
            elif pwd:
                st.error("รหัสผิด")
    
    # --- 🚦 PAGE ROUTING ---
    if is_admin:
        admin_page(df)
    else:
        user_shop_page(df)

# --- 👮‍♂️ ADMIN PAGE (STOCK MANAGER) ---
def admin_page(df):
    st.header("🛠️ จัดการสต็อกสินค้า (Admin Mode)")
    st.info("💡 แก้ไขตัวเลขในตาราง แล้วกดปุ่ม 'บันทึก' ด้านล่างเพื่ออัปเดต Google Sheets")
    
    # Search Filter
    col1, col2 = st.columns([3, 1])
    with col1: search = st.text_input("🔍 ค้นหา (รหัส/ชื่อ)", "")
    with col2: 
        # Extract Sets safely
        try:
            sets = sorted(list(set(df['Code'].str.split('-').str[0].astype(str))))
        except:
            sets = []
        set_filter = st.selectbox("หมวดหมู่", ["All"] + sets)
    
    # Filter Logic
    filtered = df.copy()
    if search:
        filtered = filtered[filtered['Code'].str.contains(search, case=False, na=False) | 
                            filtered['Name_JP'].str.contains(search, case=False, na=False)]
    if set_filter != "All":
        filtered = filtered[filtered['Code'].str.startswith(set_filter)]
    
    # --- 📝 DATA EDITOR ---
    edited_df = st.data_editor(
        filtered[['UID', 'Code', 'Name_JP', 'Art_Type', 'Quantity']],
        column_config={
            "Quantity": st.column_config.NumberColumn("จำนวนคงเหลือ", min_value=0, step=1, format="%d"),
            "UID": st.column_config.TextColumn("System ID", disabled=True),
            "Code": st.column_config.TextColumn("รหัสการ์ด", disabled=True),
        },
        disabled=["UID", "Code", "Name_JP", "Art_Type"],
        use_container_width=True,
        hide_index=True,
        key="editor"
    )
    
    # SAVE BUTTON
    st.markdown("---")
    if st.button("💾 บันทึกการเปลี่ยนแปลงลง Cloud", type="primary", use_container_width=True):
        # Update logic
        changes = edited_df.set_index('UID')['Quantity']
        df.set_index('UID', inplace=True)
        df.update(changes)
        df.reset_index(inplace=True)
        save_data(df)

# --- 🛍️ USER PAGE (SHOPPING) ---
def user_shop_page(df):
    st.subheader("🛒 ค้นหาการ์ด & สั่งซื้อ")
    
    # 🛒 Cart Summary Sidebar
    with st.sidebar:
        st.markdown("---")
        st.subheader("🛍️ ตะกร้าของฉัน")
        if 'cart' not in st.session_state or not st.session_state.cart:
            st.caption("ยังไม่มีสินค้า")
        else:
            total_items = 0
            msg_list = []
            for uid, item in st.session_state.cart.items():
                st.write(f"▪️ **{item['code']}** ({item['art']}) x{item['qty']}")
                msg_list.append(f"{item['code']} ({item['art']}) x{item['qty']}")
                total_items += 1
            
            st.markdown("---")
            if st.button("❌ ล้างตะกร้า"):
                clear_cart()
                st.rerun()
            
            if st.button("✅ สรุปยอดสั่งซื้อ", type="primary"):
                order_msg = "🛒 **รายการสั่งซื้อ**\n" + "\n".join(msg_list) + "\n\nรบกวนเช็คของให้หน่อยครับ!"
                st.code(order_msg, language="text")
                st.success("ก๊อปปี้ข้อความด้านบนส่งให้แอดมินได้เลย!")

    # Search
    search_q = st.text_input("🔍 พิมพ์ชื่อการ์ด หรือ รหัส (เช่น BT1-001)", placeholder="ค้นหาการ์ด...").strip()
    
    # Show Cards
    if search_q:
        results = df[
            df['Code'].str.contains(search_q, case=False, na=False) |
            df['Name_JP'].str.contains(search_q, case=False, na=False)
        ]
        
        # แสดงเฉพาะที่มีของ (Quantity > 0)
        # แต่ถ้าเพิ่งสร้างไฟล์ใหม่ Quantity จะเป็น 0 หมด -> จะหาไม่เจอ
        # ดังนั้น: ถ้าเป็น User ทั่วไป โชว์เฉพาะ > 0
        # แต่ช่วงแรก เราอาจจะอยากเห็นว่าระบบมันเจอการ์ดไหม ให้แสดงหมดไปก่อนก็ได้
        # results = results[results['Quantity'] > 0] 
        
        if results.empty:
            st.warning("ไม่พบสินค้า")
        else:
            st.success(f"เจอ {len(results)} รายการ")
            
            # Grid Layout
            for i in range(0, len(results), CARDS_PER_ROW):
                cols = st.columns(CARDS_PER_ROW)
                batch = results.iloc[i:i+CARDS_PER_ROW]
                
                for idx, (index, row) in enumerate(batch.iterrows()):
                    with cols[idx]:
                        with st.container():
                            # Image
                            img_url = str(row.get('Image_URL_JP', ''))
                            if img_url.startswith('http'):
                                st.image(img_url, use_container_width=True)
                            else:
                                st.markdown("🖼️ No Image")
                            
                            # Info
                            st.markdown(f"**{row['Code']}**")
                            st.caption(f"{row['Name_JP']}")
                            
                            # Stock Badge
                            qty = row['Quantity']
                            if qty > 0:
                                st.markdown(f"<div class='stock-badge'>มี {qty} ใบ</div>", unsafe_allow_html=True)
                                if st.button("➕ ใส่ตะกร้า", key=f"add_{row['UID']}"):
                                    add_to_cart(row, 1)
                            else:
                                st.markdown(f"<span style='color:red; font-size:12px;'>สินค้าหมด</span>", unsafe_allow_html=True)

    else:
        st.info("👈 พิมพ์ค้นหาการ์ดที่ต้องการได้เลยครับ")

if __name__ == "__main__":
    main()