import streamlit as st
import pandas as pd
import os
import time
import altair as alt
from datetime import datetime
import urllib.parse

# --- 1. 頁面設定 ---
st.set_page_config(page_title="新光醫院 AI 軟體評定", layout="wide")

# --- 2. 完整 16 條指標內容與權重 (保持不變) ---
RUBRIC_CONTENT = {
    "1. 模型準確度與臨床一致性": "評核 AUC/感度/特異性是否達標。方式：查驗臨床驗證報告與 TFDA 許可證。",
    "2. 異常值偵測與風險警示": "辨識無法判讀影像之能力。方式：測試高風險病灶之即時通報機制。",
    "3. 病患安全防護機制": "防止過度診斷。方式：確認具備『醫師覆核』流程，而非 AI 自動發報。",
    "4. 臨床工作流適應性": "是否符合現有診斷流程。方式：評估醫師操作步驟是否增加負擔或能簡化流程。",
    "5. 院內系統整合度": "支援 DICOM/HL7 指標。方式：觀察與 PACS/HIS 介接流暢度 (建議 < 5秒)。",
    "6. 資安合規性": "數據傳輸加密。方式：查驗 ISO 27001 認證或資安漏洞掃描報告。",
    "7. 系統維運與更新機制": "系統穩定性。方式：確認當機備援方案 (DR) 及廠商 SLA 支援能力。",
    "8. 數據隱私與去識別化": "保護病患隱私。方式：查驗資料產出、傳輸及儲存是否落實去識別化規範。",
    "9. 可解釋性與透明度": "非黑箱 AI。方式：確認是否提供 Heatmap (熱區圖) 或信心度評分。",
    "10. 人類監督機制": "醫師最高權限。方式：測試醫師是否能更正結果並保留修改軌跡。",
    "11. 偏差檢測與公平性": "避免演算法歧視。方式：查驗模型在不同性別、年齡層之效能是否穩定無顯著偏差。",
    "12. 模型生命週期管理": "效能不隨時間下降。方式：確認廠商有無監控效能偏移 (Drift) 機制。",
    "13. 成本效益分析": "ROI 評估。方式：評估是否縮短判讀時程 (TAT) 或降低檢查支出。",
    "14. 市場實績與品牌信譽": "產品成熟度。方式：查驗國內外醫學中心採用實績及廠商財務/技術服務穩定度。",
    "15. 病患體驗與衛教應用": "醫病溝通。方式：查驗 AI 報告是否具備圖形化輸出供病患參考。",
    "16. ESG 與永續指標": "社會責任。方式：評估無紙化程度及對偏鄉醫療可近性之提升。"
}

RUBRIC = {
    "一、臨床卓越與安全性 (35%)": [
        ("1. 模型準確度與臨床一致性", 10.0), ("2. 異常值偵測與風險警示", 9.0), 
        ("3. 病患安全防護機制", 8.0), ("4. 臨床工作流適應性", 8.0)
    ],
    "二、系統整合與資安 (25%)": [
        ("5. 院內系統整合度", 7.0), ("6. 資安合規性", 7.0), 
        ("7. 系統維運與更新機制", 6.0), ("8. 數據隱私與去識別化", 5.0)
    ],
    "三、負責性 AI 與治理 (25%)": [
        ("9. 可解釋性與透明度", 7.0), ("10. 人類監督機制", 7.0), 
        ("11. 偏差檢測與公平性", 5.0), ("12. 模型生命週期管理", 6.0)
    ],
    "四、營運效益與創新價值 (15%)": [
        ("13. 成本效益分析", 5.0), ("14. 市場實績與品牌信譽", 4.0),
        ("15. 病患體驗與衛教應用", 3.0), ("16. ESG 與永續指標", 3.0)
    ]
}

FILE_NAME = "vote_data_v2.csv"

