import streamlit as st
import os
import sys
import re
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import FileReadTool, SerperDevTool
from langchain_google_genai import ChatGoogleGenerativeAI
# --- 動態尋找廣播中心的防彈寫法 ---
try:
    # CrewAI 最新版的路徑
    from crewai.events.event_bus import crewai_event_bus
except ModuleNotFoundError:
    try:
        # CrewAI 舊版的路徑
        from crewai.utilities.events import crewai_event_bus
    except ModuleNotFoundError:
        crewai_event_bus = None

# --- 1. 網頁 UI 基本設定 ---
st.set_page_config(page_title="Smart Watcher - 社群公關智囊團", page_icon="🤖", layout="wide")
st.title("Smart Watcher - 社群公關智囊團 🤖")
st.markdown("輸入 Threads 上的貼文，勾選需要的團隊成員，讓 AI 為你執行客製化任務。")

class StreamToExpander:
    def __init__(self, expander):
        self.expander = expander
        self.buffer = []
        self.text_area = self.expander.empty()

    def write(self, data):
        clean_data = re.sub(r'\x1b\[[0-9;]*m', '', data)
        self.buffer.append(clean_data)
        self.text_area.code("".join(self.buffer), language="text")

    def flush(self): pass

# --- 2. 統一把 Agent 的參數寫成「員工名冊」 ---
AGENT_ROSTER = {
    "researcher": {
        "icon": "🕵️‍♂️",
        "role": "資深社群輿情分析師",
        "goal": "分析 Threads 貼文。你必須使用搜尋工具尋找相關的「最新新聞或近期股價動態」，結合最新資訊來提供切入點建議。",
        "backstory": "你是一個對美股半導體與網通晶片極度敏銳的數據分析師。擅長一針見血地看出散戶的焦慮與市場盲點。",
        "task_desc": "分析以下這篇貼文：\n\n{post}\n\n提取核心疑問，並提供專業的市場切入點。",
        "expected_output": "一段包含最新市場動態的簡短分析報告。",
        "needs_search": True,
        "needs_guidelines": False
    },
    "pr_writer": {
        "icon": "✍️",
        "role": "資深品牌公關與技術專家",
        "goal": "根據前文撰寫留言。必須先使用工具讀取 pr_guidelines.txt，並嚴格遵守裡面的語氣。",
        "backstory": "你是一位懂技術也懂人心的專家。留言從不推銷，語氣成熟穩重。",
        "task_desc": "針對該議題（若有前一份分析報告請務必參考），草擬一段 100 字以內的回覆：\n\n{post}",
        "expected_output": "一段準備好可以直接複製貼上的繁體中文留言草稿。",
        "needs_search": False,
        "needs_guidelines": True
    },
    "GreenBird_writer": {
        "icon": "🐦",
        "role": "充滿台灣價值的小編",
        "goal": "根據前文撰寫留言。",
        "backstory": "你是一位充滿台灣價值，精通青鳥邏輯的社群媒體小編寫手。你的風格導師是呱吉，四叉貓，沈柏洋等人。所有跟台灣有關事件都能政治正確的轉譯成對台灣有利的鄉民語言。",
        "task_desc": "針對該議題（若有前一份分析報告請務必參考），草擬一段 100 字以內的回覆：\n\n{post}",
        "expected_output": "一段準備好可以直接複製貼上社群媒體的繁體中文留言草稿。",
        "needs_search": False,
        "needs_guidelines": True
    }
}

# --- 3. 前端 UI：目標貼文輸入區 ---
default_post = "最近科技股震盪，尤其是網通晶片。像 MRVL 這種 ASIC 概念股，大家覺得現在的位階還可以佈局嗎？想聽聽高手的看法。"
user_post = st.text_area("🎯 目標 Threads 貼文：", value=default_post, height=100)

# --- 4. 前端 UI：動態選擇與排序出任務的 Agent ---
st.markdown("### 👥 選擇與排序出任務的智囊團成員")
st.caption("請在下方選單中，**依照你要的執行順序**挑選 Agent。先選的會先執行，並把結果交給下一位！")

# 建立選項對應字典 (顯示名稱 -> 內部 key)
agent_options = {f"{config['icon']} {config['role']}": key for key, config in AGENT_ROSTER.items()}

# 🌟 關鍵魔法：使用 multiselect 讓使用者選人，它會記住點擊的順序！
selected_display_names = st.multiselect(
    "設定出勤名單與執行順序：",
    options=list(agent_options.keys()),
    default=list(agent_options.keys()) # 預設全選，且照著 researcher -> pr_writer 的順序
)

# 把顯示名稱轉回內部的 key 清單 (這份清單的順序，就是你剛剛點擊排出來的順序)
selected_agent_keys = [agent_options[name] for name in selected_display_names]

