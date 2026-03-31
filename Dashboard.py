import streamlit as st
import pandas as pd
import os
import time
import altair as alt
from datetime import datetime
import urllib.parse

# --- 1. 頁面設定 ---
st.set_page_config(page_title="新光醫院 AI 軟體評估", layout="wide")

# --- 2. 評分標準與詳細說明 (新增細項評估內容) ---
# 這是為了回應您要求的「列出這16條(實際為12條核心項)的評估內容跟方式」
RUBRIC_DETAILS = {
    "1. 模型準確度與臨床一致性": "評估其 AUC/感度/特異性是否達標。方式：查驗臨床驗證報告與 TFDA 醫材許可證。",
    "2. 異常值偵測與風險警示": "系統是否能辨識無法判讀之影像。方式：測試高風險病灶之即時通報機制與準確性。",
    "3. 病患安全防護機制": "防止 AI 誤導決策。方式：確認具備『醫師覆核』流程，而非 AI 自動發報。",
    "5. 院內系統整合度": "支援 DICOM/HL7。方式：觀察與 PACS/HIS 介接流暢度，讀取時間建議 < 5秒。",
    "6. 資安合規性": "數據傳輸加密。方式：查驗 ISO 27001 認證或最近一期資安漏洞掃描報告。",
    "7. 系統維運與更新機制": "系統穩定性。方式：確認當機備援方案 (DR) 及廠商 SLA 支援能力。",
    "9. 可解釋性與透明度": "非黑箱 AI。方式：確認是否提供 Heatmap (熱區圖) 或信心度評分標註。",
    "10. 人類監督機制": "醫師最高權限。方式：測試醫師是否能輕易更正 AI 結果並保留修改軌跡。",
    "12. 模型生命週期管理": "模型不會隨時間失效。方式：確認廠商有無監控效能偏移 (Drift) 之機制。",
    "13. 成本效益分析": "投資報酬率。方式：評估是否縮短判讀時程 (TAT) 或降低後續檢查支出。",
    "15. 病患體驗與衛教應用": "醫病溝通輔助。方式：查驗 AI 報告是否具備圖形化輸出供病患參考。",
    "16. ESG 與永續指標": "社會責任。方式：評估無紙化程度及對偏鄉醫療可近性之提升潛力。"
}

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

# --- 3. 輔助函式 (保留原始讀取邏輯) ---
def get_existing_projects():
    if os.path.exists(FILE_NAME):
        try:
            df = pd.read_csv(FILE_NAME)
            if "Project" in df.columns:
                projects = df["Project"].dropna().unique().tolist()
                return sorted(projects)
        except: return []
    return []

# --- 4. 頁面渲染函式 ---

