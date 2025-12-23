import streamlit as st
import pandas as pd
import os
import time
import altair as alt
from datetime import datetime

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

FILE_NAME = "vote_data_v2.csv"

# --- 3. 定義功能函式 ---

def render_voting_page():
    """ 顯示投票介面 """
    query_params = st.query_params
    project_name = query_params.get("project", "預設專案")

    st.header(f"📝 評分表決：{project_name}")
    st.markdown("請針對各項目給予 **0 ~ 100** 分 (每 5 分為一個級距)。")
    st.info("💡 系統會自動採計您的**最新一次**評分 (同姓名覆蓋)。")

    voter_name = st.text_input("您的姓名 (評審)", placeholder="例如：王醫師")
    
    user_scores = {}
    current_total_score = 0
    
    for category, criteria_list in RUBRIC.items():
        st.subheader(category)
        for criterion, weight in criteria_list:
            score = st.slider(
                f"{criterion}", 
                min_value=0, 
                max_value=100, 
                value=70, 
                step=5,
                key=criterion,
                help=f"滿分權重: {weight} 分"
            )
            weighted_score = (score / 100) * weight
            user_scores[criterion] = weighted_score
            current_total_score += weighted_score

    st.divider()
    
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

    feedback = st.text_area("💬 意見回饋 / 備註 (選填)", placeholder="請輸入您對此案的具體建議...")

    if st.button("🚀 確認提交評分", type="primary", use_container_width=True):
        if not voter_name:
            st.error("❌ 請輸入您的姓名後再提交！")
        else:
            vote_record = {
                "Project": project_name, 
                "Voter": voter_name,
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            for k, v in user_scores.items():
                vote_record[k] = v
            vote_record["Total Score"] = current_total_score
            vote_record["Feedback"] = feedback
            
            df_new = pd.DataFrame([vote_record])
            
            try:
                if not os.path.exists(FILE_NAME):
                    df_new.to_csv(FILE_NAME, index=False)
                else:
                    df_new.to_csv(FILE_NAME, mode='a', header=False, index=False)
                st.success(f"✅ {voter_name} 的評分已送出！(專案：{project_name})")
                st.balloons()
                time.sleep(2)
            except Exception as e:
                st.error(f"寫入失敗，請重試: {e}")

def render_dashboard_page():
    """ 顯示大螢幕儀表板 """
    # 顯示最後更新時間，確保畫面有在動
    st.markdown(f"<div style='text-align: right; color: gray; font-size: 12px;'>最後更新: {datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)
    st.title("📊 新光醫院 AI 軟體評估 - 決策看板")
    
    # --- 側邊欄 ---
    with st.sidebar:
        st.header("⚙️ 控制台")
        st.subheader("📁 當前顯示專案")
        # 這裡輸入什麼，大螢幕就顯示什麼
        project_name = st.text_input("專案名稱", value="專案 A")
        
        st.divider()
        default_url = "https://shinkong-ai-vote.streamlit.app" 
        base_url = st.text_input("App 主網址", value=default_url)
        
        import urllib.parse
        safe_project_name = urllib.parse.quote(project_name)
        vote_link = f"{base_url}/?page=vote&project={safe_project_name}"
        
        st.divider()
        if st.button("🔄 手動刷新"):
            st.rerun()

    # --- Dashboard 主畫面 ---
    col_qr, col_info = st.columns([1, 4])
    with col_qr:
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={vote_link}"
        st.image(qr_url, caption=f"掃碼評分：{project_name}")
    with col_info:
        st.info(f"💡 目前正在進行 **【{project_name}】** 的評分")
        st.markdown(f"**投票連結：** `{vote_link}`")

    st.divider()

    # --- 讀取資料 ---
    df_all = pd.DataFrame()
    if os.path.exists(FILE_NAME):
        try:
            df_all = pd.read_csv(FILE_NAME)
            # 欄位補全防呆
            if "Project" not in df_all.columns: df_all["Project"] = "預設專案"
            if "Timestamp" not in df_all.columns: df_all["Timestamp"] = "2024-01-01 00:00:00"
        except:
            pass # 讀取失敗可能是正在寫入，略過本次刷新

    # --- 第一部分：當前專案分析 ---
    if not df_all.empty:
        # 篩選當前專案
        df_project = df_all[df_all["Project"] == project_name].copy()
        
        if not df_project.empty:
            # 取最新一筆 (覆蓋邏輯)
            df_clean = df_project.sort_values("Timestamp").drop_duplicates(subset=["Voter"], keep="last")
            
            # KPI
            avg = df_clean["Total Score"].mean()
            c1, c2, c3 = st.columns(3)
            c1.metric("📥 已投票人數", f"{len(df_clean)} 人")
            c2.metric("🏆 平均總分", f"{avg:.1f}")
            
            final_result = "推薦引進 (Recommend)" if avg >= 75 else "修正後推薦 (Conditional)" if avg >= 60 else "不推薦 (Reject)"
            final_color = "green" if avg >= 75 else "orange" if avg >= 60 else "red"
            c3.markdown(f"**目前綜合決策：**")
            c3.markdown(f":{final_color}[## {final_result}]")
            
            st.divider()

            # 圓餅圖
            st.subheader("🗳️ 投票結果分布")
            def classify_score(s):
                if s >= 75: return "推薦引進"
                elif s >= 60: return "修正後推薦"
                else: return "不推薦"
            
            df_clean["Status"] = df_clean["Total Score"].apply(classify_score)
            status_counts = df_clean["Status"].value_counts().reset_index()
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

            # 橫向長條圖 (細項)
            st.subheader("📈 各構面達成率細項")
            cat_data = []
            for cat, criteria in RUBRIC.items():
                total_w = sum(w for c, w in criteria)
                cols = [c for c, w in criteria]
                if all(c in df_clean.columns for c in cols):
                    actual = df_clean[cols].sum(axis=1).mean()
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
            text_chart = bar_chart.mark_text(align='left', baseline='middle', dx=3, fontSize=14).encode(text='達成率 (%)')
            st.altair_chart(bar_chart + text_chart, use_container_width=True)

            # 詳細與下載
            st.divider()
            with st.expander("📂 查看與下載詳細數據", expanded=False):
                st.markdown(f"### 【{project_name}】最終採計結果")
                st.dataframe(df_clean)
                csv = df_clean.to_csv(index=False).encode('utf-8-sig')
                st.download_button(label="📥 下載 Excel", data=csv, file_name=f'{project_name}_result.csv', mime='text/csv')

        else:
            st.warning(f"專案【{project_name}】目前沒有資料。")
            
    else:
        st.warning("目前尚無任何投票資料。")

    # --- 第二部分：歷史專案總覽 (反查功能) ---
    st.divider()
    st.markdown("### 🗂️ 歷史專案總覽 (所有已存檔紀錄)")
    
    if not df_all.empty and "Project" in df_all.columns:
        # 製作總表：顯示每個專案有多少人投、平均幾分
        # 先做去重處理，確保統計的是有效票數
        df_all_clean = df_all.sort_values("Timestamp").drop_duplicates(subset=["Project", "Voter"], keep="last")
        
        history_summary = df_all_clean.groupby("Project").agg(
            有效票數=('Voter', 'count'),
            平均總分=('Total Score', 'mean'),
            最後更新時間=('Timestamp', 'max')
        ).reset_index()
        
        # 格式化小數點
        history_summary["平均總分"] = history_summary["平均總分"].round(1)
        
        st.dataframe(history_summary, use_container_width=True)
        st.caption("💡 提示：若要在上方儀表板顯示特定專案，請將該專案名稱複製到左側側邊欄的「專案名稱」欄位中。")

        # 全域下載按鈕
        with st.expander("📥 下載所有專案完整原始檔"):
            csv_all = df_all.to_csv(index=False).encode('utf-8-sig')
            st.download_button(label="下載完整備份 (All Projects)", data=csv_all, file_name='all_votes_backup.csv', mime='text/csv')

    # 強制自動刷新 (每 5 秒)
    time.sleep(5)
    st.rerun()

# --- 4. 路由控制 ---
query_params = st.query_params
page = query_params.get("page", "dashboard")

if page == "vote":
    render_voting_page()
else:
    render_dashboard_page()
