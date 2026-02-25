import streamlit as st
import os
import sys
import re
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import FileReadTool

# 網頁 UI 設定
st.set_page_config(page_title="Smart Watcher - 社群公關智囊團", page_icon="🤖")
st.title("Smart Watcher - 社群公關智囊團 🤖")
st.markdown("輸入 Threads 上的貼文，讓 AI 團隊自動分析並草擬專業回覆。")

# --- 新增：用來攔截 Terminal 輸出並顯示在網頁上的類別 ---
class StreamToExpander:
    def __init__(self, expander):
        self.expander = expander
        self.buffer = []
        # 在折疊面板中建立一個空的區塊來隨時更新文字
        self.text_area = self.expander.empty()

    def write(self, data):
        # 過濾掉 Terminal 專用的顏色代碼 (ANSI escape codes)，避免網頁顯示亂碼
        clean_data = re.sub(r'\x1b\[[0-9;]*m', '', data)
        self.buffer.append(clean_data)
        # 把收集到的 Log 即時印在網頁上
        self.text_area.code("".join(self.buffer), language="text")

    def flush(self):
        pass
# ----------------------------------------------------

default_post = "最近科技股震盪，尤其是網通晶片。像 MRVL 這種 ASIC 概念股，大家覺得現在的位階還可以佈局嗎？想聽聽高手的看法。"
user_post = st.text_area("目標 Threads 貼文：", value=default_post, height=150)

if st.button("🚀 啟動智囊團分析"):
    api_key = st.secrets.get("GEMINI_API_KEY")
    
    if not api_key:
        st.error("請先在 Streamlit Cloud 後台設定 GEMINI_API_KEY！")
    else:
        with st.spinner("Agent 團隊正在開會討論中... 請看下方幕後 Log 👇"):
            os.environ["GEMINI_API_KEY"] = api_key
            os.environ["GOOGLE_API_KEY"] = api_key
            
            llm = LLM(model="gemini/gemini-2.5-flash", temperature=0.6, api_key=api_key)
            guidelines_tool = FileReadTool(file_path='pr_guidelines.txt')

            # 👉 關鍵：加上 verbose=True 讓他們開口講話
            researcher = Agent(
                role='資深社群輿情分析師',
                goal='分析 Threads 貼文，提供財經與技術面的切入點建議。',
                backstory='你是一個對美股半導體與網通晶片極度敏銳的數據分析師。擅長一針見血地看出散戶的焦慮與市場盲點。',
                allow_delegation=False,
                verbose=True, 
                llm=llm
            )

            pr_writer = Agent(
                role='資深品牌公關與技術專家',
                goal='根據分析報告撰寫留言。必須先使用工具讀取 pr_guidelines.txt，並嚴格遵守裡面的語氣。',
                backstory='你是一位懂技術也懂人心的專家。留言從不推銷，語氣成熟穩重。',
                tools=[guidelines_tool],
                allow_delegation=False,
                verbose=True, 
                llm=llm
            )

            task1 = Task(
                description=f'分析以下這篇貼文：\n\n{user_post}\n\n提取核心疑問，並提供兩個回覆的專業切入點。',
                expected_output='一段簡短的分析報告。',
                agent=researcher
            )

            task2 = Task(
                description='閱讀分析師提供的報告，草擬一段 100 字以內的回覆。',
                expected_output='一段準備好可以直接複製貼上的繁體中文留言草稿。',
                agent=pr_writer
            )

            pr_crew = Crew(
                agents=[researcher, pr_writer],
                tasks=[task1, task2],
                process=Process.sequential 
            )

            # --- 新增：建立折疊面板並啟動攔截器 ---
            st.markdown("### 🧠 Agent 思考過程即時轉播")
            log_expander = st.expander("點擊展開/收合幕後 Log", expanded=True)
            original_stdout = sys.stdout # 備份原本的輸出管道
            sys.stdout = StreamToExpander(log_expander) # 偷天換日

            try:
                # 執行任務 (這時候的輸出都會被吸進網頁裡)
                result = pr_crew.kickoff()
                
                st.success("✨ 分析與草擬完成！")
                st.subheader("📝 建議回覆草稿：")
                st.write(result.raw)
                
            except Exception as e:
                st.error("🚨 發生錯誤！")
                st.code(str(e))
            finally:
                # 任務結束，把輸出管道還給系統，以免搞壞 Streamlit
                sys.stdout = original_stdout
