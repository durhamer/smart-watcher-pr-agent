# app.py
import streamlit as st
import sys

# 👉 終極防護：每次網頁刷新時，強制把可能被卡死的系統通道還原！
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__

# 👉 從我們剛建立的模組中引入所需的工具與 AI 引擎
from agents import AGENT_ROSTER
from utils import StreamToExpander
from ai_core import evaluate_pipeline, execute_crew

# --- 1. 網頁 UI 基本設定 ---
st.set_page_config(page_title="Smart Watcher - 社群公關智囊團", page_icon="🤖", layout="wide")
st.title("Smart Watcher - 社群公關智囊團 🤖")
st.markdown("輸入 Threads 上的貼文，勾選需要的團隊成員，讓 AI 為你執行客製化任務。")

# --- 2. 前端 UI：目標貼文與戰略設定區 ---
st.markdown("### 🎯 戰術情報台 (輸入貼文與目的)")
st.caption("請貼上你想攻略的 Threads 內容，並下達你的戰略指令。")

# 使用 Streamlit 的欄位排版，左邊放情報，右邊放目的
col_info, col_strategy = st.columns([1.2, 1])

with col_info:
    post_content = st.text_area("📝 1. 原貼文內容：", height=120, placeholder="貼上版主發的原文...")
    comment_content = st.text_area("💬 2. 精選留言區：", height=120, placeholder="複製幾段你覺得有代表性、或你想反駁的網友留言貼在這裡...")

with col_strategy:
    strategy_goal = st.text_area("🎯 3. 你的戰略目的 (給小編的秘密指令)：", height=300, 
                                 placeholder="例如：\n我想假裝是路過的高手。\n請順著某個留言的邏輯，順勢帶出 MRVL 的網通技術其實比 NVDA 更具長線佈局價值。\n語氣要帶點嘲諷，不要太像寫報告。")

# 🌟 魔法步驟：把這三個輸入框的內容，打包成「一包大字串」，這包字串會被當作 {post} 傳給所有 Agent！
combined_info = f"""
【原貼文內容】：
{post_content if post_content else "無"}

【網友留言區】：
{comment_content if comment_content else "無"}

【老闆下達的戰略目的】：
{strategy_goal if strategy_goal else "請依據上述內容，自由發揮給出最合適的留言。"}
"""

# --- 3. 前端 UI：動態選擇與排序出任務的 Agent ---
st.markdown("### 👥 選擇與排序出任務的智囊團成員")
st.caption("請在下方選單中，**依照你要的執行順序**挑選 Agent。先選的會先執行，並把結果交給下一位！")

agent_options = {f"{config['icon']} {config['role']}": key for key, config in AGENT_ROSTER.items()}

selected_display_names = st.multiselect(
    "設定出勤名單與執行順序：",
    options=list(agent_options.keys()),
    default=list(agent_options.keys())
)

selected_agent_keys = [agent_options[name] for name in selected_display_names]

if selected_agent_keys:
    st.markdown("#### 📋 目前的流水線順序：")
    for i, key in enumerate(selected_agent_keys):
        config = AGENT_ROSTER[key]
        with st.expander(f"第 {i+1} 棒：{config['icon']} {config['role']}", expanded=True):
            st.markdown(f"**🎯 目標 (Goal):** {config['goal']}")
            st.markdown(f"**📖 背景 (Backstory):** {config['backstory']}")
            
            tools_str = []
            if config['needs_search']: tools_str.append("🔍 網路搜尋 (Serper)")
            if config['needs_guidelines']: tools_str.append("📄 教戰守則")
            st.markdown(f"**🛠️ 配備工具:** {', '.join(tools_str) if tools_str else '無'}")
else:
    st.warning("⚠️ 請從上方選單至少挑選一位 Agent！")

st.markdown("---")

# --- 4. 執行核心邏輯與邏輯檢查 ---
col_check, col_run = st.columns(2)

with col_check:
    if st.button("🕵️ 先幫我檢查流水線邏輯", use_container_width=True):
        api_key = st.secrets.get("GEMINI_API_KEY")
        if not api_key:
            st.error("請先設定 GEMINI_API_KEY！")
        elif len(selected_agent_keys) == 0:
            st.warning("⚠️ 請至少挑選一位 Agent！")
        else:
            with st.spinner("AI 架構師正在審查您的排班表..."):
                try:
                    # 👉 這裡已經改用 combined_info 傳遞情報
                    final_text, base_tokens = evaluate_pipeline(combined_info, selected_agent_keys, api_key)
                    
                    st.info(f"**🕵️ AI 架構師點評：**\n\n{final_text}")
                    st.warning(f"📊 **Token 消耗預估 (僅含靜態提示詞)：** 約 {base_tokens} Tokens。\n\n*(注意：實際執行時，因 Agent 會去搜尋網路並來回思考，總消耗量通常會是此預估值的 3 到 5 倍)*")
                except Exception as e:
                    st.error("🚨 檢查時發生錯誤！真實的系統回報如下：")
                    st.code(str(e))

with col_run:
    if st.button("🚀 確認無誤，正式啟動團隊！", type="primary", use_container_width=True):
        api_key = st.secrets.get("GEMINI_API_KEY")
        serper_api_key = st.secrets.get("SERPER_API_KEY")
        
        if not api_key or not serper_api_key:
            st.error("請先在 Streamlit Cloud 後台設定 GEMINI_API_KEY 與 SERPER_API_KEY！")
        elif len(selected_agent_keys) == 0:
            st.warning("⚠️ 至少要打勾選擇一位成員出任務喔！")
        else:
            with st.spinner("Agent 團隊正在開會討論中... 請看下方幕後 Log 👇"):
                
                st.markdown("### 🧠 Agent 思考過程即時轉播")
                log_expander = st.expander("點擊展開/收合幕後 Log", expanded=True)
                
                # 👉 雙重備份：同時記住標準通道與錯誤通道
                original_stdout = sys.stdout 
                original_stderr = sys.stderr 
                
                # 👉 雙重攔截：把兩個通道的聲音都導向我們的網頁 Expander
                stream_catcher = StreamToExpander(log_expander)
                sys.stdout = stream_catcher 
                sys.stderr = stream_catcher 

                try:
                    # 👉 這裡已經改用 combined_info 傳遞情報
                    result_text, metrics = execute_crew(combined_info, selected_agent_keys, api_key, serper_api_key)
                    
                    st.success("✨ 任務完成！")
                    st.subheader("📝 最終產出：")
                    st.write(result_text)
                    
                    st.markdown("---")
                    st.subheader("📈 效能與成本結算 (Token Usage)")
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("輸入 Token (Prompt)", metrics["prompt_tokens"])
                    col2.metric("輸出 Token (Completion)", metrics["completion_tokens"])
                    col3.metric("總消耗 Token", metrics["total_tokens"])
                    
                except Exception as e:
                    st.error("🚨 發生錯誤！")
                    st.code(str(e))
                finally:
                    # 👉 雙重還原：任務結束後，把兩個通道都還給系統
                    sys.stdout = original_stdout
                    sys.stderr = original_stderr
