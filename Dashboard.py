import streamlit as st
import pandas as pd
import os
import time
import altair as alt
from datetime import datetime
import urllib.parse

# --- 1. 頁面設定 ---
st.set_page_config(page_title="新光醫院 AI 軟體評定", layout="wide")

# --- 2. 完整 16 條評核指標內容與權重定義 (總分 100) ---
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
VOTER_TYPE_COL = "Voter Type"
VOTER_TYPES = ["院內", "院外"]
UNKNOWN_VOTER_TYPE = "未分類"

def get_rubric_columns():
    cols = []
    for cat in RUBRIC:
        for name, weight in RUBRIC[cat]:
            cols.append(name)
    return cols

def get_csv_columns():
    return ["Project", "Voter", VOTER_TYPE_COL, "Timestamp", "Total Score", "Feedback"] + get_rubric_columns()

def append_record(record):
    ensure_csv()
    cols = pd.read_csv(FILE_NAME, nrows=0).columns.tolist()
    pd.DataFrame([record]).reindex(columns=cols).to_csv(FILE_NAME, mode='a', index=False, header=False)

# --- 3. 核心輔助函式 ---
def ensure_csv():
    """ 確保 CSV 檔案存在且具備正確欄位 """
    expected_cols = get_csv_columns()
    if not os.path.exists(FILE_NAME):
        pd.DataFrame(columns=expected_cols).to_csv(FILE_NAME, index=False)
        return

    df = pd.read_csv(FILE_NAME)
    changed = False
    if VOTER_TYPE_COL not in df.columns:
        df[VOTER_TYPE_COL] = UNKNOWN_VOTER_TYPE
        changed = True
    for col in expected_cols:
        if col not in df.columns:
            df[col] = ""
            changed = True
    extra_cols = [col for col in df.columns if col not in expected_cols]
    ordered_cols = expected_cols + extra_cols
    if df.columns.tolist() != ordered_cols:
        df = df.reindex(columns=ordered_cols)
        changed = True
    if changed:
        df[VOTER_TYPE_COL] = df[VOTER_TYPE_COL].fillna(UNKNOWN_VOTER_TYPE).replace("", UNKNOWN_VOTER_TYPE)
        df.to_csv(FILE_NAME, index=False)

def get_existing_projects():
    """ 取得所有已建立的專案名稱 """
    ensure_csv()
    try:
        df = pd.read_csv(FILE_NAME)
        return sorted([str(p) for p in df["Project"].dropna().unique().tolist() if str(p) != "SYSTEM_INIT"])
    except: return []

