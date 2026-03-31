import streamlit as st
import pandas as pd
import os
import time
import altair as alt
from datetime import datetime
import urllib.parse

# --- 1. 頁面設定 ---
st.set_page_config(page_title="新光醫院 AI 軟體評定", layout="wide")

# --- 2. 完整 16 條指標與權重 (保持不變) ---
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

# --- 3. 核心輔助函式：確保 CSV 結構存在 ---
def ensure_csv():
    if not os.path.exists(FILE_NAME):
        # 建立包含所有欄位的空 DataFrame
        cols = ["Project", "Voter", "Timestamp", "Total Score", "Feedback"]
        for cat in RUBRIC:
            for name, weight in RUBRIC[cat]:
                cols.append(name)
        df_empty = pd.DataFrame(columns=cols)
        df_empty.to_csv(FILE_NAME, index=False)

def get_existing_projects():
    ensure_csv()
    try:
        df = pd.read_csv(FILE_NAME)
        return sorted([str(p) for p in df["Project"].dropna().unique().tolist()])
    except:
        return []

# --- 4. 頁面渲染 ---

def render_voting_page():
    project_name = st.query_params.get("project", st.text_input("專案名稱："))
    if not project_name: st.stop()

    st.markdown(f"## 📝 正在評審：{project_name}")
    voter = st.text_input("您的姓名")

    user_scores = {}
    total = 0
    for cat, items in RUBRIC.items():
        st.subheader(cat)
        for name, weight in items:
            score = st.slider(name, 0, 100, 70, 5, help=f"權重：{weight}")
            w_score = (score/100)*weight
            user_scores[name] = w_score
            total += w_score

    if st.button("🚀 提交評分", use_container_width=True, type="primary"):
        if not voter: st.error("請輸入姓名"); return
        ensure_csv()
        rec = {"Project": project_name, "Voter": voter, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Total Score": total}
        rec.update(user_scores)
        pd.DataFrame([rec]).to_csv(FILE_NAME, mode='a', index=False, header=False)
        st.success("提交成功！"); st.rerun()

def render_dashboard_page():
    if "current_project" not in st.session_state: st.session_state["current_project"] = None

    with st.sidebar:
        st.header("🗂️ 專案管理")
        
        # 修正：直接建立空的專案紀錄到 CSV，確保清單立刻更新
        with st.form("new_proj", clear_on_submit=True):
            name = st.text_input("➕ 新增專案")
            if st.form_submit_button("建立"):
                if name:
                    ensure_csv()
                    # 建立一筆預設資料讓 CSV 記住專案名稱
                    dummy = {"Project": name, "Voter": "SYSTEM_INIT", "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                    pd.DataFrame([dummy]).to_csv(FILE_NAME, mode='a', index=False, header=False)
                    st.session_state["current_project"] = name
                    st.rerun()

        st.divider()
        projs = get_existing_projects()
        if projs:
            idx = projs.index(st.session_state["current_project"]) if st.session_state["current_project"] in projs else 0
            sel = st.selectbox("🎯 切換專案：", projs, index=idx)
            st.session_state["current_project"] = sel
        
        auto = st.toggle("🔄 自動刷新", value=True)
        if st.button("🗑️ 清空所有資料"):
            if os.path.exists(FILE_NAME): os.remove(FILE_NAME)
            st.session_state["current_project"] = None
            st.rerun()

    curr = st.session_state["current_project"]
    if not curr:
        st.info("請在左側『新增專案』。")
        return

    st.title(f"📊 {curr} - 決議看板")
    
    # QR Code
    link = f"https://shinkong-ai-vote.streamlit.app/?page=vote&project={urllib.parse.quote(curr)}"
    c1, c2 = st.columns([1, 4])
    c1.image(f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={urllib.parse.quote(link)}")
    c2.markdown(f"**連結：**<br><code>{link}</code>", unsafe_allow_html=True)

    st.divider()

    if os.path.exists(FILE_NAME):
        df = pd.read_csv(FILE_NAME)
        # 過濾掉初始化用的系統紀錄
        df_p = df[(df["Project"] == curr) & (df["Voter"] != "SYSTEM_INIT")]
        
        if not df_p.empty:
            df_c = df_p.sort_values("Timestamp").drop_duplicates(subset=["Voter"], keep="last")
            avg = df_c["Total Score"].mean()
            res = "推薦引進" if avg >= 75 else "修正後推薦" if avg >= 60 else "不推薦"
            clr = "#28a745" if avg >= 75 else "#ffc107" if avg >= 60 else "#dc3545"

            # 數據特大字體
            col1, col2, col3 = st.columns(3)
            def box(l, v): return f"<div style='text-align:center;'><p style='font-size:26px;'>{l}</p><p style='font-size:80px; font-weight:bold; color:{clr};'>{v}</p></div>"
            col1.markdown(box("已投人數", len(df_c)), unsafe_allow_html=True)
            col2.markdown(box("平均總分", f"{avg:.1f}"), unsafe_allow_html=True)
            col3.markdown(box("目前決策", res), unsafe_allow_html=True)

            st.divider()
            # 圖表 (16項達成率)
            items = []
            for cat, crits in RUBRIC.items():
                for n, w in crits:
                    v = df_c[n].mean() if n in df_c.columns else 0
                    items.append({"項": n, "率": round((v/w)*100, 1), "類": cat.split(" ")[0]})
            bar = alt.Chart(pd.DataFrame(items)).mark_bar().encode(
                x=alt.X("率", scale=alt.Scale(domain=[0, 100])), y=alt.Y("項", sort=None), color="類"
            ).properties(height=500)
            st.altair_chart(bar + bar.mark_text(align='left', dx=5, fontSize=18).encode(text='率:Q'), use_container_width=True)
        else:
            st.warning("目前尚無評分數據。")

    # 顯示 16 條準則說明
    st.divider()
    st.markdown("### 📋 1-16 項指標定義與權重")
    gl, gr = st.columns(2)
    full = []
    for cat, crits in RUBRIC.items():
        for n, w in crits: full.append((n, w, RUBRIC_CONTENT[n]))
    def show_g(its, col):
        for n, w, c in its:
            col.markdown(f'<div style="background-color:#f8f9fa;padding:10px;margin-bottom:5px;border-left:5px solid #1E90FF;"><b>{n} ({w}分)</b><br><small>{c}</small></div>', unsafe_allow_html=True)
    show_g(full[:8], gl); show_g(full[8:], gr)

    if auto: time.sleep(5); st.rerun()

# --- 5. 路由 ---
if st.query_params.get("page") == "vote": render_voting_page()
else: render_dashboard_page()