# --- 3. 核心輔助函式 ---
def ensure_csv():
    if not os.path.exists(FILE_NAME):
        cols = ["Project", "Voter", "Timestamp", "Total Score", "Feedback"]
        for cat in RUBRIC:
            for name, weight in RUBRIC[cat]:
                cols.append(name)
        pd.DataFrame(columns=cols).to_csv(FILE_NAME, index=False)

def get_existing_projects():
    ensure_csv()
    try:
        df = pd.read_csv(FILE_NAME)
        return sorted([str(p) for p in df["Project"].dropna().unique().tolist() if str(p) != "SYSTEM_INIT"])
    except: return []

# --- 4. 頁面渲染 ---

def render_voting_page():
    # ✅ 修正：使用最新的 st.query_params 讀取方式
    project_from_url = st.query_params.get("project", "")
    
    # 如果 URL 沒帶專案名稱，才顯示輸入框
    if not project_from_url:
        project_name = st.text_input("請手動輸入專案名稱：")
    else:
        project_name = project_from_url
        st.markdown(f"## 📝 正在評估專案：**{project_name}**")

    if not project_name: st.stop()

    voter_name = st.text_input("您的姓名 (評審)", placeholder="姓名僅供存檔核對")

    user_scores = {}
    total = 0
    for cat, items in RUBRIC.items():
        st.subheader(cat)
        for name, weight in items:
            score = st.slider(name, 0, 100, 70, 5, help=RUBRIC_CONTENT.get(name), key=f"v_{name}")
            w_score = (score/100)*weight
            user_scores[name] = w_score
            total += w_score

    st.divider()
    c = "green" if total >= 75 else "orange" if total >= 60 else "red"
    st.markdown(f"<h2 style='text-align:center;'>目前總計分數：<span style='color:{c}; font-size:60px;'>{total:.1f}</span></h2>", unsafe_allow_html=True)
    
    fb = st.text_area("💬 匿名建議回饋")
    if st.button("🚀 確認提交評分", use_container_width=True, type="primary"):
        if not voter_name: st.error("請輸入姓名"); return
        ensure_csv()
        rec = {"Project": project_name, "Voter": voter_name, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Total Score": total, "Feedback": fb}
        rec.update(user_scores)
        pd.DataFrame([rec]).to_csv(FILE_NAME, mode='a', index=False, header=False)
        st.success("提交成功！已紀錄您的評分。"); st.balloons(); time.sleep(1); st.rerun()

def render_dashboard_page():
    if "current_project" not in st.session_state: st.session_state["current_project"] = None

    with st.sidebar:
        st.header("🗂️ 專案管理")
        with st.form("new_p", clear_on_submit=True):
            name = st.text_input("➕ 新增專案")
            if st.form_submit_button("建立"):
                if name:
                    ensure_csv()
                    dummy = {"Project": name, "Voter": "SYSTEM_INIT", "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Total Score": 0}
                    pd.DataFrame([dummy]).to_csv(FILE_NAME, mode='a', index=False, header=False)
                    st.session_state["current_project"] = name
                    st.rerun()

        st.divider()
        projs = get_existing_projects()
        if projs:
            idx = projs.index(st.session_state["current_project"]) if st.session_state["current_project"] in projs else 0
            sel = st.selectbox("🎯 切換專案：", projs, index=idx)
            st.session_state["current_project"] = sel
        
        auto = st.toggle("🔄 自動刷新 (Live)", value=True)
        if st.button("🗑️ 清空所有數據"):
            if os.path.exists(FILE_NAME): os.remove(FILE_NAME)
            st.session_state.clear(); st.rerun()

    curr = st.session_state["current_project"]
    if not curr: st.info("👋 請在左側新增或切換專案。"); return

    # ✅ 修正：確保連結字體夠大且 QR Code 正常
    link = f"https://shinkong-ai-vote.streamlit.app/?page=vote&project={urllib.parse.quote(curr)}"
    st.markdown(f"<h1 style='text-align: center;'>📊 {curr} - 決策看板</h1>", unsafe_allow_html=True)
    
    col_l, col_r = st.columns([1, 4])
    with col_l:
        st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={urllib.parse.quote(link)}")
    with col_r:
        st.markdown(f"<div style='background-color:#f0f2f6; padding:15px; border-radius:10px;'><strong>手機評分網址 (字體已加大)：</strong><br><a href='{link}' style='font-size:24px; color:#1E90FF; word-break:break-all;'>{link}</a></div>", unsafe_allow_html=True)

    st.divider()

    if os.path.exists(FILE_NAME):
        df = pd.read_csv(FILE_NAME)
        df_p = df[(df["Project"] == curr) & (df["Voter"] != "SYSTEM_INIT")]
        
        if not df_p.empty:
            df_c = df_p.sort_values("Timestamp").drop_duplicates(subset=["Voter"], keep="last")
            avg = df_c["Total Score"].mean()
            res = "推薦引進" if avg >= 75 else "修正後推薦" if avg >= 60 else "不推薦"
            clr = "#28a745" if avg >= 75 else "#ffc107" if avg >= 60 else "#dc3545"

            # 頂部數據 (大字體)
            m1, m2, m3 = st.columns(3)
            def box(l, v): return f"<div style='text-align:center;'><p style='font-size:28px; color:#555;'>{l}</p><p style='font-size:85px; font-weight:bold; color:{clr}; margin-top:-20px;'>{v}</p></div>"
            m1.markdown(box("已投人數", len(df_c)), unsafe_allow_html=True)
            m2.markdown(box("平均總分", f"{avg:.1f}"), unsafe_allow_html=True)
            m3.markdown(box("目前決策結論", res), unsafe_allow_html=True)

            st.divider()
            
            # ✅ 修正：確保圓餅圖與長條圖並行顯示
            c_pie, c_bar = st.columns([2, 3])
            with c_pie:
                st.markdown("### 🗳️ 投票分布")
                df_c["Status"] = df_c["Total Score"].apply(lambda s: "推薦引進" if s >= 75 else "修正後推薦" if s >= 60 else "不推薦")
                st_counts = df_c["Status"].value_counts().reset_index()
                st_counts.columns = ["類別", "票數"]
                pie = alt.Chart(st_counts).mark_arc(outerRadius=120).encode(
                    theta="票數", color=alt.Color("類別", scale=alt.Scale(domain=["推薦引進", "修正後推薦", "不推薦"], range=["#28a745", "#ffc107", "#dc3545"]), legend=alt.Legend(labelFontSize=18))
                ).properties(height=450)
                st.altair_chart(pie, use_container_width=True)

            with c_bar:
                st.markdown("### 📈 指標達成率 (%)")
                items = []
                for cat, crits in RUBRIC.items():
                    for n, w in crits:
                        v = df_c[n].mean() if n in df_c.columns else 0
                        items.append({"項": n, "率": round((v/w)*100, 1), "類": cat.split(" ")[0]})
                bar = alt.Chart(pd.DataFrame(items)).mark_bar().encode(
                    x=alt.X("率", scale=alt.Scale(domain=[0, 100]), axis=alt.Axis(labelFontSize=16)), 
                    y=alt.Y("項", sort=None, axis=alt.Axis(labelFontSize=16, labelLimit=400)), color="類"
                ).properties(height=500)
                st.altair_chart(bar + bar.mark_text(align='left', dx=5, fontSize=16, fontWeight='bold').encode(text='率:Q'), use_container_width=True)
        else:
            st.warning("⚠️ 該專案目前尚無正式評分數據，請掃描 QR Code 開始。")

    if auto: time.sleep(5); st.rerun()

# --- 5. 路由 ---
page = st.query_params.get("page", "dashboard")
if page == "vote": render_voting_page()
else: render_dashboard_page()
