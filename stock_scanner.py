import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Thai Stock SMA 5-Zone Scanner", layout="wide")

# ==============================================================================
# รายชื่อหุ้น Group A, Group B และ Group C (SET50)
# ==============================================================================

# Group A: หุ้นใหญ่ คูเมืองแข็งแกร่ง (ตามผัง + BH)
GROUP_A = [
    "SCC.BK", "AOT.BK", "GULF.BK", "TOP.BK", "ADVANC.BK", "PTT.BK", 
    "PTTGC.BK", "PTTEP.BK", "KBANK.BK", "BBL.BK", "SCB.BK", "BH.BK"
]

# Group B: หุ้นปันผล/เติบโตตามผังต้นฉบับ + กองทรัสต์/หุ้นเสริมคุณภาพ
GROUP_B = [
    "KTB.BK", "TLI.BK", "TCAP.BK", "TTB.BK", "KKP.BK", "TIDLOR.BK", "DIF.BK", 
    "TU.BK", "TOA.BK", "BTG.BK", "CRC.BK", "GPSC.BK", "AMATA.BK", "DIF.BK", 
    "BAY.BK", "EGCO.BK", "AWC.BK", "CENTEL.BK", "BGRIM.BK", "KTC.BK", "CPN.BK", 
    "STECON.BK", "CPALL.BK", "BEM.BK", "TISCO.BK", "SCGP.BK", "KCE.BK", "RATCH.BK", 
    "BDMS.BK", "CPF.BK", "OSP.BK", "AEONTS.BK", "CBG.BK", "TACC.BK", "HMPRO.BK", 
    "3BBIF.BK", "TASCO.BK", "MAJOR.BK", "VGI.BK", "BJC.BK", "TFFIF.BK", "MINT.BK", 
    "STA.BK", "DELTA.BK", "TRUE.BK", "HANA.BK", "WHA.BK", "CK.BK", "IVL.BK", 
    "SAWAD.BK", "AP.BK", "CPAXT.BK", "LH.BK", "OR.BK", "BTS.BK",
    "WHART.BK", "FTREIT.BK", "TTW.BK", "MC.BK", "CPNREIT.BK", "IMPACT.BK", "SIRI.BK"
]

# Group C: หุ้นในดัชนี SET50
GROUP_C = [
    "ADVANC.BK", "AOT.BK", "AWC.BK", "BANPU.BK", "BBL.BK", "BCP.BK", "BDMS.BK", 
    "BEM.BK", "BGRIM.BK", "BH.BK", "BJC.BK", "CBG.BK", "CPALL.BK", "CPAXT.BK", 
    "CPN.BK", "CRC.BK", "DELTA.BK", "EGCO.BK", "GLOBAL.BK", "GPSC.BK", "GULF.BK", 
    "HMPRO.BK", "INTUCH.BK", "IVL.BK", "KBANK.BK", "KKP.BK", "KTB.BK", "KTC.BK", 
    "MINT.BK", "MTC.BK", "OR.BK", "OSP.BK", "PTT.BK", "PTTEP.BK", "PTTGC.BK", 
    "RATCH.BK", "SAWAD.BK", "SCB.BK", "SCC.BK", "SCGP.BK", "SIRI.BK", "TCAP.BK", 
    "TISCO.BK", "TLI.BK", "TOP.BK", "TRUE.BK", "TTB.BK", "TU.BK", "WHA.BK"
]

@st.cache_data(ttl=1800)
def fetch_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="5y")
        df = df.dropna(subset=['Close'])
        
        if len(df) < 200:
            return None, f"{ticker}: ข้อมูลไม่ครบ 200 วัน"
            
        df['SMA_46'] = df['Close'].rolling(window=46, min_periods=40).mean()
        df['SMA_67'] = df['Close'].rolling(window=67, min_periods=60).mean()
        df['SMA_200'] = df['Close'].rolling(window=200, min_periods=180).mean()
        
        latest = df.iloc[-1]
        price = latest['Close']
        sma46 = latest['SMA_46']
        sma67 = latest['SMA_67']
        sma200 = latest['SMA_200']
        
        if pd.isna(sma200) or pd.isna(sma46) or pd.isna(sma67):
            return None, f"{ticker}: ค่า SMA เป็น NaN"

        # คำนวณ Dividend Yield (TTM)
        dividend_yield_pct = 0.0
        try:
            divs = stock.dividends
            if not divs.empty:
                divs.index = divs.index.tz_localize(None)
                one_year_ago = datetime.now() - timedelta(days=365)
                ttm_div = divs[divs.index >= one_year_ago].sum()
                if price > 0:
                    dividend_yield_pct = (ttm_div / price) * 100
        except Exception:
            dividend_yield_pct = 0.0

        # ลอจิกแยก 5 โซน + Action คำแนะนำ
        sma_mid_max = max(sma46, sma67)
        sma_mid_min = min(sma46, sma67)

        if price >= sma200 and price >= sma_mid_max:
            zone = "🔴 ส้มเข้ม"
            action = "✋ แพงไป / ควรรอ (อย่าเพิ่งเข้าซื้อ)"
        elif price >= sma200 and price < sma_mid_max:
            mid_point = (sma200 + sma_mid_max) / 2
            if price >= mid_point:
                zone = "🟠 ส้มอ่อน"
                action = "⏳ รอก่อน / แรงขายยังไม่สุด"
            else:
                zone = "🟡 เหลือง"
                action = "🎯 เข้าซื้อไม้ที่ 1 (จุดซื้อดีที่สุด)"
        elif price < sma200 and price >= sma_mid_min:
            zone = "⚪ ครีม"
            action = "🛒 เข้าซื้อไม้ที่ 2 (ไม้ถัวเฉลี่ย)"
        else:
            zone = "⚫ ดำ"
            action = "🚫 ห้ามซื้อเด็ดขาด / ขาลงชัดเจน"
            
        return {
            "Ticker": ticker.replace(".BK", ""),
            "Price": round(price, 2),
            "SMA 46": round(sma46, 2),
            "SMA 67": round(sma67, 2),
            "SMA 200": round(sma200, 2),
            "Yield (%)": round(dividend_yield_pct, 2),
            "Zone": zone,
            "คำแนะนำ (Action)": action
        }, None
        
    except Exception as e:
        return None, f"{ticker}: ({str(e)})"

