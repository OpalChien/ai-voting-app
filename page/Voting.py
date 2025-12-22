import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="評分問卷", layout="centered")

# --- 定義與 Dashboard 一致的標準 ---
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

st.header("📝 AI 軟體評估表")
st.markdown("請針對各項目滑動評分 (0-100)，完成後請點擊最下方的提交按鈕。")

# 投票表單
with st.form("vote_form"):
    voter_name = st.text_input("評審姓名 (請輸入您的姓名)", placeholder="例如：王大明醫師")
    
    scores = {}
    for category, criteria_list in RUBRIC.items():
        st.subheader(category)
        for criterion, weight in criteria_list:
            # 預設值 70 分
            scores[criterion] = st.slider(f"{criterion}", 0, 100, 70, key=criterion)
            st.caption(f"此題權重：{weight} 分")
    
    st.divider()
    submitted = st.form_submit_button("🚀 提交評分", use_container_width=True)

if submitted:
    if not voter_name:
        st.error("請輸入評審姓名後再提交！")
    else:
        # 計算邏輯
        vote_record = {"Voter": voter_name}
        total_weighted_score = 0
        
        for category, criteria_list in RUBRIC.items():
            for criterion, weight in criteria_list:
                raw_score = scores[criterion]
                # 加權分數 = (原始分數 / 100) * 權重
                weighted_score = (raw_score / 100) * weight
                vote_record[criterion] = weighted_score
                total_weighted_score += weighted_score
        
        vote_record["Total Score"] = total_weighted_score
        
        # 寫入 CSV
        df_new = pd.DataFrame([vote_record])
        if not os.path.exists(FILE_NAME):
            df_new.to_csv(FILE_NAME, index=False)
        else:
            df_new.to_csv(FILE_NAME, mode='a', header=False, index=False)
            
        st.success("✅ 評分已成功送出！請通知主持人查看即時結果。")
        st.balloons()