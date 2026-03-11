# admin_dashboard.py
import streamlit as st
import json
import gspread
from agents import AGENT_ROSTER

def render_admin_page():
    st.markdown("### 🔌 系統狀態：雲端資料庫連線")
    
    db_connected = False
    ws = None
    cloud_guidelines = ""
    
    try:
        # 使用 Streamlit Secrets 讀取 TOML 格式的 GCP 金鑰
        credentials_dict = dict(st.secrets["gcp_service_account"])
        gc = gspread.service_account_from_dict(credentials_dict)
        sh = gc.open("Smart_Watcher_DB")
        ws = sh.sheet1
        
        # --- 🛡️ 暴力初始化：確保 A1/B1 有標題 ---
        if not ws.acell('A1').value or ws.acell('A1').value.strip() == "":
            ws.update_acell('A1', 'Guidelines')
            ws.update_acell('B1', 'Settings')
            st.toast("🐣 檢測到新資料庫，已完成自動初始化標題！")
            
        # --- 🛡️ 處理 B2 (Settings JSON) ---
        cloud_settings_raw = ws.acell('B2').value
        if not cloud_settings_raw or cloud_settings_raw.strip() == "":
            cloud_settings = {}
            ws.update_acell('B2', '{}')
        else:
            try:
                cloud_settings = json.loads(cloud_settings_raw)
            except json.JSONDecodeError:
                cloud_settings = {}

        # --- 🛡️ 處理 A2 (Guidelines 文字) ---
        cloud_guidelines = ws.acell('A2').value or ""
        
        # 將雲端設定同步到記憶體中的 AGENT_ROSTER
        for key, settings in cloud_settings.items():
            if key in AGENT_ROSTER:
                AGENT_ROSTER[key].update(settings)
                
        db_connected = True
        st.success("✅ Google Sheets 資料庫同步完成！")
        
    except Exception as e:
        st.error(f"🚨 連線異常：{str(e)}")

    # --- 2. 介面：教戰守則 ---
    st.markdown("### 🧠 企業公關教戰守則")
    with st.container(border=True):
        st.text_area("📄 目前雲端儲存的守則：", value=cloud_guidelines, height=150, disabled=True)
        new_rule = st.text_area("你想教 AI 團隊什麼新規則？", placeholder="例如：回覆語氣要展現受過嚴格訓練的專家素養...")
        
        if st.button("💾 永久寫入雲端大腦"):
            if db_connected and new_rule:
                with st.spinner("同步中..."):
                    updated_guidelines = cloud_guidelines + f"\n- 【執行長最新指令】：{new_rule}"
                    ws.update_acell('A2', updated_guidelines)
                    # 同時寫入本機 pr_guidelines.txt 供 ai_core.py 讀取
                    with open("pr_guidelines.txt", "w", encoding="utf-8") as f:
                        f.write(updated_guidelines)
                st.success("✅ 記憶已更新！")
                st.rerun()
            elif not db_connected:
                st.warning("⚠️ 資料庫未連線，無法寫入。")

    # --- 3. 介面：特務裝備控制台 ---
    st.markdown("### 🎛️ 特務裝備與權限控制台")
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
        with st.spinner("同步設定至雲端..."):
            ws.update_acell('B2', json.dumps(updated_full_settings, ensure_ascii=False))
        st.success("✅ 設定已自動同步！")
        st.rerun()