# --- 4. 頁面渲染：評審投票端 (手機版) ---
def render_voting_page():
    # 自動抓取網址中的專案名稱
    project_from_url = st.query_params.get("project", "")
    
    if not project_from_url:
        project_name = st.text_input("請輸入或確認專案名稱：")
    else:
        project_name = project_from_url
        st.markdown(f"## 📝 正在評估專案：**{project_name}**")

    if not project_name: 
        st.warning("⚠️ 未偵測到專案名稱，請重新掃描或手動輸入。")
        st.stop()

    voter_name = st.text_input("您的姓名 (評審)", placeholder="此姓名僅供內部核對")
    voter_type = st.radio("評審來源", VOTER_TYPES, horizontal=True)

    user_scores = {}
    total = 0
    for cat, items in RUBRIC.items():
        st.subheader(cat)
        for name, weight in items:
            score = st.slider(name, 0, 100, 70, 5, help=RUBRIC_CONTENT.get(name), key=f"vote_{name}")
            w_score = (score / 100) * weight
            user_scores[name] = w_score
            total += w_score

    st.divider()
    c = "green" if total >= 75 else "orange" if total >= 60 else "red"
    st.markdown(f"<h2 style='text-align:center;'>目前總計分數：<span style='color:{c}; font-size:60px;'>{total:.1f}</span></h2>", unsafe_allow_html=True)
    
    fb = st.text_area("💬 建議與回饋 (將匿名顯示在大螢幕)")
    
    if st.button("🚀 確認提交評分", use_container_width=True, type="primary"):
        if not voter_name: 
            st.error("❌ 請輸入姓名以供系統核對。")
        else:
            ensure_csv()
            rec = {"Project": project_name, "Voter": voter_name, VOTER_TYPE_COL: voter_type, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Total Score": total, "Feedback": fb}
            rec.update(user_scores)
            append_record(rec)
            st.success("✅ 提交成功！感謝您的評分。")
            st.balloons()
            time.sleep(1)
            st.rerun()

# --- 頁面渲染：決策看板端 (大螢幕) ---
def render_dashboard_page():
    if "current_project" not in st.session_state: 
        st.session_state["current_project"] = None

    # --- 側邊欄專案管理 ---
    with st.sidebar:
        st.header("🗂️ 專案管理")
        with st.form("new_proj", clear_on_submit=True):
            name = st.text_input("➕ 新增專案名稱")
            if st.form_submit_button("建立"):
                if name:
                    ensure_csv()
                    dummy = {"Project": name, "Voter": "SYSTEM_INIT", VOTER_TYPE_COL: "SYSTEM", "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Total Score": 0}
                    append_record(dummy)
                    st.session_state["current_project"] = name
                    st.rerun()

        st.divider()
        projs = get_existing_projects()
        if projs:
            idx = projs.index(st.session_state["current_project"]) if st.session_state["current_project"] in projs else 0
            sel = st.selectbox("🎯 切換目前專案：", projs, index=idx)
            st.session_state["current_project"] = sel
        
        auto = st.toggle("🔄 自動刷新 (Live)", value=True)
        
        # ✅ 清除資料確認機制 (使用 Popover)
        st.divider()
        with st.popover("🗑️ 清空所有數據", use_container_width=True):
            st.error("確定要清空所有專案與歷史評分嗎？此動作不可撤銷。")
            if st.button("🔴 確定刪除，不後悔", type="primary", use_container_width=True):
                if os.path.exists(FILE_NAME): os.remove(FILE_NAME)
                st.session_state.clear()
                st.rerun()

    curr = st.session_state["current_project"]
    if not curr: 
        st.info("👋 您好，請在左側新增或切換專案，開始進行 AI 評核。")
        return

    # 看板標題
    st.markdown(f"<h1 style='text-align: center;'>📊 {curr} - 決策看板</h1>", unsafe_allow_html=True)
    
    # QR Code 與 加大連結
    link = f"https://shinkong-ai-vote.streamlit.app/?page=vote&project={urllib.parse.quote(curr)}"
    col_l, col_r = st.columns([1, 4])
    with col_l:
        st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={urllib.parse.quote(link)}")
    with col_r:
        st.markdown(f"<div style='background-color:#f0f2f6; padding:15px; border-radius:10px;'><strong>手機評分網址：</strong><br><a href='{link}' style='font-size:24px; color:#1E90FF; word-break:break-all;'>{link}</a></div>", unsafe_allow_html=True)

    st.divider()

    # 數據呈現區
    if os.path.exists(FILE_NAME):
        df_all = pd.read_csv(FILE_NAME)
        df_p = df_all[(df_all["Project"] == curr) & (df_all["Voter"] != "SYSTEM_INIT")]
        
        if not df_p.empty:
            df_p = df_p.copy()
            if VOTER_TYPE_COL not in df_p.columns:
                df_p[VOTER_TYPE_COL] = UNKNOWN_VOTER_TYPE
            df_p[VOTER_TYPE_COL] = df_p[VOTER_TYPE_COL].fillna(UNKNOWN_VOTER_TYPE).replace("", UNKNOWN_VOTER_TYPE)

            group_options = ["全部"] + [t for t in VOTER_TYPES if t in df_p[VOTER_TYPE_COL].unique().tolist()]
            if UNKNOWN_VOTER_TYPE in df_p[VOTER_TYPE_COL].unique().tolist():
                group_options.append(UNKNOWN_VOTER_TYPE)
            selected_group = st.radio("統計範圍", group_options, horizontal=True)
            df_view = df_p if selected_group == "全部" else df_p[df_p[VOTER_TYPE_COL] == selected_group]

            if df_view.empty:
                st.warning(f"目前沒有「{selected_group}」的投票資料。")
                return

            df_c = df_view.sort_values("Timestamp").drop_duplicates(subset=["Voter", VOTER_TYPE_COL], keep="last")
            avg = df_c["Total Score"].mean()
            res = "推薦引進" if avg >= 75 else "修正後推薦" if avg >= 60 else "不推薦"
            clr = "#28a745" if avg >= 75 else "#ffc107" if avg >= 60 else "#dc3545"

            # 1. 頂部大數據 (變色連動)
            m1, m2, m3 = st.columns(3)
            def box(l, v): return f"<div style='text-align:center;'><p style='font-size:28px; color:#555;'>{l}</p><p style='font-size:85px; font-weight:bold; color:{clr}; margin-top:-20px;'>{v}</p></div>"
            m1.markdown(box("已投人數", len(df_c)), unsafe_allow_html=True)
            m2.markdown(box("平均總分", f"{avg:.1f}"), unsafe_allow_html=True)
            m3.markdown(box("決策結論", res), unsafe_allow_html=True)

            group_base = df_p.sort_values("Timestamp").drop_duplicates(subset=["Voter", VOTER_TYPE_COL], keep="last")
            group_summary = group_base.groupby(VOTER_TYPE_COL, as_index=False).agg(
                投票人數=("Voter", "count"),
                平均分數=("Total Score", "mean"),
            )
            group_summary["平均分數"] = group_summary["平均分數"].round(1)
            st.markdown("### 院內／院外統計")
            st.dataframe(group_summary, use_container_width=True, hide_index=True)

            st.divider()
            
            # 2. 圖表區域
            c_left, c_right = st.columns([2, 3])
            with c_left:
                st.markdown("### 🗳️ 投票分佈")
                df_c["Status"] = df_c["Total Score"].apply(lambda s: "推薦引進" if s >= 75 else "修正後推薦" if s >= 60 else "不推薦")
                st_counts = df_c["Status"].value_counts().reset_index()
                st_counts.columns = ["類別", "票數"]
                pie = alt.Chart(st_counts).mark_arc(outerRadius=120).encode(
                    theta="票數", 
                    color=alt.Color("類別", scale=alt.Scale(domain=["推薦引進", "修正後推薦", "不推薦"], range=["#28a745", "#ffc107", "#dc3545"]), legend=alt.Legend(labelFontSize=18))
                ).properties(height=450)
                st.altair_chart(pie, use_container_width=True)

            with c_right:
                st.markdown("### 📈 指標達成率 (%)")
                items = []
                for cat, crits in RUBRIC.items():
                    for n, w in crits:
                        v = df_c[n].mean() if n in df_c.columns else 0
                        items.append({"項": n, "率": round((v/w)*100, 1), "類": cat.split(" ")[0]})
                bar = alt.Chart(pd.DataFrame(items)).mark_bar().encode(
                    x=alt.X("率", scale=alt.Scale(domain=[0, 100])), 
                    y=alt.Y("項", sort=None, axis=alt.Axis(labelLimit=400, labelFontSize=16)), 
                    color="類"
                ).properties(height=500)
                st.altair_chart(bar + bar.mark_text(align='left', dx=5, fontSize=16, fontWeight='bold').encode(text='率:Q'), use_container_width=True)

            # 3. 匿名意見 (大字體)
            st.divider()
            st.markdown("<h2 style='color: #4B0082;'>💬 評審匿名建議回饋</h2>", unsafe_allow_html=True)
            fb_list = df_c[df_c["Feedback"].notna() & (df_c["Feedback"] != "")]["Feedback"].tolist()
            if fb_list:
                for i, msg in enumerate(fb_list, 1):
                    st.markdown(f"""<div style="background-color:#f0f2f6;padding:25px;border-radius:10px;margin-bottom:15px;border-left:10px solid #4B0082;"><span style="font-size:30px;font-weight:500;">{msg}</span></div>""", unsafe_allow_html=True)
            else: st.caption("尚未有意見回饋。")

            # 4. 投票歷程與 Log
            st.divider()
            with st.expander("🕒 完整投票紀錄與 Log", expanded=False):
                st.dataframe(df_p.sort_values("Timestamp", ascending=False), use_container_width=True)
                st.download_button("📥 下載完整數據 CSV", df_p.to_csv(index=False).encode('utf-8-sig'), f'{curr}_history.csv')
        else:
            st.warning("⚠️ 該專案目前尚未有正式數據，請由手機端開始評分。")

    # 5. 指標評核準則 (全域顯示一次)
    st.divider()
    st.markdown("<h2 style='color: #1E90FF;'>📋 1-16 項評核指標定義與權重分配</h2>", unsafe_allow_html=True)
    gl, gr = st.columns(2)
    full_guide = []
    for cat, crits in RUBRIC.items():
        for name, w in crits: full_guide.append((name, w, RUBRIC_CONTENT[name]))
    
    def show_g(items, col):
        for n, w, c in items:
            col.markdown(f'<div style="background-color:#f8f9fa;padding:15px;border-radius:8px;margin-bottom:10px;border-left:5px solid #1E90FF;"><span style="font-size:20px;font-weight:bold;color:#333;">{n} <span style="color:#ff4b4b;">({w}分)</span></span><br><span style="font-size:18px;color:#666;">{c}</span></div>', unsafe_allow_html=True)
    show_g(full_guide[:8], gl); show_g(full_guide[8:], gr)

    if auto: time.sleep(5); st.rerun()

# --- 5. 路由路由 ---
page = st.query_params.get("page", "dashboard")
if page == "vote": render_voting_page()
else: render_dashboard_page()
