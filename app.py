# app.py
import streamlit as st
import os  # 👉 新增 os 模組來檢查檔案是否存在

# 👉 引入員工名冊、核心邏輯與中央控制台
from agents import AGENT_ROSTER
from app_config import AI_MODELS
from ai_core import evaluate_pipeline, execute_crew

# --- 1. 網頁 UI 基本設定 ---
st.set_page_config(page_title="Smart Watcher - 社群公關智囊團", page_icon="🤖", layout="wide")
st.title("Smart Watcher - 社群公關智囊團 🤖")
st.markdown("輸入 Threads 上的貼文，勾選需要的團隊成員，讓 AI 為你執行客製化任務。")

# --- 2. 前端 UI：目標貼文與戰略設定區 ---
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

# --- 3. 前端 UI：執行長辦公室 (長期記憶寫入區) ---
st.markdown("### 🧠 novadata 執行長辦公室：特務教戰守則")
with st.expander("📝 檢視與寫入長期記憶 (pr_guidelines.txt)", expanded=False):
    guidelines_path = 'pr_guidelines.txt'
    
    # 讀取並顯示目前的記憶
    if os.path.exists(guidelines_path):
        with open(guidelines_path, 'r', encoding='utf-8') as f:
            current_guidelines = f.read()
        st.text_area("📄 目前已儲存的教戰守則：", value=current_guidelines, height=150, disabled=True)
    else:
        st.info("目前還沒有建立任何教戰守則，檔案將會在第一次寫入時自動建立。")

    # 寫入新記憶
    new_rule = st.text_area("你想教 AI 團隊什麼新規則？", placeholder="例如：以後只要提到特定對手，都必須維持中立偏悲觀的語氣；絕對不能使用『笑死』這個詞...")
    
    if st.button("💾 永久寫入特務大腦"):
        if new_rule:
            # 使用 append 模式 (a) 把新規則加到檔案最後面
            with open(guidelines_path, "a", encoding="utf-8") as f:
                f.write(f"\n- 【執行長最新指令】：{new_rule}")
            st.success("✅ 記憶已成功刻入！未來的任務特務都會遵守此規則。")
            st.rerun()  # 🚀 自動刷新網頁，讓上方的預覽框立刻顯示剛剛寫入的新規則！
        else:
            st.warning("請先輸入要教導的內容喔！")

st.markdown("---")

# --- 4. 前端 UI：選擇 Agent ---
st.markdown("### 👥 選擇與排序出任務的智囊團成員")
agent_options = {f"{config['icon']} {config['role']}": key for key, config in AGENT_ROSTER.items()}
# 👉 預設為空陣列，讓畫面保持乾淨
selected_display_names = st.multiselect("設定出勤名單與執行順序：", options=list(agent_options.keys()), default=[])
selected_agent_keys = [agent_options[name] for name in selected_display_names]

if selected_agent_keys:
    st.markdown("#### 📋 目前的流水線順序：")
    for i, key in enumerate(selected_agent_keys):
        config = AGENT_ROSTER[key]
        with st.expander(f"第 {i+1} 棒：{config['icon']} {config['role']}", expanded=True):
            st.markdown(f"**🎯 目標:** {config['goal']}")
else:
    st.warning("⚠️ 請至少挑選一位 Agent！")

st.markdown("---")

# --- 5. 執行核心邏輯 ---
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
            # 👉 拔除所有 Log 攔截，只顯示一個安靜的 Spinner 讓系統專心運作
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
