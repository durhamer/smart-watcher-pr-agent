# admin_dashboard.py
import streamlit as st
import json
import gspread
from agents import AGENT_ROSTER

def render_admin_page():
    # --- 🏗️ 區塊 A：雲端資料庫狀態與強制同步 ---
    st.markdown("### 🔌 系統狀態：雲端資料庫控制台")
    
    db_connected = False
    ws = None
    cloud_guidelines = ""

    # 定義一個共用的連線函數
    def get_gsheet_connection():
        try:
            credentials_dict = dict(st.secrets["gcp_service_account"])
            gc = gspread.service_account_from_dict(credentials_dict)
            sh = gc.open("Smart_Watcher_DB")
            return sh.sheet1
        except Exception as e:
            st.error(f"❌ 無法連線至 Google Sheets: {e}")
            return None

    # 1. 建立「手動強制初始化/同步」按鈕
    col_status, col_sync = st.columns([2, 1])
    
    with col_sync:
        if st.button("🔄 強制同步雲端資料庫", use_container_width=True):
            ws = get_gsheet_connection()
            if ws:
                with st.spinner("正在強制寫入標題與格式..."):
                    # 暴力寫入標題與預設值
                    ws.update_acell('A1', 'Guidelines')
                    ws.update_acell('B1', 'Settings')
                    # 檢查 B2 是否有設定，沒有就補 {}
                    if not ws.acell('B2').value:
                        ws.update_acell('B2', '{}')
                    st.toast("🚀 雲端資料庫已強制初始化並同步！")
                    st.rerun()

    # 2. 啟動時自動拉取最新資料 (保持原本的唯讀讀取邏輯)
    ws = get_gsheet_connection()
    if ws:
        try:
            # 讀取雲端資料
            cloud_settings_raw = ws.acell('B2').value or "{}"
            cloud_settings = json.loads(cloud_settings_raw)
            cloud_guidelines = ws.acell('A2').value or ""
            
            # 同步至本地 AGENT_ROSTER
            for key, settings in cloud_settings.items():
                if key in AGENT_ROSTER:
                    AGENT_ROSTER[key].update(settings)
            
            db_connected = True
            st.success("✅ 目前與雲端資料同步中")
        except Exception as e:
            st.warning(f"⚠️ 資料解析中：{e}")

    st.markdown("---")

    # --- 🏗️ 區塊 B：教戰守則管理 ---
    st.markdown("### 🧠 企業公關教戰守則")
    with st.container(border=True):
        st.text_area("📄 雲端目前儲存的守則：", value=cloud_guidelines, height=150, disabled=True)
        new_rule = st.text_area("你想教 AI 團隊什麼新規則？", placeholder="輸入後點擊下方按鈕存入雲端...")
        
        if st.button("💾 永久寫入雲端大腦", type="primary"):
            if db_connected and new_rule:
                with st.spinner("正在上傳至 Google Sheets..."):
                    updated_guidelines = cloud_guidelines + f"\n- 【執行長最新指令】：{new_rule}"
                    ws.update_acell('A2', updated_guidelines)
                    # 同步更新本機暫存檔
                    with open("pr_guidelines.txt", "w", encoding="utf-8") as f:
                        f.write(updated_guidelines)
                st.success("✅ 雲端守則已更新！")
                st.rerun()

    # --- 🏗️ 區塊 C：特務裝備控制台 ---
    st.markdown("### 🎛️ 特務裝備權限 (自動同步)")
    settings_changed = False
    updated_full_settings = {}

    for key, config in AGENT_ROSTER.items():
        with st.expander(f"{config['icon']} {config['role']} ({key})"):
            col1, col2, col3 = st.columns(3)
            
            c_search = config.get("needs_search", False)
            c_guide = config.get("needs_guidelines", False)
            c_mem = config.get("memory", False)

            t_search = col1.toggle("🌐 搜尋", value=c_search, key=f"s_{key}")
            t_guide = col2.toggle("📖 守則", value=c_guide, key=f"g_{key}")
            t_mem = col3.toggle("🧠 記憶", value=c_mem, key=f"m_{key}")

            updated_full_settings[key] = {
                "needs_search": t_search,
                "needs_guidelines": t_guide,
                "memory": t_mem
            }

            if t_search != c_search or t_guide != c_guide or t_mem != c_mem:
                settings_changed = True

    if settings_changed and db_connected:
        with st.spinner("同步設定中..."):
            ws.update_acell('B2', json.dumps(updated_full_settings, ensure_ascii=False))
        st.success("✅ 裝備設定已同步至雲端！")
        st.rerun()
