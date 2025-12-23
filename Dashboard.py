import streamlit as st
import pandas as pd
import os
import time
import altair as alt # 引入繪圖庫以製作更清楚的圖表

# --- 1. 頁面設定 ---
st.set_page_config(page_title="新光醫院 AI 軟體評估", layout="wide")

# --- 2. 評分標準定義 ---
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

# --- 3. 定義功能函式 ---

def render_voting_page():
    """ 顯示投票介面 (手機端優化) """
    st.header("📝 AI 軟體評估表決")
    st.markdown("請針對各項目給予 **1 (最低) ~ 5 (最高)** 分。")
    st.info("💡 下方分數會隨著您的調整即時更新。")

    voter_name = st.text_input("您的姓名 (評審)", placeholder="例如：王醫師")
    
    # 用來暫存使用者的選擇
    user_scores = {}
    current_total_score = 0
    
    # 建立評分區塊 (移除 st.form 以實現即時計算)
    for category, criteria_list in RUBRIC.items():
        st.subheader(category)
        for criterion, weight in criteria_list:
            # 1~5分，預設3分
            score = st.slider(
                f"{criterion}", 
                min_value=1, 
                max_value=5, 
                value=3, 
                key=criterion,
                help=f"權重: {weight}%"
            )
            
            # 計算邏輯：(分數 x 20) = 百分比分數
            # 加權得分 = (百分比分數 / 100) * 權重
            # 簡化公式： (score * 20 / 100) * weight = (score / 5) * weight
            weighted_score = (score / 5) * weight
            user_scores[criterion] = weighted_score
            current_total_score += weighted_score

    st.divider()
    
    # === 新增功能：即時顯示目前總分 ===
    st.markdown("### 🏆 您目前的評分總計")
    
    # 根據分數變色
    score_color = "red"
    if current_total_score >= 75: score_color = "green"
    elif current_total_score >= 60: score_color = "orange"
    
    st.markdown(f"""
    <div style="font-size: 40px; font-weight: bold; color: {score_color};">
        {current_total_score:.1f} / 100 分
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()

    # === 新增功能：意見回饋 ===
    feedback = st.text_area("💬 意見回饋 / 備註 (選填)", placeholder="請輸入您對此案的具體建議...")

    # 提交按鈕
    if st.button("🚀 確認提交評分", type="primary", use_container_width=True):
        if not voter_name:
            st.error("❌ 請輸入您的姓名後再提交！")
        else:
            vote_record = {"Voter": voter_name}
            # 將剛才計算好的加權分數存入
            for k, v in user_scores.items():
                vote_record[k] = v
            
            vote_record["Total Score"] = current_total_score
            vote_record["Feedback"] = feedback # 存入回饋
            
            df_new = pd.DataFrame([vote_record])
            
            # 處理檔案寫入
            if not os.path.exists(FILE_NAME):
                df_new.to_csv(FILE_NAME, index=False)
            else:
                # 確保舊檔案有 Feedback 欄位，避免報錯
                try:
                    df_old = pd.read_csv(FILE_NAME)
                    if "Feedback" not in df_old.columns:
                        df_old["Feedback"] = ""
                        df_old.to_csv(FILE_NAME, index=False)
                except:
                    pass
                df_new.to_csv(FILE_NAME, mode='a', header=False, index=False)
                
            st.success("✅ 評分已送出！感謝您的參與。")
            st.balloons()
            time.sleep(2)


def render_dashboard_page():
    """ 顯示大螢幕儀表板 (視覺優化版) """
    st.title("📊 新光醫院 AI 軟體評估 - 決策看板")
    
    # 側邊欄控制
    with st.sidebar:
        st.header("⚙️ 控制台")
        default_url = "https://shinkong-ai-vote.streamlit.app" 
        base_url = st.text_input("確認 App 主網址", value=default_url)
        vote_link = f"{base_url}/?page=vote"
        
        st.divider()
        if st.button("🔄 刷新數據"):
            st.rerun()
        if st.button("⚠️ 清除所有數據"):
            if os.path.exists(FILE_NAME):
                os.remove(FILE_NAME)
                st.success("已清除！")
                time.sleep(1)
                st.rerun()

    # QR Code 區塊
    col_qr, col_info = st.columns([1, 4])
    with col_qr:
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={vote_link}"
        st.image(qr_url, caption="掃碼投票")
    with col_info:
        st.info("💡 請評審掃描左側 QR Code 進入評分頁面")
        st.markdown(f"**投票連結：** `{vote_link}`")

    st.divider()

    # 數據顯示
    if os.path.exists(FILE_NAME):
        try:
            df = pd.read_csv(FILE_NAME)
            if not df.empty:
                # 1. 關鍵指標 KPI
                avg = df["Total Score"].mean()
                c1, c2, c3 = st.columns(3)
                c1.metric("📥 已投票人數", f"{len(df)} 人")
                c2.metric("🏆 平均總分", f"{avg:.1f}")
                
                result = "推薦引進 (Pass)" if avg >= 75 else "修正後推薦 (Conditional)" if avg >= 60 else "不推薦 (Reject)"
                color = "green" if avg >= 75 else "orange" if avg >= 60 else "red"
                c3.markdown(f"**最終建議：**")
                c3.markdown(f":{color}[## {result}]")
                
                st.divider()

                # 2. 圖表優化：橫向長條圖 + 大字體
                st.subheader("📈 各構面達成率分析")
                
                # 資料處理
                cat_data = []
                for cat, criteria in RUBRIC.items():
                    total_w = sum(w for c, w in criteria)
                    cols = [c for c, w in criteria]
                    if all(c in df.columns for c in cols):
                        actual = df[cols].sum(axis=1).mean()
                        pct = (actual / total_w) * 100
                        # 縮短名稱以免佔用太多空間
                        short_name = cat.split(" ")[0] + " " + cat.split(" ")[1] 
                        cat_data.append({"構面": short_name, "達成率 (%)": round(pct, 1)})
                
                chart_df = pd.DataFrame(cat_data)
                
                # 使用 Altair 繪製高客製化圖表
                base = alt.Chart(chart_df).encode(
                    x=alt.X('達成率 (%)', scale=alt.Scale(domain=[0, 100]), title="達成率 (%)"),
                    y=alt.Y('構面', sort=None, title="", axis=alt.Axis(labelFontSize=15, titleFontSize=16)), # 設定字體大小
                    tooltip=['構面', '達成率 (%)']
                )

                bar = base.mark_bar(height=40).encode(
                    color=alt.Color('達成率 (%)', scale=alt.Scale(scheme='blues'), legend=None)
                )

                text = base.mark_text(
                    align='left',
                    baseline='middle',
                    dx=3,
                    fontSize=16  # 數據標籤字體大小
                ).encode(
                    text='達成率 (%)'
                )

                final_chart = (bar + text).properties(height=350) # 圖表高度
                
                st.altair_chart(final_chart, use_container_width=True)

                # 3. 意見回饋區 (新增)
                st.subheader("💬 評委意見回饋")
                if "Feedback" in df.columns:
                    # 過濾掉空白的回饋
                    feedbacks = df[df["Feedback"].notna() & (df["Feedback"] != "")][["Voter", "Feedback"]]
                    if not feedbacks.empty:
                        for index, row in feedbacks.iterrows():
                            st.info(f"**{row['Voter']}:** {row['Feedback']}")
                    else:
                        st.caption("目前尚無文字回饋。")

                # 4. 詳細資料表
                with st.expander("查看詳細評分數據"):
                    st.dataframe(df)

                time.sleep(5) # 自動刷新間隔
                st.rerun()
            else:
                st.warning("尚無投票資料...")
                time.sleep(3)
                st.rerun()
        except Exception as e:
            # 容錯處理 (避免讀取衝突)
            time.sleep(1)
            st.rerun()
    else:
        st.warning("等待投票中...")
        time.sleep(3)
        st.rerun()

# --- 4. 路由控制 ---
query_params = st.query_params
page = query_params.get("page", "dashboard")

if page == "vote":
    render_voting_page()
else:
    render_dashboard_page()