# --- UI Interface ---
st.title("📈 Thai Stock Scanner: SMA 5-Zone & Dividend > 5%")

with st.expander("📖 คำแนะนำ Action ในแต่ละโซนสี (กดเพื่อเปิด/ปิด)", expanded=True):
    st.markdown("""
    * **🔴 ส้มเข้ม:** **แพงไป / ควรรอ** — หุ้นอยู่บนเทรนด์ขาขึ้นแรง ยังไม่ควรไล่ราคา
    * **🟠 ส้มอ่อน:** **รอก่อน / แรงขายยังไม่สุด** — เริ่มย่อตัวลงมา แต่ยังไม่ถึงจุดที่คุ้มความเสี่ยง
    * **🟡 เหลือง:** **เข้าซื้อไม้ที่ 1 (คุ้มที่สุด)** — ย่อลงมาใกล้เส้น SMA 200 วัน ได้ทั้ง Yield สูงและเงินต้นปลอดภัย
    * **⚪ ครีม:** **เข้าซื้อไม้ที่ 2 (ไม้ถัวเฉลี่ย)** — หลุดเส้น 200 วันลงมาแต่เริ่มตั้งฐานได้ ใช้ถัวต้นทุน
    * **⚫ ดำ:** **ห้ามซื้อเด็ดขาด** — ขาลงชัดเจน ปันผลสูงแค่ไหนก็เสี่ยงเงินต้นติดลบหนัก
    """)

# ปรับเพิ่มตัวเลือก Group C (SET50)
group_choice = st.radio(
    "เลือกกลุ่มหุ้นที่ต้องการสแกน:", 
    ("Group A", "Group B", "Group C (SET50)", "ทั้งหมด (A + B + C)")
)

if st.button("🚀 เริ่มสแกนหุ้น"):
    if group_choice == "Group A":
        tickers_to_scan = GROUP_A
    elif group_choice == "Group B":
        tickers_to_scan = GROUP_B
    elif group_choice == "Group C (SET50)":
        tickers_to_scan = GROUP_C
    else:
        # รวมหุ้นทุกหมวด โดยใช้ set() เพื่อตัดตัวซ้ำออก
        tickers_to_scan = list(set(GROUP_A + GROUP_B + GROUP_C))
        
    my_bar = st.progress(0, text="กำลังดึงข้อมูล... กรุณารอสักครู่")
    
    results = []
    errors = []
    total = len(tickers_to_scan)
    
    for i, ticker in enumerate(tickers_to_scan):
        data, err = fetch_stock_data(ticker)
        if data:
            results.append(data)
        if err:
            errors.append(err)
            
        my_bar.progress((i + 1) / total, text=f"กำลังประมวลผล: {ticker}")
        
    my_bar.empty()
    
    if results:
        df_results = pd.DataFrame(results)
        
        st.subheader("🎯 หุ้นน่าซื้อวันนี้ (Yield > 5% และอยู่ในโซนเหลือง/ครีม)")
        target_stocks = df_results[
            (df_results['Yield (%)'] >= 5.0) & 
            (df_results['Zone'].str.contains("เหลือง|ครีม"))
        ]
        
        if not target_stocks.empty:
            st.success("พบหุ้นที่เข้าเกณฑ์น่าซื้อวันนี้!")
            st.dataframe(target_stocks.reset_index(drop=True), use_container_width=True)
        else:
            st.info("วันนี้ยังไม่มีหุ้นตัวไหนเข้าเกณฑ์ (ปันผล > 5% และอยู่ในโซนเหลือง/ครีม)")

        st.subheader("📊 ข้อมูลหุ้นทั้งหมดที่สแกนได้")
        st.dataframe(df_results, use_container_width=True)
            
    if errors:
        with st.expander("⚠️ รายการหุ้นที่มีปัญหา / ข้อมูลไม่พอคำนวณ"):
            for err_msg in errors:
                st.write(err_msg)
