import streamlit as st
import pandas as pd
import os
import time
import altair as alt
from datetime import datetime
import urllib.parse

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
    # 修正：使用更穩定的方式抓取參數
    try:
        query_params = st.query_params
        # 優先嘗試抓取 project，若無則顯示警示
        project_name = query_params.get("project", None)
    except:
        project_name = None

    # 如果抓不到專案名稱 (代表使用者可能直接開網頁沒掃碼)
    if not project_name:
        st.warning("⚠️ 警告：未偵測到專案名稱，請重新掃描大螢幕上的 QR Code。")
        project_name = st.text_input("或請手動輸入專案名稱：")
        if not project_name:
            st.stop() # 停止執行，直到有名稱為止

    st.markdown(f"### 📝 正在評估：**{project_name}**")
    st.markdown("---")
    st.markdown("請針對各項目給予 **0 ~ 100** 分 (每 5 分為一個級距)。")
    st.caption("💡 系統採計邏輯：若重複提交，將自動覆蓋舊分數 (以最新一次為主)。")

    voter_name = st.text_input("您的姓名 (評審)", placeholder="例如：王醫師")
    
    user_scores = {}
    current_total_score = 0
    
    # 建立評分區塊
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
                "Project": project_name, # 確保寫入的是抓到的專案名
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
                st.success(f"✅ {voter_name} 的評分已送出！")
                st.info(f"歸檔專案：{project_name}")
                st.balloons()
                time.sleep(2)
            except Exception as e:
                st.error(f"寫入失敗，請重試: {e}")

def get_existing_projects():
    """ 從 CSV 讀取已存在的專案列表 """
    if os.path.exists(FILE_NAME):
        try:
            df = pd.read_csv(FILE_NAME)
            if "Project" in df.columns:
                # 取得唯一值並轉為列表，過濾掉 nan
                projects = df["Project"].dropna().unique().tolist()
                return sorted(projects)
        except:
            return []
    return []

def render_dashboard_page():
    """ 顯示大螢幕儀表板 """
    
    # 初始化 Session State (用來記住現在選的是哪個專案)
    if "current_project" not in st.session_state:
        st.session_state["current_project"] = "新光醫院 AI 評估案 (預設)"

    # --- 側邊欄：專案管理中心 ---
    with st.sidebar:
        st.header("⚙️ 專案管理控制台")
        
        # 1. 取得現有專案列表
        existing_projects = get_existing_projects()
        
        # 2. 專案選擇模式
        tab1, tab2 = st.tabs(["📂 選擇舊專案", "➕ 新增專案"])
        
        with tab1:
            if existing_projects:
                selected_proj = st.selectbox(
                    "請選擇要顯示的專案：", 
                    existing_projects,
                    index=0 if existing_projects else None
                )
                if selected_proj:
                    st.session_state["current_project"] = selected_proj
            else:
                st.caption("目前尚無任何專案紀錄。")

        with tab2:
            new_proj_name = st.text_input("輸入新專案名稱：", placeholder="例如：胸腔 X 光 AI")
            if st.button("建立並切換"):
                if new_proj_name:
                    st.session_state["current_project"] = new_proj_name
                    st.success(f"已切換至新專案：{new_proj_name}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("請輸入名稱")

        st.divider()
        st.info(f"📌 目前鎖定專案：\n\n**{st.session_state['current_project']}**")
        st.divider()

        # 3. 網址設定
        default_url = "https://shinkong-ai-vote.streamlit.app" 
        base_url = st.text_input("App 主網址", value=default_url)
        
        # 產生帶有 Project 參數的連結 (做 URL 編碼處理特殊字元)
        project_param = urllib.parse.quote(st.session_state["current_project"])
        vote_link = f"{base_url}/?page=vote&project={project_param}"
        
        if st.button("🔄 手動刷新數據"):
            st.rerun()

    # --- Dashboard 主畫面 ---
    
    # 標題區
    st.markdown(f"<div style='text-align: right; color: gray; font-size: 12px;'>最後更新: {datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)
    st.title("📊 新光醫院 AI 軟體評估 - 決策看板")

    current_proj = st.session_state["current_project"]

    # QR Code 與連結區
    col_qr, col_info = st.columns([1, 4])
    with col_qr:
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={vote_link}"
        st.image(qr_url, caption=f"專案：{current_proj}")
    with col_info:
        st.info(f"📢 目前正在進行 **【{current_proj}】** 的評分")
        st.markdown(f"請評審掃描左側 QR Code，連結已包含專案參數。")
        st.code(vote_link)

    st.divider()

    # --- 讀取資料 ---
    df_all = pd.DataFrame()
    if os.path.exists(FILE_NAME):
        try:
            df_all = pd.read_csv(FILE_NAME)
            # 欄位補全
            if "Project" not in df_all.columns: df_all["Project"] = "Default"
            if "Timestamp" not in df_all.columns: df_all["Timestamp"] = "2024-01-01 00:00:00"
        except:
            pass 

    # --- 當前專案分析 ---
    has_data = False
    if not df_all.empty:
        # 篩選
        df_project = df_all[df_all["Project"] == current_proj].copy()
        
        if not df_project.empty:
            has_data = True
            # 取最新 (覆蓋邏輯)
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
                st.markdown(f"### 【{current_proj}】最終採計結果")
                st.dataframe(df_clean)
                csv = df_clean.to_csv(index=False).encode('utf-8-sig')
                st.download_button(label="📥 下載 Excel", data=csv, file_name=f'{current_proj}_result.csv', mime='text/csv')

    if not has_data:
        st.warning(f"專案【{current_proj}】目前尚無資料，請評委掃碼開始投票。")

    # --- 歷史專案列表 (反查功能) ---
    st.divider()
    st.markdown("### 🗂️ 專案資料庫總覽")
    if not df_all.empty and "Project" in df_all.columns:
        df_all_clean = df_all.sort_values("Timestamp").drop_duplicates(subset=["Project", "Voter"], keep="last")
        history_summary = df_all_clean.groupby("Project").agg(
            有效票數=('Voter', 'count'),
            平均總分=('Total Score', 'mean'),
            最後更新時間=('Timestamp', 'max')
        ).reset_index()
        history_summary["平均總分"] = history_summary["平均總分"].round(1)
        st.dataframe(history_summary, use_container_width=True)

        with st.expander("📥 下載所有專案原始檔"):
            csv_all = df_all.to_csv(index=False).encode('utf-8-sig')
            st.download_button(label="下載完整備份 (All Projects)", data=csv_all, file_name='all_votes_backup.csv', mime='text/csv')

    time.sleep(5)
    st.rerun()

# --- 4. 路由控制 ---
query_params = st.query_params
page = query_params.get("page", "dashboard")

if page == "vote":
    render_voting_page()
else:
    render_dashboard_page()