# 動態畫出排序好的卡片，讓使用者清楚知道現在的「流水線」長怎樣
if selected_agent_keys:
    st.markdown("#### 📋 目前的流水線順序：")
    for i, key in enumerate(selected_agent_keys):
        config = AGENT_ROSTER[key]
        # 卡片標題自動加上「第 X 棒」
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

# --- 5. 執行核心邏輯與邏輯檢查 ---
st.markdown("---")

# 建立左右兩個按鈕
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
                os.environ["GOOGLE_API_KEY"] = api_key
                # 召喚一個專門用來檢查邏輯的輕量級大腦
                reviewer_llm = ChatGoogleGenerativeAI(
                    model="gemini-3-flash-preview", 
                    temperature=0.2,
                    api_key=api_key  # 👉 加上這行，確保它絕對拿得到金鑰
                )

                pipeline_str = " ➡️ ".join([AGENT_ROSTER[k]['role'] for k in selected_agent_keys])
                roles_desc = "\n".join([f"- {AGENT_ROSTER[k]['role']}: {AGENT_ROSTER[k]['goal']}" for k in selected_agent_keys])

                prompt = f"""
                你是一位資深的 AI 系統架構師。使用者安排了一個 Multi-Agent 流水線來處理以下任務：
                「{user_post}」

                使用者安排的執行順序是：
                {pipeline_str}

                各 Agent 職責：
                {roles_desc}

                請以繁體中文，在 150 字以內評估這個順序是否合理。
                如果邏輯完美（例如：先查資料分析，再讓公關寫作），請大力稱讚。
                如果邏輯顛倒（例如：公關先憑空寫作，分析師才去查資料），請幽默地點出盲點（例如提醒公關會被迫通靈），並建議正確順序。
                """
                
                try:
                    response = reviewer_llm.invoke(prompt)
                    raw_content = response.content
                    
                    # --- 新增：專門處理 Gemini 3 Preview 特殊格式的過濾器 ---
                    final_text = raw_content # 預設先等於原始內容
                    
                    # 如果 LangChain 吐出來的是 List，直接抓第一筆的 text
                    if isinstance(raw_content, list) and len(raw_content) > 0:
                        final_text = raw_content[0].get("text", str(raw_content))
                    # 如果 LangChain 把它硬轉成字串了，我們把它解開來抓 text
                    elif isinstance(raw_content, str) and raw_content.startswith("[{'type':"):
                        import ast
                        try:
                            parsed = ast.literal_eval(raw_content)
                            final_text = parsed[0].get("text", raw_content)
                        except:
                            pass
                    # --------------------------------------------------------

                    st.info(f"**🕵️ AI 架構師點評：**\n\n{final_text}")
                    
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
                # 👉 新增：強制清除 CrewAI 廣播中心的舊記憶，防止 Log 疊加！
                if crewai_event_bus and hasattr(crewai_event_bus, '_handlers'):
                    crewai_event_bus._handlers.clear()

                os.environ["GEMINI_API_KEY"] = api_key
                os.environ["GOOGLE_API_KEY"] = api_key
                os.environ["SERPER_API_KEY"] = serper_api_key
                
                llm = LLM(model="gemini/gemini-2.5-flash-lite", temperature=0.6, api_key=api_key)
                guidelines_tool = FileReadTool(file_path='pr_guidelines.txt')
                search_tool = SerperDevTool()

                active_agents = []
                active_tasks = []

                for key in selected_agent_keys:
                    config = AGENT_ROSTER[key]
                    
                    agent_tools = []
                    if config['needs_search']: agent_tools.append(search_tool)
                    if config['needs_guidelines']: agent_tools.append(guidelines_tool)
                    
                    agent = Agent(
                        role=config['role'],
                        goal=config['goal'],
                        backstory=config['backstory'],
                        tools=agent_tools,
                        allow_delegation=False,
                        verbose=True,
                        llm=llm
                    )
                    active_agents.append(agent)
                    
                    task = Task(
                        description=config['task_desc'].format(post=user_post),
                        expected_output=config['expected_output'],
                        agent=agent
                    )
                    active_tasks.append(task)

                pr_crew = Crew(
                    agents=active_agents,
                    tasks=active_tasks,
                    process=Process.sequential 
                )

                st.markdown("### 🧠 Agent 思考過程即時轉播")
                log_expander = st.expander("點擊展開/收合幕後 Log", expanded=True)
                original_stdout = sys.stdout 
                sys.stdout = StreamToExpander(log_expander) 

                try:
                    result = pr_crew.kickoff()
                    st.success("✨ 任務完成！")
                    st.subheader("📝 最終產出：")
                    st.write(result.raw)
                except Exception as e:
                    st.error("🚨 發生錯誤！")
                    st.code(str(e))
                finally:
                    sys.stdout = original_stdout
