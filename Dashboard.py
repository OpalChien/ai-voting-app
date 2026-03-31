import streamlit as st
import pandas as pd
import os
import time
import altair as alt
from datetime import datetime
import urllib.parse

# --- 1. 頁面設定 ---
st.set_page_config(page_title="新光醫院 AI 軟體評定", layout="wide")

# --- 2. 評分標準與詳細說明 ---
RUBRIC_DETAILS = {
    "1. 模型準確度與臨床一致性": "評核 AUC/感度/特異性是否達標。方式：查驗臨床驗證報告與 TFDA 許可證。",
    "2. 異常值偵測與風險警示": "辨識無法判讀影像之能力。方式：測試高風險病灶之即時通報機制。",
    "3. 病患安全防護機制": "防止過度診斷。方式：確認具備『醫師覆核』流程，而非 AI 自動發報。",
    "5. 院內系統整合度": "支援 DICOM/HL7指標。方式：觀察與 PACS/HIS 介接流暢度 (建議 < 5秒)。",
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
    """ 投票端：優化手機端閱讀體驗 """
    try:
        project_name = st.query_params.get("project", None)
    except: project_name = None

    if not project_name:
        project_name = st.text_input("請輸入專案名稱：")
        if not project_name: st.stop()

    st.markdown(f"## 📝 正在評估：{project_name}")
    voter_name = st.text_input("您的姓名 (評審)", placeholder="後台核對用，看板將匿名顯示")

    user_scores = {}
    total = 0
    for cat, items in RUBRIC.items():
        st.markdown(f"### {cat}")
        for name, weight in items:
            score = st.slider(name, 0, 100, 70, 5, help=RUBRIC_DETAILS.get(name, ""), key=name)
            w_score = (score/100)*weight
            user_scores[name] = w_score
            total += w_score

    st.divider()
    c = "green" if total >= 75 else "orange" if total >= 60 else "red"
    st.markdown(f"<h2 style='text-align: center;'>目前總計：<span style='color:{c}; font-size:60px;'>{total:.1f}</span></h2>", unsafe_allow_html=True)
    
    fb = st.text_area("💬 匿名建議 (將直接顯示於大螢幕)")
    if st.button("🚀 確認提交評分", use_container_width=True, type="primary"):
        if not voter_name: st.error("請輸入姓名"); return
        rec = {"Project": project_name, "Voter": voter_name, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Total Score": total, "Feedback": fb}
        rec.update(user_scores)
        df = pd.DataFrame([rec])
        df.to_csv(FILE_NAME, mode='a', index=False, header=not os.path.exists(FILE_NAME))
        st.success("提交成功！"); st.balloons(); time.sleep(1); st.rerun()

def render_dashboard_page():
    """ 看板端：字體放大優化版本 """
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
        if st.button("🗑️ 清空所有數據"):
            if os.path.exists(FILE_NAME): os.remove(FILE_NAME)
            st.rerun()

    curr = st.session_state["current_project"]
    if not curr: st.info("👋 請在左側選擇或新增評估專案。"); return

    # QR Code
    link = f"https://shinkong-ai-vote.streamlit.app/?page=vote&project={urllib.parse.quote(curr)}"
    st.markdown(f"<h1 style='text-align: center;'>📊 {curr} - 決策看板</h1>", unsafe_allow_html=True)
    
    col_l, col_r = st.columns([1, 4])
    col_l.image(f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={urllib.parse.quote(link)}")
    col_r.markdown(f"**手機評分連結：**<br><code style='font-size: 20px;'>{link}</code>", unsafe_allow_html=True)

    st.divider()

    if os.path.exists(FILE_NAME):
        df = pd.read_csv(FILE_NAME)
        df_p = df[df["Project"] == curr]
        if not df_p.empty:
            df_c = df_p.sort_values("Timestamp").drop_duplicates(subset=["Voter"], keep="last")
            avg = df_c["Total Score"].mean()

            # 1. 核心指標 (放大字體)
            m1, m2, m3 = st.columns(3)
            # 使用自定義 HTML 放大 Metric 字體
            st.markdown("""
                <style>
                [data-testid="stMetricValue"] { font-size: 60px !important; }
                [data-testid="stMetricLabel"] { font-size: 24px !important; }
                </style>
                """, unsafe_allow_html=True)
            
            m1.metric("已投人數", f"{len(df_c)} 人")
            m2.metric("平均總分", f"{avg:.1f}")
            res = "推薦引進" if avg >= 75 else "修正後推薦" if avg >= 60 else "不推薦"
            clr = "green" if avg >= 75 else "orange" if avg >= 60 else "red"
            m3.markdown(f"<p style='font-size: 24px; font-weight: bold; margin-bottom: 0;'>目前決策：</p><h1 style='color:{clr}; font-size: 70px; margin-top: 0;'>{res}</h1>", unsafe_allow_html=True)

            st.divider()
            
            # 2. 圖表區：圓餅圖 與 長條圖 (加大字體)
            c_left, c_right = st.columns([2, 3])
            
            with c_left:
                st.markdown("### 🗳️ 投票結果分布")
                df_c["Status"] = df_c["Total Score"].apply(lambda s: "推薦引進" if s >= 75 else "修正後推薦" if s >= 60 else "不推薦")
                st_counts = df_c["Status"].value_counts().reset_index()
                st_counts.columns = ["類別", "票數"]
                pie = alt.Chart(st_counts).mark_arc(outerRadius=120).encode(
                    theta="票數", 
                    color=alt.Color("類別", scale=alt.Scale(domain=["推薦引進", "修正後推薦", "不推薦"], range=["#4CAF50", "#FF9800", "#F44336"]),
                                   legend=alt.Legend(labelFontSize=18, titleFontSize=20)),
                    tooltip=["類別", "票數"]
                ).properties(height=450)
                st.altair_chart(pie, use_container_width=True)

            with c_right:
                st.markdown("### 📈 各指標達成率 (%)")
                items = []
                for cat, crits in RUBRIC.items():
                    for name, w in crits:
                        if name in df_c.columns:
                            items.append({"指標項目": name, "達成率 (%)": round((df_c[name].mean()/w)*100, 1), "分類": cat.split(" ")[0]})
                
                bar = alt.Chart(pd.DataFrame(items)).mark_bar().encode(
                    x=alt.X("達成率 (%)", scale=alt.Scale(domain=[0, 100]), axis=alt.Axis(labelFontSize=16, titleFontSize=18)), 
                    y=alt.Y("指標項目", sort=None, axis=alt.Axis(labelLimit=500, labelFontSize=18, titleFontSize=20)), 
                    color=alt.Color("分類", legend=alt.Legend(labelFontSize=16, titleFontSize=18)),
                    tooltip=["指標項目", "達成率 (%)"]
                ).properties(height=450)
                
                text = bar.mark_text(align='left', dx=5, fontSize=18, fontWeight='bold').encode(text='達成率 (%):Q')
                st.altair_chart(bar + text, use_container_width=True)

            # 3. 匿名意見回饋 (放大並美化)
            st.divider()
            st.markdown("<h2 style='color: #4B0082;'>💬 評審匿名意見與建議</h2>", unsafe_allow_html=True)
            feedback_list = df_c[df_c["Feedback"].notna() & (df_c["Feedback"] != "")]["Feedback"].tolist()
            
            if feedback_list:
                for i, msg in enumerate(feedback_list, 1):
                    # 加大意見字體到 24px
                    st.markdown(f"""
                        <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin-bottom: 15px; border-left: 10px solid #4B0082;">
                            <span style="font-size: 20px; color: #555;">建議 {i}：</span><br>
                            <span style="font-size: 28px; font-weight: 500;">{msg}</span>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.caption("尚未有意見回饋。")

            # 4. 下載明細 (縮小放在最後)
            with st.expander("📂 數據明細與下載"):
                st.dataframe(df_c)
                st.download_button("📥 下載採計結果", df_c.to_csv(index=False).encode('utf-8-sig'), f'{curr}_final.csv')

    if auto: time.sleep(5); st.rerun()

# --- 5. 路由 ---
pg = st.query_params.get("page", "dashboard")
if pg == "vote": render_voting_page()
else: render_dashboard_page()
