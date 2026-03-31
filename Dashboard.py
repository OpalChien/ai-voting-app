import streamlit as st
import pandas as pd
import os
import time
import altair as alt
from datetime import datetime
import urllib.parse

# --- 1. 頁面設定 ---
st.set_page_config(page_title="新光醫院 AI 軟體評估", layout="wide")

# --- 2. 評分標準與詳細說明 ---
RUBRIC_DETAILS = {
    "1. 模型準確度與臨床一致性": "評核 AUC/感度/特異性是否達標。方式：查驗臨床驗證報告與 TFDA 許可證。",
    "2. 異常值偵測與風險警示": "辨識無法判讀影像之能力。方式：測試高風險病灶之即時通報機制。",
    "3. 病患安全防護機制": "防止過度診斷。方式：確認具備『醫師覆核』流程，而非 AI 自動發報。",
    "5. 院內系統整合度": "支援 DICOM/HL7。方式：觀察與 PACS/HIS 介接流暢度 (建議 < 5秒)。",
    "6. 資安合規性": "數據傳輸加密。方式：查驗 ISO 27001 認證或資安漏洞掃描報告。",
    "7. 系統維運與更新機制": "系統穩定性。方式：確認當機備援方案 (DR) 及廠商 SLA 支援能力。",
    "9. 可解釋性與透明度": "非黑箱 AI。方式：確認是否提供 Heatmap (熱區圖) 或信心度評分。",
    "10. 人類監督機制": "醫師最高權限。方式：測試醫師是否能更正結果並保留修改軌跡。",
    "12. 模型生命週期管理": "效能不隨時間下降。方式：確認廠商有無監控效能偏移 (Drift) 機制。",
    "13. 成本效益分析": "ROI 評估。方式：評估是否縮短判讀時程 (TAT) 或降低檢查支出。",
    "15. 病患體驗與衛教應用": "醫病溝通。方式：查驗 AI 報告是否具備圖形化輸出供病患參考。",
    "16. ESG 與永續指標": "社會責任。方式：評估無紙化程度及對偏鄉醫療可近性之提升。"
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

# --- 3. 輔助函式 ---
def get_existing_projects():
    if os.path.exists(FILE_NAME):
        try:
            df = pd.read_csv(FILE_NAME)
            return sorted(df["Project"].dropna().unique().tolist())
        except: return []
    return []

# --- 4. 頁面渲染 ---

def render_voting_page():
    """ 投票端：保持 Slider 與 姓名覆蓋邏輯 """
    project_name = st.query_params.get("project", st.text_input("專案名稱："))
    if not project_name: st.stop()

    st.markdown(f"### 📝 評估：**{project_name}**")
    voter_name = st.text_input("您的姓名 (評審)", key="v_name")

    user_scores = {}
    total = 0
    for cat, items in RUBRIC.items():
        st.subheader(cat)
        for name, weight in items:
            score = st.slider(name, 0, 100, 70, 5, help=RUBRIC_DETAILS.get(name, ""), key=name)
            w_score = (score/100)*weight
            user_scores[name] = w_score
            total += w_score

    st.divider()
    c = "green" if total >= 75 else "orange" if total >= 60 else "red"
    st.markdown(f"### 總分：<span style='color:{c}; font-size:40px;'>{total:.1f}</span>", unsafe_allow_html=True)
    
    fb = st.text_area("💬 意見回饋")
    if st.button("🚀 提交評分", use_container_width=True, type="primary"):
        if not voter_name: st.error("請輸入姓名"); return
        rec = {"Project": project_name, "Voter": voter_name, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Total Score": total, "Feedback": fb}
        rec.update(user_scores)
        df = pd.DataFrame([rec])
        df.to_csv(FILE_NAME, mode='a', index=False, header=not os.path.exists(FILE_NAME))
        st.success("提交成功！"); st.balloons(); time.sleep(2); st.rerun()

def render_dashboard_page():
    """ 看板端：找回圓餅圖，保留所有管理功能 """
    # Session State
    if "current_project" not in st.session_state: st.session_state["current_project"] = None

    with st.sidebar:
        st.header("🗂️ 專案管理")
        projs = get_existing_projects()
        sel = st.radio("切換專案：", projs if projs else ["尚未建立"], key="p_sel")
        if sel != "尚未建立": st.session_state["current_project"] = sel
        
        st.divider()
        with st.form("add_p"):
            new_p = st.text_input("新增專案")
            if st.form_submit_button("建立"):
                st.session_state["current_project"] = new_p; st.rerun()
        
        auto = st.toggle("🔄 自動刷新 (Live)", value=True)
        if st.button("🗑️ 清空數據"):
            if os.path.exists(FILE_NAME): os.remove(FILE_NAME)
            st.rerun()

    curr = st.session_state["current_project"]
    if not curr: st.info("請選擇專案"); return

    # QR Code
    link = f"https://shinkong-ai-vote.streamlit.app/?page=vote&project={urllib.parse.quote(curr)}"
    st.title(f"📊 {curr} - 決議看板")
    col_l, col_r = st.columns([1, 4])
    col_l.image(f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={urllib.parse.quote(link)}")
    col_r.info(f"評分連結：{link}")

    if os.path.exists(FILE_NAME):
        df = pd.read_csv(FILE_NAME)
        df_p = df[df["Project"] == curr]
        if not df_p.empty:
            df_c = df_p.sort_values("Timestamp").drop_duplicates(subset=["Voter"], keep="last")
            avg = df_c["Total Score"].mean()

            # 頂部數據
            m1, m2, m3 = st.columns(3)
            m1.metric("已投人數", f"{len(df_c)} 人")
            m2.metric("平均總分", f"{avg:.1f}")
            res = "推薦引進" if avg >= 75 else "修正後推薦" if avg >= 60 else "不推薦"
            clr = "green" if avg >= 75 else "orange" if avg >= 60 else "red"
            m3.markdown(f"決策：# :{clr}[{res}]")

            st.divider()
            
            # 圖表區：圓餅圖與長條圖並列
            col_pie, col_bar = st.columns([2, 3])
            
            with col_pie:
                st.subheader("🗳️ 投票分布")
                df_c["Status"] = df_c["Total Score"].apply(lambda s: "推薦引進" if s >= 75 else "修正後推薦" if s >= 60 else "不推薦")
                st_counts = df_c["Status"].value_counts().reset_index()
                st_counts.columns = ["類別", "票數"]
                pie = alt.Chart(st_counts).mark_arc(outerRadius=100).encode(
                    theta="票數", color=alt.Color("類別", scale=alt.Scale(domain=["推薦引進", "修正後推薦", "不推薦"], range=["#4CAF50", "#FF9800", "#F44336"]))
                ).properties(height=350)
                st.altair_chart(pie, use_container_width=True)

            with col_bar:
                st.subheader("📈 細項達成率 (%)")
                items = []
                for cat, crits in RUBRIC.items():
                    for name, w in crits:
                        if name in df_c.columns:
                            items.append({"項": name, "率": round((df_c[name].mean()/w)*100, 1), "類": cat.split(" ")[0]})
                bar = alt.Chart(pd.DataFrame(items)).mark_bar().encode(
                    x=alt.X("率", scale=alt.Scale(domain=[0, 100])), y=alt.Y("項", sort=None), color="類"
                ).properties(height=350)
                st.altair_chart(bar + bar.mark_text(align='left', dx=5).encode(text='率:Q'), use_container_width=True)

            # --- 新功能：評審意見清單 ---
            st.divider()
            st.subheader("💬 評審意見與建議")
            feedback_df = df_c[df_c["Feedback"].notna()][["Voter", "Feedback"]]
            if not feedback_df.empty:
                for idx, row in feedback_df.iterrows():
                    st.markdown(f"**{row['Voter']}**：{row['Feedback']}")
            else:
                st.caption("目前尚無意見回饋。")

            with st.expander("📂 下載與明細"):
                st.dataframe(df_c)
                st.download_button("📥 下載 (UTF-8-SIG)", df_c.to_csv(index=False).encode('utf-8-sig'), f'{curr}.csv')

    if auto: time.sleep(5); st.rerun()

# --- 5. 路由 ---
pg = st.query_params.get("page", "dashboard")
if pg == "vote": render_voting_page()
else: render_dashboard_page()
