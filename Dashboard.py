import streamlit as st
import pandas as pd
import os
import time

# 設定頁面為寬版模式
st.set_page_config(page_title="新光醫院 AI 評估 - 即時結果", layout="wide")

# --- 定義評分標準與權重 ---
RUBRIC = {
    "一、臨床卓越與安全性 (35%)": [
        ("1. 模型準確度與臨床一致性", 14.0),
        ("2. 異常值偵測與風險警示", 10.5),
        ("3. 病患安全防護機制", 10.5)
    ],
    "二、系統整合與資安 (25%)": [
        ("5. 院內系統整合度", 8.75),
        ("6. 資安合規性", 8.75),
        ("7. 系統維運與更新機制", 7.5)
    ],
    "三、負責性 AI 與治理 (25%)": [
        ("9. 可解釋性與透明度", 8.75),
        ("10. 人類監督機制", 8.75),
        ("12. 模型生命週期管理", 7.5)
    ],
    "四、營運效益與創新價值 (15%)": [
        ("13. 成本效益分析", 7.5),
        ("15. 病患體驗與衛教應用", 4.5),
        ("16. ESG 與永續指標", 3.0)
    ]
}

FILE_NAME = "vote_data.csv"

# --- 側邊欄：設定與控制 ---
with st.sidebar:
    st.header("⚙️ 設定與控制")
    
    # [關鍵功能] 輸入部屬後的網址以產生正確 QR Code
    st.info("👇 請在此貼上您部屬後的 App 網址")
    base_url = st.text_input("App 主網址", value="https://ai-voting-app.streamlit.app")
    
    st.divider()
    
    if st.button("🔄 手動刷新"):
        st.rerun()
    
    # 清除數據功能
    if st.button("⚠️ 清除所有數據 (開啟新一輪)"):
        if os.path.exists(FILE_NAME):
            os.remove(FILE_NAME)
            st.success("數據已清除！")
            time.sleep(1)
            st.rerun()

# --- 主畫面內容 ---
st.title("📊 新光醫院 AI 軟體評估 - 即時決策看板")

# === QR Code 顯示區 ===
vote_url = f"{base_url}/Voting"
st.info("💡 請評審掃描下方 QR Code 或輸入網址進入評分頁面")

col_qr, col_info = st.columns([1, 4])

with col_qr:
    # 使用 QR Server API 產生圖片
    qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={vote_url}"
    st.image(qr_api_url, caption="📱 掃碼評分")

with col_info:
    st.markdown("### 🔗 評分網址：")
    st.code(vote_url)
    st.caption("若 QR Code 掃描後無法進入，請確認左側側邊欄的網址是否正確。")

st.divider()

# === 結果顯示區 ===
if os.path.exists(FILE_NAME):
    try:
        df = pd.read_csv(FILE_NAME)
        
        if not df.empty:
            # 1. 關鍵指標 (KPIs)
            avg_score = df["Total Score"].mean()
            count = len(df)
            
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("📥 已投票人數", f"{count} 人")
            kpi2.metric("🏆 平均總分", f"{avg_score:.1f} / 100")
            
            # 決策燈號
            if avg_score >= 75:
                result_text = "推薦引進 (Recommend)"
                result_color = "green"
            elif avg_score >= 60:
                result_text = "修正後推薦 (Conditional)"
                result_color = "orange"
            else:
                result_text = "不推薦 (Reject)"
                result_color = "red"
            
            kpi3.markdown(f"**最終建議**")
            kpi3.markdown(f":{result_color}[## {result_text}]")
            
            # 2. 圖表分析
            st.subheader("📈 構面得分分析")
            
            # 計算各構面得分率
            category_scores = {}
            for category, criteria_list in RUBRIC.items():
                cat_total_weight = sum([w for c, w in criteria_list])
                cols = [c for c, w in criteria_list]
                # 該構面實際得分總和的平均
                if all(col in df.columns for col in cols):
                    actual_score_sum = df[cols].sum(axis=1).mean()
                    score_pct = (actual_score_sum / cat_total_weight) * 100
                    category_short_name = category.split(" ")[0] 
                    category_scores[category_short_name] = score_pct

            if category_scores:
                chart_df = pd.DataFrame({
                    "評估構面": list(category_scores.keys()),
                    "達成率 (%)": list(category_scores.values())
                })
                st.bar_chart(chart_df, x="評估構面", y="達成率 (%)", color="#2E86C1")

            # 3. 詳細明細
            with st.expander("查看詳細評審投票紀錄"):
                st.dataframe(df.style.format(precision=1))
            
            # 自動刷新機制 (有資料時每 5 秒刷新)
            time.sleep(5)
            st.rerun()

        else:
            st.warning("尚無資料，等待評審投票中...")
            time.sleep(5)
            st.rerun()
    except Exception as e:
        st.error(f"讀取資料時發生錯誤 (可能是寫入衝突)，將自動重試。錯誤: {e}")
        time.sleep(2)
        st.rerun()
else:
    st.warning("尚無資料，等待評審投票中...")
    time.sleep(5)
    st.rerun()
