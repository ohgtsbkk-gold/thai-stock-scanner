import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

st.set_page_config(page_title="Thai Stock SMA Scanner", layout="wide")

# 1. กำหนดรายชื่อหุ้น Group A และ Group B (เติม .BK สำหรับหุ้นไทย)
GROUP_A = ["SCC.BK", "AOT.BK", "GULF.BK", "TOP.BK", "ADVANC.BK", "PTT.BK", 
           "PTTGC.BK", "PTTEP.BK", "KBANK.BK", "BBL.BK", "SCB.BK"]

# คัดมาเฉพาะตัวหลักๆ ใน Group B (สามารถพิมพ์เพิ่มใน List นี้ได้เลยครับ)
GROUP_B = ["TTB.BK", "KTB.BK", "TISCO.BK", "KKP.BK", "TCAP.BK", "BDMS.BK", 
           "CPALL.BK", "CPN.BK", "WHA.BK", "AMATA.BK", "DIF.BK", "3BBIF.BK", 
           "TFFIF.BK", "WHART.BK", "FTREIT.BK", "MC.BK", "TTW.BK", "LH.BK", "AP.BK"]

@st.cache_data(ttl=3600) # Cache ข้อมูลไว้ 1 ชั่วโมงจะได้ไม่ต้องโหลดใหม่ทุกครั้ง
def fetch_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        # ดึงข้อมูลย้อนหลัง 1 ปีเพื่อคำนวณ SMA 200
        df = stock.history(period="1y")
        
        if df.empty or len(df) < 200:
            return None
            
        # คำนวณ SMA
        df['SMA_46'] = df['Close'].rolling(window=46).mean()
        df['SMA_67'] = df['Close'].rolling(window=67).mean()
        df['SMA_200'] = df['Close'].rolling(window=200).mean()
        
        # ดึงข้อมูลแถวล่าสุด
        latest = df.iloc[-1]
        
        # ดึงข้อมูลปันผล (Yield)
        info = stock.info
        dividend_yield = info.get('dividendYield', 0)
        if dividend_yield is None:
            dividend_yield = 0
        dividend_yield_pct = dividend_yield * 100
        
        # จัดโซนตามลอจิก SMA
        price = latest['Close']
        sma46 = latest['SMA_46']
        sma67 = latest['SMA_67']
        sma200 = latest['SMA_200']
        
        # จำลองลอจิกจากภาพ
        if price > sma46 and price > sma67 and price > sma200:
            zone = "🔴 ส้มเข้ม (ขาขึ้นแข็งแกร่ง)"
        elif price > sma200 and (price < sma46 or price < sma67):
            zone = "🟡 เหลือง (ย่อตัวบนขาขึ้น - น่าซื้อ)"
        elif price < sma200 and (price > sma46 or price > sma67):
            zone = "⚪ ครีม (รีบาวด์ - เริ่มฟื้นตัว)"
        else:
            zone = "⚫ ดำ (ขาลงชัดเจน)"
            
        return {
            "Ticker": ticker.replace(".BK", ""),
            "Price": round(price, 2),
            "SMA 46": round(sma46, 2),
            "SMA 67": round(sma67, 2),
            "SMA 200": round(sma200, 2),
            "Yield (%)": round(dividend_yield_pct, 2),
            "Zone": zone
        }
    except Exception as e:
        return None

# --- หน้าตา Web App ---
st.title("📈 Thai Stock Scanner: SMA & Dividend > 5%")
st.markdown("แสกนหุ้น Group A และ B ค้นหาจุดเข้าซื้อตามลอจิก **ย่อตัวใกล้เส้น 200 วัน** หรือ **เริ่มฟื้นตัว** พร้อมปันผลสูง")

group_choice = st.radio("เลือกกลุ่มหุ้นที่ต้องการแสกน:", ("Group A", "Group B", "ทั้งหมด (A + B)"))

if st.button("🚀 เริ่มแสกนหุ้น"):
    if group_choice == "Group A":
        tickers_to_scan = GROUP_A
    elif group_choice == "Group B":
        tickers_to_scan = GROUP_B
    else:
        tickers_to_scan = GROUP_A + GROUP_B
        
    progress_text = "กำลังดึงข้อมูล... กรุณารอสักครู่"
    my_bar = st.progress(0, text=progress_text)
    
    results = []
    total = len(tickers_to_scan)
    
    for i, ticker in enumerate(tickers_to_scan):
        data = fetch_stock_data(ticker)
        if data:
            results.append(data)
        my_bar.progress((i + 1) / total, text=f"กำลังประมวลผล: {ticker}")
        
    my_bar.empty() # ลบหลอดโหลดเมื่อเสร็จ
    
    if results:
        df_results = pd.DataFrame(results)
        
        st.subheader("📊 ข้อมูลหุ้นทั้งหมดที่แสกนได้")
        st.dataframe(df_results, use_container_width=True)
        
        st.subheader("🎯 หุ้นเข้าเกณฑ์ซื้อ (Yield > 5% และอยู่ในโซนเหลือง/ครีม)")
        # คัดกรองหุ้นตามเงื่อนไขที่กำหนด
        target_stocks = df_results[
            (df_results['Yield (%)'] >= 5.0) & 
            (df_results['Zone'].str.contains("เหลือง|ครีม"))
        ]
        
        if not target_stocks.empty:
            st.success("พบหุ้นที่เข้าเกณฑ์น่าสนใจวันนี้!")
            st.dataframe(target_stocks.reset_index(drop=True), use_container_width=True)
        else:
            st.warning("วันนี้ยังไม่มีหุ้นตัวไหนเข้าเกณฑ์ (ปันผล > 5% และย่อตัวใกล้ SMA 200)")
            
st.markdown("---")
st.caption("⚠️ **ข้อควรระวัง:** ข้อมูล Dividend Yield จาก Yahoo Finance อาจมีการอัปเดตล่าช้า หรือไม่ตรงกับของไทยเป๊ะๆ แนะนำให้ตรวจสอบตัวเลขปันผลจริงกับเว็บ settrade.com อีกครั้งก่อนตัดสินใจลงทุนครับ")
