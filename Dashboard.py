import streamlit as st
import pandas as pd
import os
import time
import altair as alt
from datetime import datetime
import urllib.parse

# --- 1. 頁面設定 ---
st.set_page_config(page_title="新光醫院 AI 軟體評定", layout="wide")

# --- 2. 完整 16 條指標內容與權重定義 ---
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
    voter_name = st.text_input("您的姓名 (評審)", placeholder="姓名僅供後台核對用")

    user_scores = {}
    total = 0
    for cat, items in RUBRIC.items():
        st.markdown(f"### {cat}")
        for name, weight in items:
            score = st.slider(name, 0, 100, 70, 5, help=f"{RUBRIC_CONTENT.get(name)}\n\n滿分權重：{weight}分", key=name)
            w_score = (score/100)*weight
            user_scores[name] = w_score
            total += w_score

    st.divider()
    c = "green" if total >= 75 else "orange" if total >= 60 else "red"
    st.markdown(f"<h2 style='text-align:center;'>目前得分：<span style='color:{c}; font-size:60px;'>{total:.1f}</span></h2>", unsafe_allow_html=True)
    
    fb = st.text_area("💬 匿名評語 (建議)")
    if st.button("🚀 確認提交", use_container_width=True, type="primary"):
        if not voter_name: st.error("請輸入姓名"); return
        rec = {"Project": project_name, "Voter": voter_name, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Total Score": total, "Feedback": fb}
        rec.update(user_scores)
        pd.DataFrame([rec]).to_csv(FILE_NAME, mode='a', index=False, header=not os.path.exists(FILE_NAME))
        st.success("提交成功！"); st.balloons(); time.sleep(1); st.rerun()

def render_dashboard_page():
    """ 看板端：補齊 16 條，權重顯示，且分類標籤向右推 """
    if "current_project" not in st.session_state: st.session_state["current_project"] = None

    with st.sidebar:
        st.header("🗂️ 專案管理")
        projs = get_existing_projects()
        sel = st.radio("選擇專案：", projs if projs else ["尚未建立"], key="p_sel")
        if sel != "尚未建立": st.session_state["current_project"] = sel
        
        st.divider()
        with st.form("add_p"):
            n = st.text_input("新增專案")
            if st.form_submit_button("建立"):
                st.session_state["current_project"] = n; st.rerun()
        
        auto = st.toggle("🔄 自動刷新 (Live)", value=True)
        if st.button("🗑️ 清空所有數據"):
            if os.path.exists(FILE_NAME): os.remove(FILE_NAME); st.rerun()

    curr = st.session_state["current_project"]
    if not curr: st.info("👋 請選擇或新增評定專案。"); return

    st.markdown(f"<h1 style='text-align: center;'>📊 {curr} - 決策看板</h1>", unsafe_allow_html=True)
    
    # QR Code & Link
    link = f"https://shinkong-ai-vote.streamlit.app/?page=vote&project={urllib.parse.quote(curr)}"
    cl, cr = st.columns([1, 4])
    cl.image(f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={urllib.parse.quote(link)}")
    cr.markdown(f"**評分連結：**<br><code style='font-size:22px;'>{link}</code>", unsafe_allow_html=True)

    st.divider()

    if os.path.exists(FILE_NAME):
        df = pd.read_csv(FILE_NAME)
        df_p = df[df["Project"] == curr]
        if not df_p.empty:
            df_c = df_p.sort_values("Timestamp").drop_duplicates(subset=["Voter"], keep="last")
            avg = df_c["Total Score"].mean()

            # 決策顏色連動
            res = "推薦引進" if avg >= 75 else "修正後推薦" if avg >= 60 else "不推薦"
            clr = "#28a745" if avg >= 75 else "#ffc107" if avg >= 60 else "#dc3545"

            # 1. 核心指標 (配合決策結論變色)
            m1, m2, m3 = st.columns(3)
            def metric_html(label, val, unit=""):
                return f"<div style='text-align: center;'><p style='font-size: 26px; color: #555; margin-bottom: 0;'>{label}</p><p style='font-size: 85px; font-weight: bold; color: {clr}; margin-top: -10px;'>{val} <span style='font-size: 30px;'>{unit}</span></p></div>"
            
            m1.markdown(metric_html("已投人數", len(df_c), "人"), unsafe_allow_html=True)
            m2.markdown(metric_html("平均總分", f"{avg:.1f}"), unsafe_allow_html=True)
            m3.markdown(metric_html("目前決策", res), unsafe_allow_html=True)

            st.divider()
            
            # 2. 圖表區
            c_left, c_right = st.columns([2, 3])
            with c_left:
                st.markdown("### 🗳️ 投票結果分布")
                df_c["Status"] = df_c["Total Score"].apply(lambda s: "推薦引進" if s >= 75 else "修正後推薦" if s >= 60 else "不推薦")
                st_counts = df_c["Status"].value_counts().reset_index()
                st_counts.columns = ["類別", "票數"]
                pie = alt.Chart(st_counts).mark_arc(outerRadius=120).encode(
                    theta="票數", color=alt.Color("類別", scale=alt.Scale(domain=["推薦引進", "修正後推薦", "不推薦"], range=["#28a745", "#ffc107", "#dc3545"]), legend=alt.Legend(labelFontSize=18))
                ).properties(height=450)
                st.altair_chart(pie, use_container_width=True)

            with c_right:
                st.markdown("### 📈 16 項指標達成率 (%)")
                items = []
                for cat, crits in RUBRIC.items():
                    for name, w in crits:
                        val = df_c[name].mean() if name in df_c.columns else 0
                        items.append({
                            "指標項目": name, 
                            "達成率 (%)": round((val/w)*100, 1), 
                            "滿分權重": w,
                            "構面分類": cat.split(" ")[0]
                        })
                
                bar_df = pd.DataFrame(items)
                # 設定 Legend 向右偏移且字體加大
                bar = alt.Chart(bar_df).mark_bar().encode(
                    x=alt.X("達成率 (%)", scale=alt.Scale(domain=[0, 100]), axis=alt.Axis(labelFontSize=16, titleFontSize=18)), 
                    y=alt.Y("指標項目", sort=None, axis=alt.Axis(labelFontSize=18, labelLimit=500)), 
                    color=alt.Color("構面分類", legend=alt.Legend(
                        labelFontSize=16, 
                        titleFontSize=18,
                        offset=50, # 將分類標籤再向右推
                        orient='right'
                    )),
                    tooltip=["指標項目", "達成率 (%)", "滿分權重"]
                ).properties(height=550)
                
                txt = bar.mark_text(align='left', dx=5, fontSize=18, fontWeight='bold').encode(text='達成率 (%):Q')
                # 調整整個圖表的內部 Padding，為右邊標籤騰出空間
                st.altair_chart((bar + txt).configure_view(strokeWidth=0), use_container_width=True)

            # 3. 完整 16 條內容與「權重」
            st.divider()
            st.markdown("<h2 style='color: #1E90FF;'>📋 1-16 項評核指標定義與權重分配</h2>", unsafe_allow_html=True)
            gl, gr = st.columns(2)
            # 將指標名稱與權重重新組合成清單
            full_guide = []
            for cat, crits in RUBRIC.items():
                for name, w in crits:
                    full_guide.append((name, w, RUBRIC_CONTENT[name]))
            
            half = len(full_guide) // 2
            def show_g(items, col):
                for n, w, c in items:
                    col.markdown(f"""
                        <div style="background-color:#f8f9fa;padding:15px;border-radius:8px;margin-bottom:10px;border-left:5px solid #1E90FF;">
                            <span style="font-size:20px;font-weight:bold;color:#333;">{n} <span style="color:#ff4b4b;">(權重: {w}分)</span></span><br>
                            <span style="font-size:18px;color:#666;">{c}</span>
                        </div>
                    """, unsafe_allow_html=True)
            show_g(full_guide[:half], gl); show_g(full_guide[half:], gr)

            # 4. 匿名建議
            st.divider()
            st.markdown("<h2 style='color: #4B0082;'>💬 評審匿名建議回饋</h2>", unsafe_allow_html=True)
            fb_list = df_c[df_c["Feedback"].notna() & (df_c["Feedback"] != "")]["Feedback"].tolist()
            if fb_list:
                for i, msg in enumerate(fb_list, 1):
                    st.markdown(f"""<div style="background-color:#f0f2f6;padding:25px;border-radius:10px;margin-bottom:15px;border-left:10px solid #4B0082;"><span style="font-size:30px;font-weight:500;">{msg}</span></div>""", unsafe_allow_html=True)
            else: st.caption("尚未有意見回饋。")

    if auto: time.sleep(5); st.rerun()

# --- 5. 路由 ---
pg = st.query_params.get("page", "dashboard")
if pg == "vote": render_voting_page()
else: render_dashboard_page()
