# app.py
import streamlit as st
import os
import json

# 👉 引入員工名冊、核心邏輯與中央控制台
from agents import AGENT_ROSTER
from app_config import AI_MODELS
from ai_core import evaluate_pipeline, execute_crew

# --- 0. 動態設定檔載入機制 (UX 升級核心) ---
# 建立一個 JSON 檔案來持久化儲存你在網頁上切換的 True/False 開關
SETTINGS_FILE = 'agent_settings.json'

# 如果有儲存過的設定，就在系統啟動時動態覆寫到 AGENT_ROSTER 上
if os.path.exists(SETTINGS_FILE):
    with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
        saved_settings = json.load(f)
        for key, settings in saved_settings.items():
            if key in AGENT_ROSTER:
                AGENT_ROSTER[key].update(settings)

# --- 1. 網頁 UI 基本設定 ---
st.set_page_config(page_title="Smart Watcher - 社群公關智囊團", page_icon="🤖", layout="wide")
st.title("Smart Watcher - 社群公關智囊團 🤖")

# 🚀 使用 Tabs 來打造雙頁面 UX
tab_main, tab_admin = st.tabs(["🚀 戰術執行大廳", "⚙️ 執行長後台管理"])

# ==========================================
# 📍 分頁 1：戰術執行大廳 (日常操作區)
# ==========================================
with tab_main:
    st.markdown("### 🎯 戰術情報台 (輸入貼文與目的)")
    col_info, col_strategy = st.columns([1.2, 1])

    with col_info:
        post_content = st.text_area("📝 1. 原貼文內容：", height=120)
        comment_content = st.text_area("💬 2. 精選留言區：", height=120)

    with col_strategy:
        strategy_goal = st.text_area("🎯 3. 你的戰略目的 (給小編的秘密指令)：", height=300)

    combined_info = f"""
    【原貼文內容】：\n{post_content if post_content else "無"}
    【網友留言區】：\n{comment_content if comment_content else "無"}
    【老闆下達的戰略目的】：\n{strategy_goal if strategy_goal else "請依據上述內容自由發揮。"}
    """

    st.markdown("### 👥 選擇與排序出任務的智囊團成員")
    agent_options = {f"{config['icon']} {config['role']}": key for key, config in AGENT_ROSTER.items()}
    selected_display_names = st.multiselect("設定出勤名單與執行順序：", options=list(agent_options.keys()), default=[])
    selected_agent_keys = [agent_options[name] for name in selected_display_names]

    if selected_agent_keys:
        st.markdown("#### 📋 目前的流水線順序：")
        for i, key in enumerate(selected_agent_keys):
            config = AGENT_ROSTER[key]
            with st.expander(f"第 {i+1} 棒：{config['icon']} {config['role']}", expanded=True):
                st.markdown(f"**🎯 目標:** {config['goal']}")
                
                # 👉 UX 貼心小設計：在首頁也能一眼看穿特務帶了哪些裝備
                badges = []
                if config.get("needs_search"): badges.append("🌐 網路搜尋")
                if config.get("needs_guidelines"): badges.append("📖 教戰守則")
                if config.get("memory"): badges.append("🧠 獨立記憶")
                if badges:
                    st.caption(f"🎒 目前裝備：{' | '.join(badges)}")
    else:
        st.warning("⚠️ 請至少挑選一位 Agent！")

    st.markdown("---")

    col_check, col_run = st.columns(2)

    with col_check:
        if st.button("🕵️ 先幫我檢查流水線邏輯", use_container_width=True):
            api_key = st.secrets.get("GEMINI_API_KEY")
            if api_key and selected_agent_keys:
                with st.spinner("AI 架構師正在審查..."):
                    try:
                        final_text, base_tokens = evaluate_pipeline(combined_info, selected_agent_keys, api_key)
                        st.info(f"**🕵️ 點評：**\n\n{final_text}")
                        st.warning(f"📊 **Token 消耗預估：** 約 {base_tokens} Tokens。")
                    except Exception as e:
                        st.error(f"🚨 錯誤：{str(e)}")

    with col_run:
        if st.button("🚀 確認無誤，正式啟動團隊！", type="primary", use_container_width=True):
            api_key = st.secrets.get("GEMINI_API_KEY")
            serper_api_key = st.secrets.get("SERPER_API_KEY")
            if api_key and serper_api_key and selected_agent_keys:
                with st.spinner("🕵️‍♂️ 特務團隊正在後台秘密查證與撰寫中，這可能需要 1~2 分鐘，請耐心稍候..."):
                    try:
                        result_text, metrics = execute_crew(combined_info, selected_agent_keys, api_key, serper_api_key)
                        st.success("✨ 任務完成！")
                        st.subheader("📝 最終產出：")
                        st.write(result_text)
                        st.markdown("---")
                        col1, col2, col3 = st.columns(3)
                        col1.metric("輸入 Token", metrics["prompt_tokens"])
                        col2.metric("輸出 Token", metrics["completion_tokens"])
                        col3.metric("總消耗", metrics["total_tokens"])
                    except Exception as e:
                        st.error(f"🚨 錯誤：{str(e)}")