def render_voting_page():
    """ 投票介面：保留所有提交與覆蓋邏輯，並加入細項說明 """
    try:
        project_name = st.query_params.get("project", None)
    except: project_name = None

    if not project_name:
        st.warning("⚠️ 警告：未偵測到專案名稱。")
        project_name = st.text_input("或請手動輸入專案名稱：")
        if not project_name: st.stop()

    st.markdown(f"### 📝 正在評估：**{project_name}**")
    st.caption("💡 點擊項目旁的 (?) 可查看詳細評估內容與方式。")

    voter_name = st.text_input("您的姓名 (評審)", placeholder="請輸入姓名")

    user_scores = {}
    current_total_score = 0

    for category, criteria_list in RUBRIC.items():
        st.subheader(category)
        for criterion, weight in criteria_list:
            # 加入細項說明
            help_text = RUBRIC_DETAILS.get(criterion, "")
            score = st.slider(
                f"{criterion}",
                min_value=0, max_value=100, value=70, step=5,
                key=criterion,
                help=f"{help_text} (滿分權重: {weight})"
            )
            weighted_score = (score / 100) * weight
            user_scores[criterion] = weighted_score
            current_total_score += weighted_score

    st.divider()
    # 即時總分顯示
    score_color = "green" if current_total_score >= 75 else "orange" if current_total_score >= 60 else "red"
    st.markdown(f'### 🏆 目前評分：<span style="color:{score_color}; font-size:40px;">{current_total_score:.1f}</span> / 100', unsafe_allow_html=True)
    
    feedback = st.text_area("💬 意見回饋 / 備註", placeholder="請輸入對此案的建議...")

    if st.button("🚀 確認提交評分", type="primary", use_container_width=True):
        if not voter_name:
            st.error("❌ 請輸入您的姓名後再提交！")
        else:
            vote_record = {"Project": project_name, "Voter": voter_name, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            vote_record.update(user_scores)
            vote_record.update({"Total Score": current_total_score, "Feedback": feedback})

            df_new = pd.DataFrame([vote_record])
            if not os.path.exists(FILE_NAME): df_new.to_csv(FILE_NAME, index=False)
            else: df_new.to_csv(FILE_NAME, mode='a', header=False, index=False)
            
            st.success("評分已送出！"); st.balloons(); time.sleep(2); st.rerun()

def render_dashboard_page():
    """ 儀表板：保留專案切換、自動重整與 CSV 下載功能 """
    if "current_project" not in st.session_state: st.session_state["current_project"] = None
    if "project_selector" not in st.session_state: st.session_state["project_selector"] = None
    if "pending_project" not in st.session_state: st.session_state["pending_project"] = None

    with st.sidebar:
        st.header("🗂️ 專案管理")
        existing_projects = get_existing_projects()
        
        if st.session_state.get("pending_project"):
            st.session_state["current_project"] = st.session_state["project_selector"] = st.session_state["pending_project"]
            st.session_state["pending_project"] = None

        display_options = existing_projects.copy()
        if st.session_state["current_project"] and st.session_state["current_project"] not in display_options:
            display_options.append(st.session_state["current_project"])

        if display_options:
            if st.session_state["project_selector"] not in display_options:
                st.session_state["project_selector"] = display_options[0]
            st.radio("點擊切換專案：", display_options, key="project_selector")
            if st.session_state["current_project"] != st.session_state["project_selector"]:
                st.session_state["current_project"] = st.session_state["project_selector"]
                st.rerun()

        st.subheader("➕ 新增專案")
        with st.form("create"):
            n = st.text_input("專案名稱")
            if st.form_submit_button("建立"):
                if n: st.session_state["pending_project"] = n.strip(); st.rerun()

        auto_refresh = st.toggle("🔄 開啟自動刷新 (Live)", value=True)

    st.title("📊 新光醫院 AI 評估 - 決策看板")
    curr = st.session_state["current_project"]
    if not curr:
        st.info("👋 請在左側建立或選擇一個專案。"); return

    # QR Code 生成 (保留您的連結邏輯)
    vote_link = f"https://shinkong-ai-vote.streamlit.app/?page=vote&project={urllib.parse.quote(curr)}"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={urllib.parse.quote(vote_link)}"
    
    col_qr, col_info = st.columns([1, 4])
    with col_qr: st.image(qr_url, caption="掃描評分")
    with col_info: st.info(f"📢 目前正在評估：**{curr}**"); st.code(vote_link)

    st.divider()

    # 數據讀取與展示
    if os.path.exists(FILE_NAME):
        df_all = pd.read_csv(FILE_NAME)
        df_p = df_all[df_all["Project"] == curr]
        if not df_p.empty:
            # 關鍵保留：只取每人最後一筆
            df_c = df_p.sort_values("Timestamp").drop_duplicates(subset=["Voter"], keep="last")
            avg_score = df_c["Total Score"].mean()
            
            # 指標列
            c1, c2, c3 = st.columns(3)
            c1.metric("📥 已投票人數", f"{len(df_c)} 人")
            c2.metric("🏆 平均總分", f"{avg_score:.1f}")
            res = "推薦引進" if avg_score >= 75 else "修正後推薦" if avg_score >= 60 else "不推薦"
            col = "green" if avg_score >= 75 else "orange" if avg_score >= 60 else "red"
            c3.markdown(f"**綜合決策：**\n# :{col}[{res}]")

            st.subheader("📈 各細項指標達成率與權重佔比")
            item_data = []
            for cat, criteria in RUBRIC.items():
                for crit, weight in criteria:
                    if crit in df_c.columns:
                        # 達成率 = (平均得分 / 該項滿分權重) * 100
                        pct = (df_c[crit].mean() / weight) * 100
                        item_data.append({"構面": cat.split(" ")[0], "評估細項": crit, "達成率 (%)": round(pct, 1)})
            
            # 生成長條圖 (展開細項)
            df_chart = pd.DataFrame(item_data)
            bar = alt.Chart(df_chart).mark_bar().encode(
                x=alt.X('達成率 (%)', scale=alt.Scale(domain=[0, 100])),
                y=alt.Y('評估細項', sort=None, axis=alt.Axis(labelLimit=400)),
                color='構面',
                tooltip=['評估細項', '達成率 (%)']
            ).properties(height=500)
            
            st.altair_chart(bar + bar.mark_text(align='left', dx=5).encode(text='達成率 (%):Q'), use_container_width=True)

            with st.expander("📂 數據明細與下載"):
                st.dataframe(df_c)
                st.download_button("📥 下載 Excel (CSV)", df_c.to_csv(index=False).encode('utf-8-sig'), f'{curr}_final.csv')

    if auto_refresh: time.sleep(5); st.rerun()

# --- 5. 路由 ---
p = st.query_params.get("page", "dashboard")
if p == "vote": render_voting_page()
else: render_dashboard_page()
