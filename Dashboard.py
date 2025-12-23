import streamlit as st
import pandas as pd
import os
import time
import altair as alt

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
    """ 顯示投票介面 """
    st.header("📝 AI 軟體評估表決")
    st.markdown("請針對各項目給予 **0 ~ 100** 分 (每 5 分為一個級距)。")
    st.info("💡 若需修改分數，請使用**相同姓名**重新提交即可覆蓋舊資料。")

    voter_name = st.text_input("您的姓名 (評審)", placeholder="例如：王醫師")
    
    # 用來暫存使用者的選擇
    user_scores = {}
    current_total_score = 0
    
    # 建立評分區塊
    for category, criteria_list in RUBRIC.items():
        st.subheader(category)
        for criterion, weight in criteria_list:
            # 0-100分，間隔為 5
            score = st.slider(
                f"{criterion}", 
                min_value=0, 
                max_value=100, 
                value=70, 
                step=5,
                key=criterion,
                help=f"滿分權重: {weight} 分"
            )
            
            # 計算邏輯：(原始分數 / 100) * 權重
            weighted_score = (score / 100) * weight
            user_scores[criterion] = weighted_score
            current_total_score += weighted_score

    st.divider()
    
    # 即時顯示目前總分
    st.markdown("### 🏆 您目前的評分總計")
    
    score_color = "red"
    if current_total_score >= 75: score_color = "green"
    elif current_total_score >= 60: score_color = "orange"
    
    st.markdown(f"""
    <div style="font-size: 40px; font-weight: bold; color: {score_color};">
        {current_total_score:.1f} / 100 分
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()

    # 意見回饋
    feedback = st.text_area("💬 意見回饋 / 備註 (選填)", placeholder="請輸入您對此案的具體建議...")

    # 提交按鈕
    if st.button("🚀 確認提交評分", type="primary", use_container_width=True):
        if not voter_name:
            st.error("❌ 請輸入您的姓名後再提交！")
        else:
            # --- 覆蓋機制 ---
            vote_record = {"Voter": voter_name}
            for k, v in user_scores.items():
                vote_record[k] = v
            
            vote_record["Total Score"] = current_total_score
            vote_record["Feedback"] = feedback
            
            df_new = pd.DataFrame([vote_record])
            
            # 讀取並覆蓋
            if os.path.exists(FILE_NAME):
                try:
                    df_old = pd.read_csv(FILE_NAME)
                    # 刪除該名字舊的資料 (如果存在)
                    df_old = df_old[df_old["Voter"] != voter_name]
                    # 合併新資料
                    df_final = pd.concat([df_old, df_new], ignore_index=True)
                    df_final.to_csv(FILE_NAME, index=False)
                except Exception as e:
                    st.error(f"存檔時發生錯誤，請重試: {e}")
            else:
                df_new.to_csv(FILE_NAME, index=False)
                
            st.success(f"✅ {voter_name} 的評分已更新/送出！")
            st.balloons()
            time.sleep(2)


def render_dashboard_page():
    """ 顯示大螢幕儀表板 """
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
                
                final_result = "推薦引進 (Recommend)" if avg >= 75 else "修正後推薦 (Conditional)" if avg >= 60 else "不推薦 (Reject)"
                final_color = "green" if avg >= 75 else "orange" if avg >= 60 else "red"
                c3.markdown(f"**目前綜合決策：**")
                c3.markdown(f":{final_color}[## {final_result}]")
                
                st.divider()

                # 2. 投票分布圓餅圖
                st.subheader("🗳️ 投票結果分布")
                
                def classify_score(s):
                    if s >= 75: return "推薦引進"
                    elif s >= 60: return "修正後推薦"
                    else: return "不推薦"
                
                df["Status"] = df["Total Score"].apply(classify_score)
                status_counts = df["Status"].value_counts().reset_index()
                status_counts.columns = ["決策類別", "票數"]
                
                domain = ["推薦引進", "修正後推薦", "不推薦"]
                range_ = ["#4CAF50", "#FF9800", "#F44336"]

                base = alt.Chart(status_counts).encode(
                    theta=alt.Theta("票數", stack=True),
                    color=alt.Color("決策類別", scale=alt.Scale(domain=domain, range=range_))
                )

                pie = base.mark_arc(outerRadius=120)
                text = base.mark_text(radius=140).encode(
                    text=alt.Text("票數", format=".0f"),
                    order=alt.Order("決策類別"),
                    color=alt.value("black"),
                    size=alt.value(20)
                )
                st.altair_chart(pie + text, use_container_width=True)

                # 3. 各構面詳細長條圖 (Original Bar Chart)
                st.subheader("📈 各構面達成率細項")
                cat_data = []
                for cat, criteria in RUBRIC.items():
                    total_w = sum(w for c, w in criteria)
                    cols = [c for c, w in criteria]
                    if all(c in df.columns for c in cols):
                        actual = df[cols].sum(axis=1).mean()
                        pct = (actual / total_w) * 100
                        short_name = cat.split(" ")[0] 
                        cat_data.append({"構面": short_name, "達成率 (%)": round(pct, 1)})
                
                chart_df = pd.DataFrame(cat_data)
                
                bar_chart = alt.Chart(chart_df).mark_bar().encode(
                    x=alt.X('達成率 (%)', scale=alt.Scale(domain=[0, 100])),
                    y=alt.Y('構面', sort=None, axis=alt.Axis(labelFontSize=14)),
                    color=alt.Color('達成率 (%)', scale=alt.Scale(scheme='blues'), legend=None),
                    tooltip=['構面', '達成率 (%)']
                ).properties(height=300)

                text_chart = bar_chart.mark_text(
                    align='left', baseline='middle', dx=3, fontSize=14
                ).encode(
                    text='達成率 (%)'
                )
                
                st.altair_chart(bar_chart + text_chart, use_container_width=True)

                # 4. 意見回饋區
                st.subheader("💬 評委意見回饋")
                if "Feedback" in df.columns:
                    feedbacks = df[df["Feedback"].notna() & (df["Feedback"] != "")][["Voter", "Feedback"]]
                    if not feedbacks.empty:
                        for index, row in feedbacks.iterrows():
                            st.info(f"**{row['Voter']}:** {row['Feedback']}")
                    else:
                        st.caption("目前尚無文字回饋。")

                # (已移除底部的詳細資料表 st.dataframe)

                time.sleep(5) # 自動刷新
                st.rerun()
            else:
                st.warning("尚無投票資料...")
                time.sleep(3)
                st.rerun()
        except Exception as e:
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
