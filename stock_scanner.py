import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Thai Stock SMA Scanner", layout="wide")

# รายชื่อหุ้น Group A และ Group B
GROUP_A = ["SCC.BK", "AOT.BK", "GULF.BK", "TOP.BK", "ADVANC.BK", "PTT.BK", 
           "PTTGC.BK", "PTTEP.BK", "KBANK.BK", "BBL.BK", "SCB.BK"]

GROUP_B = ["TTB.BK", "KTB.BK", "TISCO.BK", "KKP.BK", "TCAP.BK", "BDMS.BK", 
           "CPALL.BK", "CPN.BK", "WHA.BK", "AMATA.BK", "DIF.BK", "3BBIF.BK", 
           "TFFIF.BK", "WHART.BK", "FTREIT.BK", "MC.BK", "TTW.BK", "LH.BK", "AP.BK"]

@st.cache_data(ttl=1800)
def fetch_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        # ดึงราคาย้อนหลัง 2 ปีเพื่อให้ได้วันทำการเกิน 200 วันชัวร์ๆ
        df = stock.history(period="2y")
        
        if df.empty or len(df) < 200:
            return None, f"{ticker}: ข้อมูลไม่ครบ 200 วัน"
            
        # คำนวณ SMA
        df['SMA_46'] = df['Close'].rolling(window=46).mean()
        df['SMA_67'] = df['Close'].rolling(window=67).mean()
        df['SMA_200'] = df['Close'].rolling(window=200).mean()
        
        latest = df.iloc[-1]
        price = latest['Close']
        sma46 = latest['SMA_46']
        sma67 = latest['SMA_67']
        sma200 = latest['SMA_200']
        
        if pd.isna(sma200) or pd.isna(sma46) or pd.isna(sma67):
            return None, f"{ticker}: คำนวณ SMA ไม่สำเร็จ"

        # คำนวณ Dividend Yield ย้อนหลัง 1 ปี (TTM) จากประวัติปันผลจริง (ไม่ใช้ stock.info เพื่อป้องกันโดนยี่ห้อบล็อก)
        dividend_yield_pct = 0.0
        try:
            divs = stock.dividends
            if not divs.empty:
                divs.index = divs.index.tz_localize(None) # ปรับ timezone
                one_year_ago = datetime.now() - timedelta(days=365)
                ttm_div = divs[divs.index >= one_year_ago].sum()
                if price > 0:
                    dividend_yield_pct = (ttm_div / price) * 100
        except Exception:
            dividend_yield_pct = 0.0

        # จัดโซนตาม SMA
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
        }, None
        
    except Exception as e:
        return None, f"{ticker}: {str(e)}"

# --- หน้าตา Web App ---
st.title("📈 Thai Stock Scanner: SMA & Dividend > 5%")
st.markdown("แสกนหุ้น Group A และ B ค้นหาจุดเข้าซื้อตามลอจิก **ย่อตัวใกล้เส้น 200 วัน** หรือ **เริ่มฟื้นตัว**")

group_choice = st.radio("เลือกกลุ่มหุ้นที่ต้องการแสกน:", ("Group A", "Group B", "ทั้งหมด (A + B)"))

if st.button("🚀 เริ่มแสกนหุ้น"):
    if group_choice == "Group A":
        tickers_to_scan = GROUP_A
    elif group_choice == "Group B":
        tickers_to_scan = GROUP_B
    else:
        tickers_to_scan = GROUP_A + GROUP_B
        
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
        
        st.subheader("📊 ข้อมูลหุ้นทั้งหมดที่แสกนได้")
        st.dataframe(df_results, use_container_width=True)
        
        st.subheader("🎯 หุ้นเข้าเกณฑ์ซื้อ (Yield > 5% และอยู่ในโซนเหลือง/ครีม)")
        target_stocks = df_results[
            (df_results['Yield (%)'] >= 5.0) & 
            (df_results['Zone'].str.contains("เหลือง|ครีม"))
        ]
        
        if not target_stocks.empty:
            st.success("พบหุ้นที่เข้าเกณฑ์น่าสนใจวันนี้!")
            st.dataframe(target_stocks.reset_index(drop=True), use_container_width=True)
        else:
            st.info("วันนี้ยังไม่มีหุ้นตัวไหนเข้าเกณฑ์ (ปันผล > 5% และอยู่ในโซนเหลือง/ครีม)")
            
    if errors:
        with st.expander("⚠️ รายการหุ้นที่ไม่สามารถดึงข้อมูลได้"):
            for err_msg in errors:
                st.write(err_msg)
