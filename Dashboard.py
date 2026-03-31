import streamlit as st
import pandas as pd
import os
import time
import altair as alt
from datetime import datetime
import urllib.parse

# --- 1. 頁面設定 ---
st.set_page_config(page_title="新光醫院 AI 軟體評估", layout="wide")

# --- 2. 評分標準定義 (保留您原始的權重與結構) ---
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

# --- 3. 輔助函式 ---
def get_existing_projects():
    if os.path.exists(FILE_NAME):
        try:
            df = pd.read_csv(FILE_NAME)
            if "Project" in df.columns:
                projects = df["Project"].dropna().unique().tolist()
                return sorted(projects)
        except:
            return []
    return []

# --- 4. 頁面渲染函式 ---

def render_voting_page():
    """ 投票介面：保留您的姓名輸入、Slider 百分制轉換、以及自動覆蓋舊分數的功能 """
    try:
        query_params = st.query_params
        project_name = query_params.get("project", None)
    except:
        project_name = None

    if not project_name:
        st.warning("⚠️ 警告：未偵測到專案名稱，請重新掃描 QR Code。")
        project_name = st.text_input("或請手動輸入專案名稱：")
        if not project_name:
            st.stop()

    st.markdown(f"### 📝 正在評估：**{project_name}**")
    st.markdown("---")
    st.caption("💡 說明：若重複提交，系統將自動覆蓋您的舊分數 (以最新一次為主)。")

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
    score_color = "green" if current_total_score >= 75 else "orange" if current_total_score >= 60 else "red"
    st.markdown(f'<div style="font-size: 40px; font-weight: bold; color: {score_color};">{current_total_score:.1f} / 100 分</div>', unsafe_allow_html=True)
    
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
                st.success(f"✅ {voter_name} 的評分已送出！")
                st.balloons()
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.error(f"寫入失敗: {e}")