# ==========================================
# 📍 分頁 2：執行長後台管理 (權限與記憶控制)
# ==========================================
with tab_admin:
    # 👇 雲端專用的資料庫連線測試儀表板 👇
    st.markdown("### 🔌 系統狀態：雲端資料庫連線測試")
    with st.container(border=True):
        if st.button("🔄 點我測試 Google Sheets API 連線", use_container_width=True):
            import gspread
            try:
                with st.spinner("正在打開 Streamlit 金庫拿鑰匙..."):
                    # 🚀 改變在這裡：直接把 Secrets 轉換成 gspread 看得懂的字典格式
                    credentials_dict = dict(st.secrets["gcp_service_account"])
                    gc = gspread.service_account_from_dict(credentials_dict)
                    
                    st.info("鑰匙驗證成功！正在尋找 Google 試算表...")
                    sh = gc.open("Smart_Watcher_DB") # 請確保你的試算表名字跟這裡一模一樣！
                    worksheet = sh.sheet1
                    
                    # 嘗試寫入並讀取
                    worksheet.update_acell('A1', '🎉 Smart Watcher 雲端系統連線成功！')
                    val = worksheet.acell('A1').value
                    
                    st.success(f"✅ 連線完美通過！已成功讀取回傳值：【{val}】")
            except Exception as e:
                st.error(f"🚨 連線失敗，請檢查設定：\n{e}")
    st.markdown("### 🧠 企業公關教戰守則 (pr_guidelines.txt)")
    with st.container(border=True):
        guidelines_path = 'pr_guidelines.txt'
        if os.path.exists(guidelines_path):
            with open(guidelines_path, 'r', encoding='utf-8') as f:
                current_guidelines = f.read()
            st.text_area("📄 目前已儲存的教戰守則：", value=current_guidelines, height=150, disabled=True)
        else:
            st.info("目前還沒有建立任何教戰守則，檔案將會在第一次寫入時自動建立。")

        new_rule = st.text_area("你想教 AI 團隊什麼新規則？", placeholder="例如：以後只要提到特定對手，都必須維持中立偏悲觀的語氣...")
        
        if st.button("💾 永久寫入特務大腦"):
            if new_rule:
                with open(guidelines_path, "a", encoding="utf-8") as f:
                    f.write(f"\n- 【執行長最新指令】：{new_rule}")
                st.success("✅ 記憶已成功刻入！")
                st.rerun()
            else:
                st.warning("請先輸入要教導的內容喔！")

    st.markdown("### 🎛️ 特務裝備與權限控制台")
    st.markdown("在這裡你可以隨時開關特務身上的裝備，系統會自動儲存你的設定，下一次出任務即刻生效。")
    
    # 建立變數來追蹤是否有設定被更改
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

            # 暫存這個 Agent 的最新狀態
            new_settings[key] = {
                "needs_search": toggle_search,
                "needs_guidelines": toggle_guide,
                "memory": toggle_memory
            }

            # 檢查是否有任何狀態被你按下了切換
            if toggle_search != current_search or toggle_guide != current_guide or toggle_memory != current_memory:
                settings_changed = True

    # 如果有開關被切換，就寫入 JSON 檔案並強制重整網頁以套用新設定
    if settings_changed:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(new_settings, f, ensure_ascii=False, indent=4)
        st.success("✅ 設定已自動儲存！")
        st.rerun()
