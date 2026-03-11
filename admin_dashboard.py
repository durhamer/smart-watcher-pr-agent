# admin_dashboard.py 終極穩定版
import streamlit as st
import json
import gspread
from agents import AGENT_ROSTER

def render_admin_page():
    st.markdown("### 🔌 系統狀態：雲端資料庫控制台")
    
    # --- 內部連線工具 ---
    def get_ws():
        try:
            creds = dict(st.secrets["gcp_service_account"])
            gc = gspread.service_account_from_dict(creds)
            return gc.open("Smart_Watcher_DB").sheet1
        except Exception as e:
            st.error(f"連線失敗: {e}")
            return None

    # 初始化連線
    ws = get_ws()
    db_connected = ws is not None
    cloud_guidelines = ""
    cloud_settings = {}

    if db_connected:
        try:
            # 強制讀取最新值
            cloud_guidelines = ws.acell('A2').value or ""
            settings_raw = ws.acell('B2').value or "{}"
            cloud_settings = json.loads(settings_raw)
            
            # 同步到記憶體
            for k, v in cloud_settings.items():
                if k in AGENT_ROSTER: AGENT_ROSTER[k].update(v)
            st.success("✅ 與雲端資料同步中")
        except:
            st.warning("⚠️ 雲端資料格式初始化中...")

    # --- 區塊 1：手動同步按鈕 ---
    if st.button("🔄 重新連線並強制初始化標題"):
        ws = get_ws()
        if ws:
            ws.update_acell('A1', 'Guidelines')
            ws.update_acell('B1', 'Settings')
            if not ws.acell('B2').value: ws.update_acell('B2', '{}')
            st.toast("同步成功！")
            st.rerun()

    st.markdown("---")

    # --- 區塊 2：教戰守則 ---
    st.markdown("### 🧠 企業公關教戰守則")
    with st.container(border=True):
        st.text_area("📄 雲端儲存內容：", value=cloud_guidelines, height=100, disabled=True)
        new_rule = st.text_area("寫入新指令：", key="new_rule_input")
        
        if st.button("💾 執行寫入"):
            if db_connected and new_rule:
                with st.spinner("寫入中..."):
                    # 🚀 關鍵修正：重新取得 ws 確保連線未逾時
                    fresh_ws = get_ws()
                    updated_text = cloud_guidelines + f"\n- {new_rule}"
                    fresh_ws.update_acell('A2', updated_text)
                    # 同步本地
                    with open("pr_guidelines.txt", "w", encoding="utf-8") as f:
                        f.write(updated_text)
                st.success("寫入成功！")
                st.rerun()

    # --- 區塊 3：特務裝備 ---
    st.markdown("### 🎛️ 特務裝備權限")
    current_full_settings = {}
    any_toggle_changed = False

    for key, config in AGENT_ROSTER.items():
        with st.expander(f"{config['icon']} {config['role']}"):
            col1, col2, col3 = st.columns(3)
            # 使用更唯一的 key 避免衝突
            t_s = col1.toggle("搜尋", value=config.get("needs_search", False), key=f"ts_{key}")
            t_g = col2.toggle("守則", value=config.get("needs_guidelines", False), key=f"tg_{key}")
            t_m = col3.toggle("記憶", value=config.get("memory", False), key=f"tm_{key}")

            current_full_settings[key] = {"needs_search": t_s, "needs_guidelines": t_g, "memory": t_m}
            
            if t_s != config.get("needs_search") or t_g != config.get("needs_guidelines") or t_m != config.get("memory"):
                any_toggle_changed = True

    # 🚀 關鍵修正：當開關變動時，明確調用寫入
    if any_toggle_changed and db_connected:
        fresh_ws = get_ws()
        fresh_ws.update_acell('B2', json.dumps(current_full_settings, ensure_ascii=False))
        st.toast("設定已同步雲端")
        st.rerun()