def render_dashboard_page():
    """ 大螢幕看板：保留自動刷新、專案管理、QR Code 生成、以及 CSV 下載功能 """
    
    # Session State 初始化 (保留您的邏輯)
    if "current_project" not in st.session_state: st.session_state["current_project"] = None
    if "project_selector" not in st.session_state: st.session_state["project_selector"] = None
    if "pending_project" not in st.session_state: st.session_state["pending_project"] = None

    # --- 側邊欄 ---
    with st.sidebar:
        st.header("🗂️ 專案管理")
        existing_projects = get_existing_projects()
        
        # 處理 pending (剛建立新專案時的跳轉)
        if st.session_state.get("pending_project"):
            pending = st.session_state["pending_project"]
            st.session_state["current_project"] = pending
            st.session_state["project_selector"] = pending
            st.session_state["pending_project"] = None

        display_options = existing_projects.copy()
        if st.session_state["current_project"] and st.session_state["current_project"] not in display_options:
            display_options.append(st.session_state["current_project"])

        if display_options:
            if st.session_state["project_selector"] not in display_options:
                st.session_state["project_selector"] = st.session_state["current_project"] if st.session_state["current_project"] in display_options else display_options[0]
            
            st.radio("點擊切換專案：", display_options, key="project_selector")
            if st.session_state["current_project"] != st.session_state["project_selector"]:
                st.session_state["current_project"] = st.session_state["project_selector"]
                st.rerun()
        else:
            st.info("尚無專案，請先建立。")

        st.markdown("---")
        st.subheader("➕ 新增專案")
        with st.form("create_project_form"):
            new_proj_name = st.text_input("新專案名稱", placeholder="例如：AI 輔助診斷系統")
            if st.form_submit_button("建立"):
                new_proj_name = (new_proj_name or "").strip()
                if new_proj_name:
                    st.session_state["pending_project"] = new_proj_name
                    st.rerun()

        st.markdown("---")
        auto_refresh = st.toggle("🔄 開啟自動刷新 (Live)", value=True)

        with st.expander("🗑️ 危險區域"):
            if st.button("清除所有資料", type="primary"):
                if os.path.exists(FILE_NAME): os.remove(FILE_NAME)
                st.session_state.clear()
                st.success("已清空！")
                st.rerun()

    # --- Dashboard 主畫面 ---
    last_update = datetime.now().strftime('%H:%M:%S')
    status_text = f"🟢 Live 更新中 ({last_update})" if auto_refresh else "🔴 已暫停更新"
    st.markdown(f"<div style='text-align: right; color: gray; font-size: 12px;'>{status_text}</div>", unsafe_allow_html=True)
    st.title("📊 新光醫院 AI 軟體評估 - 決策看板")

    current_proj = st.session_state["current_project"]
    if not current_proj:
        st.info("👋 請在左側建立或選擇一個專案。")
        if auto_refresh: time.sleep(5); st.rerun()
        return

    # QR Code 生成 (保留您的 logic)
    try:
        default_url = "https://shinkong-ai-vote.streamlit.app"
        safe_proj_param = urllib.parse.quote(str(current_proj))
        vote_link = f"{default_url}/?page=vote&project={safe_proj_param}"
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={urllib.parse.quote(vote_link)}"
    except:
        qr_url = ""; vote_link = ""

    col_qr, col_info = st.columns([1, 4])
    with col_qr:
        if qr_url: st.image(qr_url, caption=f"掃描評分：{current_proj}")
    with col_info:
        st.info(f"📢 目前評估專案：**【{current_proj}】**")
        st.code(vote_link)

    st.divider()

    # --- 讀取與過濾數據 (保留 Clean 採計邏輯) ---
    df_all = pd.read_csv(FILE_NAME) if os.path.exists(FILE_NAME) else pd.DataFrame()
    has_data = False

    if not df_all.empty:
        df_project = df_all[df_all["Project"] == current_proj].copy()
        if not df_project.empty:
            has_data = True
            # Clean: 每位評審僅取最新一筆
            df_clean = df_project.sort_values("Timestamp").drop_duplicates(subset=["Voter"], keep="last")
            df_history = df_project.sort_values("Timestamp", ascending=False)

            # 統計指標
            avg = df_clean["Total Score"].mean()
            c1, c2, c3 = st.columns(3)
            c1.metric("📥 已投票人數", f"{len(df_clean)} 人")
            c2.metric("🏆 平均總分", f"{avg:.1f}")
            
            final_res = "推薦引進" if avg >= 75 else "修正後推薦" if avg >= 60 else "不推薦"
            final_col = "green" if avg >= 75 else "orange" if avg >= 60 else "red"
            c3.markdown(f"**綜合決策：**\n# :{final_col}[{final_res}]")

            st.divider()

            # --- 圖表區 1: 圓餅圖 ---
            st.subheader("🗳️ 投票結果分布")
            df_clean["Status"] = df_clean["Total Score"].apply(lambda s: "推薦引進" if s >= 75 else "修正後推薦" if s >= 60 else "不推薦")
            status_counts = df_clean["Status"].value_counts().reset_index()
            status_counts.columns = ["決策類別", "票數"]
            
            pie = alt.Chart(status_counts).mark_arc(outerRadius=120).encode(
                theta=alt.Theta("票數", stack=True),
                color=alt.Color("決策類別", scale=alt.Scale(domain=["推薦引進", "修正後推薦", "不推薦"], range=["#4CAF50", "#FF9800", "#F44336"])),
                tooltip=["決策類別", "票數"]
            )
            st.altair_chart(pie, use_container_width=True)

            # --- 圖表區 2: 12 個細項達成率 (更新重點：展開細項並標註佔比) ---
            st.subheader("📈 各細項指標達成率與權重佔比")

            item_list = []
            for cat, criteria in RUBRIC.items():
                cat_short = cat.split(" ")[0] # 例如 "一、臨床卓越"
                for criterion, weight in criteria:
                    if criterion in df_clean.columns:
                        avg_item_score = df_clean[criterion].mean()
                        # 達成率計算：(平均實得分數 / 該項滿分權重) * 100
                        achievement_rate = (avg_item_score / weight) * 100
                        item_list.append({
                            "主構面": cat_short,
                            "評估細項": criterion,
                            "達成率 (%)": round(achievement_rate, 1),
                            "滿分權重": weight
                        })

            chart_df = pd.DataFrame(item_list)
            
            # 長條圖
            bar = alt.Chart(chart_df).mark_bar().encode(
                x=alt.X('達成率 (%)', scale=alt.Scale(domain=[0, 100])),
                y=alt.Y('評估細項', sort=None, axis=alt.Axis(labelLimit=400)),
                color=alt.Color('主構面', legend=alt.Legend(orient='bottom')),
                tooltip=['主構面', '評估細項', '達成率 (%)', '滿分權重']
            ).properties(height=500)

            # 數值標籤
            text = bar.mark_text(align='left', baseline='middle', dx=5, fontWeight='bold').encode(
                text='達成率 (%):Q'
            )

            st.altair_chart(bar + text, use_container_width=True)

            # --- 詳細數據區 (保留 Tab 切換與下載功能) ---
            st.divider()
            with st.expander("📂 數據明細與下載"):
                tab1, tab2 = st.tabs(["📊 最終結果 (Clean)", "🕒 完整歷程 (History)"])
                with tab1:
                    st.dataframe(df_clean)
                    st.download_button("📥 下載最終結果", df_clean.to_csv(index=False).encode('utf-8-sig'), f'{current_proj}_final.csv')
                with tab2:
                    st.dataframe(df_history)
                    st.download_button("📥 下載完整歷程", df_history.to_csv(index=False).encode('utf-8-sig'), f'{current_proj}_history.csv')

    if not has_data:
        st.warning(f"專案【{current_proj}】目前尚無資料。")

    if auto_refresh:
        time.sleep(5)
        st.rerun()

# --- 5. 路由控制 ---
page = st.query_params.get("page", "dashboard")
if page == "vote":
    render_voting_page()
else:
    render_dashboard_page()
