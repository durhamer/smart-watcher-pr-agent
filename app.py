# app.py
import streamlit as st
import sys

# 👉 每次網頁刷新時，強制還原通道避免當機
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__

# 👉 引入員工名冊、工具與中央控制台 (已更新為 app_config)
from agents import AGENT_ROSTER
from app_config import AI_MODELS
from utils import StreamToExpander
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

# --- 3. 前端 UI：選擇 Agent ---
st.markdown("### 👥 選擇與排序出任務的智囊團成員")
agent_options = {f"{config['icon']} {config['role']}": key for key, config in AGENT_ROSTER.items()}
selected_display_names = st.multiselect("設定出勤名單與執行順序：", options=list(agent_options.keys()), default=list(agent_options.keys()))
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

# --- 4. 執行核心邏輯 ---
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
            with st.spinner("Agent 團隊正在開會討論中..."):
                st.markdown("### 🧠 Agent 思考過程即時轉播")
                log_expander = st.expander("點擊展開/收合幕後 Log", expanded=True)
                
                original_stdout, original_stderr = sys.stdout, sys.stderr 
                stream_catcher = StreamToExpander(log_expander)
                sys.stdout = sys.stderr = stream_catcher 

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
                finally:
                    sys.stdout, sys.stderr = original_stdout, original_stderr
