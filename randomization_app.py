import streamlit as st
import pandas as pd
import random
from datetime import datetime
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

# Google Sheets認証（Streamlit secrets対応）
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Randomization Log").sheet1

# 初期設定
GROUPS = ['Group A', 'Group B', 'Group C']
BLOCK_SIZE = 6
AGE = ['<75', '>=75']
DURATION = ['<18mo', '>=18mo']
BEV_FREE = ['<2mo', '>=2mo']

# 層別因子の組み合わせを作成
STRATA = [f"{age}_{dur}_{bev}" for age in AGE for dur in DURATION for bev in BEV_FREE]

if 'assignments' not in st.session_state:
    st.session_state.assignments = {s: [] for s in STRATA}
    for s in STRATA:
        for _ in range(10):
            block = GROUPS * (BLOCK_SIZE // len(GROUPS))
            random.shuffle(block)
            st.session_state.assignments[s].extend(block)

st.title("3群層別ブロックランダム化アプリ（Google Sheets保存版）")

with st.form("randomization_form"):
    subject_id = st.text_input("被験者ID")
    age_group = st.selectbox("年齢（75歳未満 / 以上）", AGE)
    duration_group = st.selectbox("治療期間（18か月未満 / 以上）", DURATION)
    bev_free_group = st.selectbox("BEV Free Interval（2か月未満 / 以上）", BEV_FREE)
    stratum = f"{age_group}_{duration_group}_{bev_free_group}"
    submitted = st.form_submit_button("割付実行")

    if submitted:
        if not subject_id:
            st.warning("被験者IDを入力してください")
        elif not st.session_state.assignments[stratum]:
            st.error(f"{stratum} の割付枠がありません。")
        else:
            group = st.session_state.assignments[stratum].pop(0)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            record = [subject_id, age_group, duration_group, bev_free_group, stratum, group, timestamp]
            sheet.append_row(record)
            st.success(f"{subject_id} は {group} に割り付けられました（層別: {stratum}）")

# ログ表示
st.subheader("最新の割付ログ（Google Sheetsより取得）")
try:
    records = sheet.get_all_records()
    if records:
        df = pd.DataFrame(records)
        st.dataframe(df)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="CSVとしてダウンロード",
            data=csv,
            file_name='randomization_log.csv',
            mime='text/csv'
        )
    else:
        st.info("まだ割付記録はありません")
except Exception as e:
    st.error(f"ログ取得中にエラーが発生しました: {e}")
