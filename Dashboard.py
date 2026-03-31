import streamlit as st
import pandas as pd
import os
import time
import altair as alt
from datetime import datetime
import urllib.parse

# --- 1. 頁面設定 ---
st.set_page_config(page_title="新光醫院 AI 軟體評估", layout="wide")

# --- 2. 評分標準與詳細內容 ---
RUBRIC_CONTENT = {
    "1. 模型準確度與臨床一致性": "評核 AUC/感度/特異性是否達標。方式：查驗臨床驗證報告與 TFDA 許可證。",
    "2. 異常值偵測與風險警示": "辨識無法判讀影像之能力。方式：測試高風險病灶之即時通報機制。",
    "3. 病患安全防護機制": "防止過度診斷。方式：確認具備『醫師覆核』流程，而非 AI 自動發報。",
    "4. 臨床工作流適應性": "是否符合現有診斷流程。方式：評估醫師操作步驟是否增加負擔或能簡化流程。",
    "5. 院內系統整合度": "支援 DICOM/HL7。方式：觀察與 PACS/HIS 介接流暢度 (建議 < 5秒)。",
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
    """ 投票端 """
    try:
        project_name = st.query_params.get("project", None)
    except: project_name = None

    if not project_name:
        project_name = st.text_input("請輸入專案名稱：")
        if not project_name: st.stop()

    st.markdown(f"## 📝 正在評估：{project_name}")
    voter_name = st.text_input("您的姓名 (評審)", placeholder="此姓名僅供存檔，看板將匿名顯示")

    user_scores = {}
    total = 0
    for cat, items in RUBRIC.items():
        st.markdown(f"### {cat}")
        for name, weight in items:
            score = st.slider(name, 0, 100, 70, 5, help=RUBRIC_CONTENT.get(name, ""), key=name)
            w_score = (score/100)*weight
            user_scores[name] = w_score
            total += w_score

    st.divider()
    c = "green" if total >= 75 else "orange" if total >= 60 else "red"
    st.markdown(f"<h2 style='text-align:center;'>目前總得分：<span style='color:{c}; font-size:60px;'>{total:.1f}</span></h2>", unsafe_allow_html=True)
    
    fb = st.text_area("💬 匿名建議 (將顯示於大螢幕看板)")
    if st.button("🚀 確認提交", use_container_width=True, type="primary"):
        if not voter_name: st.error("請輸入姓名"); return
        rec = {"Project": project_name, "Voter": voter_name, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Total Score": total, "Feedback": fb}
        rec.update(user_scores)
        pd.DataFrame([rec]).to_csv(FILE_NAME, mode='a', index=False, header=not os.path.exists(FILE_NAME))
        st.success("提交成功！"); st.balloons(); time.sleep(1); st.rerun()

def render_dashboard_page():
    """ 看板端：指標字體加大，並配合決策結論變色 """
    if "current_project" not in st.session_state: st.session_state["current_project"] = None

    with st.sidebar:
        st.header("🗂️ 專案管理")
        projs = get_existing_projects()
        sel = st.radio("選擇專案：", projs if projs else ["尚未建立"], key="p_sel")
        if sel != "尚未建立": st.session_state["current_project"] = sel
        
        st.divider()
        with st.form("add"):
            n = st.text_input("新增專案")
            if st.form_submit_button("建立"):
                st.session_state["current_project"] = n; st.rerun()
        
        auto = st.toggle("🔄 自動刷新 (Live)", value=True)
        if st.button("🗑️ 清空所有數據"):
            if os.path.exists(FILE_NAME): os.remove(FILE_NAME); st.rerun()

    curr = st.session_state["current_project"]
    if not curr: st.info("👋 請在左側選擇或新增專案。"); return

    st.markdown(f"<h1 style='text-align: center;'>📊 {curr} - 決策看板</h1>", unsafe_allow_html=True)
    
    link = f"https://shinkong-ai-vote.streamlit.app/?page=vote&project={urllib.parse.quote(curr)}"
    c_l, c_r = st.columns([1, 4])
    c_l.image(f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={urllib.parse.quote(link)}")
    c_r.markdown(f"**評分連結：**<br><code style='font-size:22px;'>{link}</code>", unsafe_allow_html=True)

    st.divider()

    if os.path.exists(FILE_NAME):
        df = pd.read_csv(FILE_NAME)
        df_p = df[df["Project"] == curr]
        if not df_p.empty:
            df_c = df_p.sort_values("Timestamp").drop_duplicates(subset=["Voter"], keep="last")
            avg = df_c["Total Score"].mean()

            # 計算決策顏色邏輯
            res = "推薦引進" if avg >= 75 else "修正後推薦" if avg >= 60 else "不推薦"
            clr = "#28a745" if avg >= 75 else "#ffc107" if avg >= 60 else "#dc3545" # 綠、黃、紅

            # 1. 核心指標區：字體加大，數值配合決策變色
            m1, m2, m3 = st.columns(3)
            
            # 使用自定義 HTML 渲染指標，使其顏色一致
            m1.markdown(f"""
                <div style='text-align: center;'>
                    <p style='font-size: 24px; color: #555; margin-bottom: 0;'>已投人數</p>
                    <p style='font-size: 80px; font-weight: bold; color: {clr}; margin-top: -10px;'>{len(df_c)} <span style='font-size: 30px;'>人</span></p>
                </div>
            """, unsafe_allow_html=True)
            
            m2.markdown(f"""
                <div style='text-align: center;'>
                    <p style='font-size: 24px; color: #555; margin-bottom: 0;'>平均總分</p>
                    <p style='font-size: 80px; font-weight: bold; color: {clr}; margin-top: -10px;'>{avg:.1f}</p>
                </div>
            """, unsafe_allow_html=True)
            
            m3.markdown(f"""
                <div style='text-align: center;'>
                    <p style='font-size: 24px; color: #555; margin-bottom: 0;'>決策結論：</p>
                    <p style='font-size: 80px; font-weight: bold; color: {clr}; margin-top: -10px;'>{res}</p>
                </div>
            """, unsafe_allow_html=True)

            st.divider()
            
            # 2. 圖表並排
            c_pie, c_bar = st.columns([2, 3])
            with c_pie:
                st.markdown("### 🗳️ 投票結果分布")
                df_c["Status"] = df_c["Total Score"].apply(lambda s: "推薦引進" if s >= 75 else "修正後推薦" if s >= 60 else "不推薦")
                pie_df = df_c["Status"].value_counts().reset_index()
                pie_df.columns = ["類別", "票數"]
                pie = alt.Chart(pie_df).mark_arc(outerRadius=120).encode(
                    theta="票數", color=alt.Color("類別", scale=alt.Scale(domain=["推薦引進", "修正後推薦", "不推薦"], range=["#28a745", "#ffc107", "#dc3545"]), legend=alt.Legend(labelFontSize=18)),
                ).properties(height=450)
                st.altair_chart(pie, use_container_width=True)

            with c_bar:
                st.markdown("### 📈 16 項指標達成率 (%)")
                items = []
                for cat, crits in RUBRIC.items():
                    for name, w in crits:
                        if name in df_c.columns:
                            items.append({"指標": name, "率": round((df_c[name].mean()/w)*100, 1), "分類": cat.split(" ")[0]})
                bar = alt.Chart(pd.DataFrame(items)).mark_bar().encode(
                    x=alt.X("率", scale=alt.Scale(domain=[0, 100]), axis=alt.Axis(labelFontSize=16)), 
                    y=alt.Y("指標", sort=None, axis=alt.Axis(labelFontSize=18, labelLimit=500)), 
                    color=alt.Color("分類", legend=alt.Legend(labelFontSize=16)),
                ).properties(height=500)
                st.altair_chart(bar + bar.mark_text(align='left', dx=5, fontSize=18).encode(text='率:Q'), use_container_width=True)

            # --- 3. 補齊 16 條指標內容說明 ---
            st.divider()
            st.markdown("<h2 style='color: #1E90FF;'>📋 16 項評核指標定義與準則</h2>", unsafe_allow_html=True)
            gl, gr = st.columns(2)
            all_g = list(RUBRIC_CONTENT.items())
            def show_g(items, col):
                for n, c in items:
                    col.markdown(f"""<div style="background-color:#f8f9fa;padding:15px;border-radius:8px;margin-bottom:10px;border-left:5px solid #1E90FF;"><span style="font-size:20px;font-weight:bold;color:#333;">{n}</span><br><span style="font-size:18px;color:#666;">{c}</span></div>""", unsafe_allow_html=True)
            show_g(all_g[:8], gl); show_g(all_g[8:], gr)

            # --- 4. 匿名建議 (特大字體) ---
            st.divider()
            st.markdown("<h2 style='color: #4B0082;'>💬 評審匿名建議</h2>", unsafe_allow_html=True)
            fb_list = df_c[df_c["Feedback"].notna() & (df_c["Feedback"] != "")]["Feedback"].tolist()
            if fb_list:
                for i, msg in enumerate(fb_list, 1):
                    st.markdown(f"""<div style="background-color:#f0f2f6;padding:20px;border-radius:10px;margin-bottom:15px;border-left:10px solid #4B0082;"><span style="font-size:28px;font-weight:500;">{msg}</span></div>""", unsafe_allow_html=True)
            else: st.caption("目前無意見。")

    if auto: time.sleep(5); st.rerun()

# --- 5. 路由 ---
pg = st.query_params.get("page", "dashboard")
if pg == "vote": render_voting_page()
else: render_dashboard_page()
