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

# --- 3. 輔助函式 ---

def get_existing_projects():
    """ 從 CSV 讀取已存在的專案列表 """
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
    """ 顯示投票介面 """
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
    
    # 評分區塊
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
    
    # 顯示總分
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

    # 提交區
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
                # 提交後強制重整，清除狀態，避免手機端亂跳
                st.rerun() 
            except Exception as e:
                st.error(f"寫入失敗: {e}")

def render_dashboard_page():
    """ 顯示大螢幕儀表板 """
    
    if "current_project" not in st.session_state:
        st.session_state["current_project"] = None

    # --- 側邊欄 ---
    with st.sidebar:
        st.header("🗂️ 專案管理")
        
        # 1. 專案選擇
        existing_projects = get_existing_projects()
        current_proj = st.session_state["current_project"]

        display_options = existing_projects.copy()
        # 確保當前的新專案有在選項裡
        if current_proj and current_proj not in display_options:
            display_options.append(current_proj)
        
        if display_options:
            try:
                current_index = display_options.index(current_proj)
            except:
                current_index = 0
            
            selected_proj = st.radio(
                "點擊切換專案：",
                display_options,
                index=current_index,
                key="project_selector"
            )
            
            if selected_proj != st.session_state["current_project"]:
                st.session_state["current_project"] = selected_proj
                st.rerun()
        else:
            st.info("尚無專案，請先建立。")

        st.markdown("---")
        
        # 2. 新增專案
        st.subheader("➕ 新增專案")
        with st.form("create_project_form"):
            new_proj_name = st.text_input("新專案名稱", placeholder="例如：胸腔 X 光 AI")
            if st.form_submit_button("建立"):
                if new_proj_name:
                    st.session_state["current_project"] = new_proj_name
                    st.success(f"已切換：{new_proj_name}")
                    time.sleep(0.5)
                    st.rerun()

        st.markdown("---")
        
        # 3. 自動刷新開關
        st.subheader("⚙️ 顯示設定")
        auto_refresh = st.toggle("🔄 開啟自動刷新 (Live)", value=True, help="開啟時每 5 秒更新一次數據。若要查看下方明細或下載檔案，建議【關閉】此功能以免畫面跳動。")
        
        st.divider()
        
        # 4. 危險區
        with st.expander("🗑️ 危險區域"):
            if st.button("清除所有資料", type="primary"):
                if os.path.exists(FILE_NAME):
                    os.remove(FILE_NAME)
                    st.session_state["current_project"] = None
                    st.success("已清空！")
                    time.sleep(1)
                    st.rerun()

    # --- Dashboard 主畫面 ---
    
    last_update = datetime.now().strftime('%H:%M:%S')
    status_text = f"🟢 Live 更新中 ({last_update})" if auto_refresh else "🔴 已暫停更新 (靜止模式)"
    st.markdown(f"<div style='text-align: right; color: gray; font-size: 12px;'>{status_text}</div>", unsafe_allow_html=True)
    
    st.title("📊 新光醫院 AI 軟體評估 - 決策看板")

    current_proj = st.session_state["current_project"]

    if not current_proj:
        st.info("👋 請在左側建立或選擇一個專案。")
        # 這裡不使用 st.stop() 以免阻擋自動刷新邏輯，而是直接 return
        if auto_refresh:
            time.sleep(5)
            st.rerun()
        return

    # QR Code 生成 (加上防呆機制，避免 None 導致 Crash)
    try:
        default_url = "https://shinkong-ai-vote.streamlit.app"
        # 使用 str() 強制轉型，避免 NoneType Error
        safe_proj_param = urllib.parse.quote(str(current_proj))
        vote_link = f"{default_url}/?page=vote&project={safe_proj_param}"
        encoded_vote_link = urllib.parse.quote(vote_link)
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={encoded_vote_link}"
    except Exception as e:
        st.error(f"QR Code 生成錯誤: {e}")
        qr_url = ""

    col_qr, col_info = st.columns([1, 4])
    with col_qr:
        if qr_url:
            st.image(qr_url, caption=f"{current_proj}")
    with col_info:
        st.info(f"📢 目前正在進行 **【{current_proj}】** 的評分")
        st.code(vote_link)

    st.divider()

    # --- 讀取資料 ---
    df_all = pd.DataFrame()
    if os.path.exists(FILE_NAME):
        try:
            df_all = pd.read_csv(FILE_NAME)
            if "Project" not in df_all.columns: df_all["Project"] = "Default"
            if "Timestamp" not in df_all.columns: df_all["Timestamp"] = "2024-01-01 00:00:00"
        except:
            pass 

    has_data = False
    if not df_all.empty:
        df_project = df_all[df_all["Project"] == current_proj].copy()
        
        if not df_project.empty:
            has_data = True
            
            # 分離 Clean 與 History
            # History: 包含所有提交紀錄，依照時間新到舊排序
            df_history = df_project.sort_values("Timestamp", ascending=False)
            
            # Clean: 只取每個人最新的一筆
            df_clean = df_project.sort_values("Timestamp").drop_duplicates(subset=["Voter"], keep="last")
            
            # --- 統計區 ---
            avg = df_clean["Total Score"].mean()
            c1, c2, c3 = st.columns(3)
            c1.metric("📥 已投票人數", f"{len(df_clean)} 人")
            c2.metric("🏆 平均總分", f"{avg:.1f}")
            
            final_result = "推薦引進 (Recommend)" if avg >= 75 else "修正後推薦 (Conditional)" if avg >= 60 else "不推薦 (Reject)"
            final_color = "green" if avg >= 75 else "orange" if avg >= 60 else "red"
            c3.markdown(f"**目前綜合決策：**")
            c3.markdown(f":{final_color}[## {final_result}]")
            
            st.divider()

            # --- 圖表區 ---
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

            # --- 詳細資料區 ---
            st.divider()
            st.markdown("### 📂 詳細數據區")
            if auto_refresh:
                st.info("⚠️ 提示：若要仔細查看或下載下方表格，建議先**關閉左側的自動刷新**，以免畫面跳動。")
            
            with st.expander("點擊展開數據表格", expanded=False):
                tab1, tab2 = st.tabs(["📊 最終採計結果 (Clean)", "🕒 完整修改歷程 (History)"])
                
                with tab1:
                    st.markdown("**說明：** 此處僅顯示每位評審的「最新」一次投票，用於計算最終分數。")
                    st.dataframe(df_clean)
                    csv_clean = df_clean.to_csv(index=False).encode('utf-8-sig')
                    st.download_button("📥 下載 Excel (最終結果)", csv_clean, f'{current_proj}_final.csv', 'text/csv')
                
                with tab2:
                    st.markdown("**說明：** 此處顯示「所有」提交紀錄，包含被覆蓋的舊分數。")
                    st.dataframe(df_history)
                    csv_history = df_history.to_csv(index=False).encode('utf-8-sig')
                    st.download_button("📥 下載 Excel (完整歷程)", csv_history, f'{current_proj}_history.csv', 'text/csv')

    if not has_data:
        st.warning(f"專案【{current_proj}】目前尚無資料。")

    # 只有在開關打開時，才執行等待與刷新
    if auto_refresh:
        time.sleep(5)
        st.rerun()

# --- 5. 路由控制 ---
query_params = st.query_params
page = query_params.get("page", "dashboard")

if page == "vote":
    render_voting_page()
else:
    render_dashboard_page()
