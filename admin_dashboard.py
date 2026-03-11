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
    
    # --- 1. 嘗試連線並拉取雲端資料 ---
    try:
        credentials_dict = dict(st.secrets["gcp_service_account"])
        gc = gspread.service_account_from_dict(credentials_dict)
        sh = gc.open("Smart_Watcher_DB")
        ws = sh.sheet1
        
        # 防呆機制：如果試算表是全空的，先幫你建立好欄位標題
        if not ws.acell('A1').value:
            ws.update(range_name='A1:B2', values=[['Guidelines', 'Settings'], ['', '{}']])
            
        # 讀取目前雲端資料
        cloud_guidelines = ws.acell('A2').value or ""
        cloud_settings_str = ws.acell('B2').value or "{}"
        cloud_settings = json.loads(cloud_settings_str)
        
        # 動態覆蓋 AGENT_ROSTER 狀態
        for key, settings in cloud_settings.items():
            if key in AGENT_ROSTER:
                AGENT_ROSTER[key].update(settings)
                
        db_connected = True
        st.success("✅ Google Sheets 資料庫同步完成！")
        
    except Exception as e:
        st.error(f"🚨 資料庫連線失敗，請檢查金鑰或試算表名稱：{e}")

    # --- 2. 介面：企業公關教戰守則 ---
    st.markdown("### 🧠 企業公關教戰守則 (Google Sheets 即時同步)")
    with st.container(border=True):
        st.text_area("📄 目前雲端儲存的教戰守則：", value=cloud_guidelines, height=150, disabled=True)
        new_rule = st.text_area("你想教 AI 團隊什麼新規則？", placeholder="例如：以後只要提到特定對手，都必須維持中立偏悲觀的語氣...")
        
        if st.button("💾 永久寫入雲端大腦"):
            if db_connected and new_rule:
                with st.spinner("正在寫入 Google Sheets..."):
                    updated_guidelines = cloud_guidelines + f"\n- 【執行長最新指令】：{new_rule}"
                    ws.update_acell('A2', updated_guidelines)
                    # 順便把文字存一份到本機的 pr_guidelines.txt，讓 AI 執行時可以讀取
                    with open("pr_guidelines.txt", "w", encoding="utf-8") as f:
                        f.write(updated_guidelines)
                st.success("✅ 記憶已成功刻入雲端！")
                st.rerun()
            elif not db_connected:
                st.warning("⚠️ 資料庫未連線，無法寫入。")
            else:
                st.warning("⚠️ 請先輸入要教導的內容喔！")

    # --- 3. 介面：特務裝備控制台 ---
    st.markdown("### 🎛️ 特務裝備與權限控制台")
    settings_changed = False
    new_settings = {}

    for key, config in AGENT_ROSTER.items():
        with st.expander(f"{config['icon']} {config['role']} ({key})", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            current_search = config.get("needs_search", False)
            current_guide = config.get("needs_guidelines", False)
            current_memory = config.get("memory", False)

            toggle_search = col1.toggle("🌐 網路搜尋", value=current_search, key=f"search_{key}")
            toggle_guide = col2.toggle("📖 閱讀教戰守則", value=current_guide, key=f"guide_{key}")
            toggle_memory = col3.toggle("🧠 獨立記憶", value=current_memory, key=f"mem_{key}")

            new_settings[key] = {
                "needs_search": toggle_search,
                "needs_guidelines": toggle_guide,
                "memory": toggle_memory
            }

            if toggle_search != current_search or toggle_guide != current_guide or toggle_memory != current_memory:
                settings_changed = True

    if settings_changed and db_connected:
        with st.spinner("正在同步設定至 Google Sheets..."):
            ws.update_acell('B2', json.dumps(new_settings, ensure_ascii=False))
        st.success("✅ 設定已自動同步至雲端大腦！")
        st.rerun()
