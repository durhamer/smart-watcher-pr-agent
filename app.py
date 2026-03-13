# app.py
import streamlit as st

# 👉 引入我們的模組
from agents import AGENT_ROSTER
from ai_core import evaluate_pipeline, execute_crew
from admin_dashboard import render_admin_page  # 🚀 引入剛寫好的後台模組

st.set_page_config(page_title="Smart Watcher - 社群公關智囊團", page_icon="🤖", layout="wide")
st.title("Smart Watcher - 社群公關智囊團 🤖")

# 使用 Tabs 來打造雙頁面 UX
tab_main, tab_admin = st.tabs(["🚀 戰術執行大廳", "⚙️ 執行長後台管理"])

# ==========================================
# 📍 分頁 2：執行長後台管理 (必須先載入，以更新 Agent 狀態)
# ==========================================
with tab_admin:
    render_admin_page()  # 👈 沒錯，後台全部濃縮成這一行了！

# ==========================================
# 📍 分頁 1：戰術執行大廳
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
        if st.button("🚀 正式啟動團隊！", type="primary", use_container_width=True):
            api_key = st.secrets.get("GEMINI_API_KEY")
            serper_api_key = st.secrets.get("SERPER_API_KEY")
            if api_key and selected_agent_keys:
                with st.spinner("團隊執行中..."):
                    result, metrics = execute_crew(combined_info, selected_agent_keys, api_key, serper_api_key)
                    st.success("✨ 任務完成！")
                    
                    # 顯示最終產出
                    st.markdown("### 📝 最終產出：")
                    st.write(result)
                    
                    st.markdown("---")
                    
                    # 💰 擷取 Token 數量
                    p_tokens = metrics.get("prompt_tokens", 0)
                    c_tokens = metrics.get("completion_tokens", 0)
                    t_tokens = metrics.get("total_tokens", 0)
                    
                    # 🧮 計算估算成本 (假設使用 Flash 輕量級距)
                    # 輸入：每百萬 Token $0.10 USD / 輸出：每百萬 Token $0.40 USD
                    est_cost_usd = (p_tokens / 1_000_000 * 0.10) + (c_tokens / 1_000_000 * 0.40)
                    
                    # 📊 顯示升級版數據面板
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("輸入 Token", f"{p_tokens:,}")
                    col2.metric("輸出 Token", f"{c_tokens:,}")
                    col3.metric("總消耗", f"{t_tokens:,}")
                    
                    # 🚀 在這裡加上了明確的「美金」單位
                    col4.metric("💰 估算花費", f"${est_cost_usd:.5f} 美金")
                    
                    # ⚠️ 加上專屬警語
                    st.caption("⚠️ 警語：以上為基於 Flash 輕量模型的估算成本，實際上可能略有出入。")
