import streamlit as st
import pandas as pd
import os
import time

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

FILE_NAME = "vote_data.csv"

# --- 3. 定義功能函式 ---

def render_voting_page():
    """ 顯示投票介面 """
    st.header("📝 AI 軟體評估表決")
    st.markdown("請針對各項目進行評分，完成後點擊提交。")

    with st.form("vote_form"):
        voter_name = st.text_input("您的姓名 (評審)", placeholder="例如：王醫師")
        
        scores = {}
        for category, criteria_list in RUBRIC.items():
            st.subheader(category)
            for criterion, weight in criteria_list:
                scores[criterion] = st.slider(f"{criterion}", 0, 100, 70, key=criterion)
                st.caption(f"此題權重：{weight} 分")
        
        st.divider()
        submitted = st.form_submit_button("🚀 提交評分", use_container_width=True)

    if submitted:
        if not voter_name:
            st.error("請輸入姓名！")
        else:
            vote_record = {"Voter": voter_name}
            total_weighted_score = 0
            
            for category, criteria_list in RUBRIC.items():
                for criterion, weight in criteria_list:
                    raw_score = scores[criterion]
                    weighted_score = (raw_score / 100) * weight
                    vote_record[criterion] = weighted_score
                    total_weighted_score += weighted_score
            
            vote_record["Total Score"] = total_weighted_score
            
            df_new = pd.DataFrame([vote_record])
            if not os.path.exists(FILE_NAME):
                df_new.to_csv(FILE_NAME, index=False)
            else:
                df_new.to_csv(FILE_NAME, mode='a', header=False, index=False)
                
            st.success("✅ 評分已送出！您可以關閉此頁面。")
            st.balloons()

def render_dashboard_page():
    """ 顯示大螢幕儀表板 """
    st.title("📊 新光醫院 AI 軟體評估 - 決策看板")
    
    # 側邊欄控制
    with st.sidebar:
        st.header("⚙️ 控制台")
        # 自動抓取當前網址 (如果抓不到，預設為空)
        default_url = "https://shinkong-ai-vote.streamlit.app" 
        base_url = st.text_input("確認 App 主網址", value=default_url)
        
        # 產生帶參數的投票連結
        vote_link = f"{base_url}/?page=vote"
        
        st.divider()
        if st.button("🔄 刷新數據"):
            st.rerun()
        if st.button("⚠️ 清除所有數據"):
            if os.path.exists(FILE_NAME):
                os.remove(FILE_NAME)
                st.success("已清除！")
                time.sleep(1)
                st.rerun()

    # QR Code 區塊
    col_qr, col_info = st.columns([1, 4])
    with col_qr:
        # 產生 QR Code 指向帶參數的網址
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={vote_link}"
        st.image(qr_url, caption="掃碼進入投票")
    with col_info:
        st.info("💡 請評審掃描左側 QR Code 進入評分頁面")
        st.markdown(f"**投票連結：** `{vote_link}`")

    st.divider()

    # 數據顯示
    if os.path.exists(FILE_NAME):
        try:
            df = pd.read_csv(FILE_NAME)
            if not df.empty:
                # KPI
                avg = df["Total Score"].mean()
                c1, c2, c3 = st.columns(3)
                c1.metric("已投票人數", f"{len(df)} 人")
                c2.metric("平均總分", f"{avg:.1f}")
                
                result = "推薦 (Pass)" if avg >= 75 else "修正後推薦" if avg >= 60 else "不推薦"
                color = "green" if avg >= 75 else "orange" if avg >= 60 else "red"
                c3.markdown(f"建議：:{color}[{result}]")
                
                # 圖表
                st.subheader("各構面達成率")
                cat_scores = {}
                for cat, criteria in RUBRIC.items():
                    total_w = sum(w for c, w in criteria)
                    cols = [c for c, w in criteria]
                    if all(c in df.columns for c in cols):
                        actual = df[cols].sum(axis=1).mean()
                        cat_scores[cat.split(" ")[0]] = (actual / total_w) * 100
                
                if cat_scores:
                    st.bar_chart(pd.DataFrame(cat_scores.items(), columns=["構面", "%"]), x="構面", y="%")
                
                # 詳細資料
                with st.expander("查看詳細紀錄"):
                    st.dataframe(df)

                time.sleep(3)
                st.rerun()
            else:
                st.warning("尚無投票資料...")
                time.sleep(3)
                st.rerun()
        except:
            pass
    else:
        st.warning("等待投票中...")
        time.sleep(3)
        st.rerun()

# --- 4. 路由控制 (核心邏輯) ---
# 檢查網址參數 ?page=vote
query_params = st.query_params
page = query_params.get("page", "dashboard")

if page == "vote":
    render_voting_page()
else:
    render_dashboard_page()
