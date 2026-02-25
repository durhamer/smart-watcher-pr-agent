import streamlit as st
import os
from crewai import Agent, Task, Crew, Process, LLM
from langchain_google_genai import ChatGoogleGenerativeAI

# 網頁 UI 設定
st.set_page_config(page_title="Smart Watcher - 社群公關智囊團", page_icon="🤖")
st.title("Smart Watcher - 社群公關智囊團 🤖")
st.markdown("輸入 Threads 上的貼文，讓 AI 團隊自動分析並草擬專業回覆。")

# 這裡設定一個預設的測試貼文
default_post = "最近科技股震盪，尤其是網通晶片。像 MRVL 這種 ASIC 概念股，大家覺得現在的位階還可以佈局嗎？想聽聽高手的看法。"
user_post = st.text_area("目標 Threads 貼文：", value=default_post, height=150)

if st.button("🚀 啟動智囊團分析"):
    # 從 Streamlit 後台抓取 API Key (為了安全，不要把 Key 寫死在程式碼裡)
    api_key = st.secrets.get("GEMINI_API_KEY")
    
    with st.spinner("Agent 團隊正在開會討論中... (大約需要 30~60 秒)"):
            # 確保環境變數同時設定這兩個，以防萬一
            os.environ["GEMINI_API_KEY"] = api_key
            os.environ["GOOGLE_API_KEY"] = api_key
            
            # 使用 CrewAI 內建的 LLM，並加上 gemini/ 前綴
            llm = LLM(
                model="gemini/gemini-2.5-pro", 
                temperature=0.6,
                api_key=api_key
            )

            # 定義員工
            researcher = Agent(
                role='資深社群輿情分析師',
                goal='分析 Threads 貼文，提供財經與技術面的切入點建議。',
                backstory='你是一個對美股半導體與網通晶片極度敏銳的數據分析師。擅長一針見血地看出散戶的焦慮與市場盲點。',
                allow_delegation=False,
                llm=llm
            )

            pr_writer = Agent(
                role='資深品牌公關與技術專家',
                goal='根據分析報告，撰寫一段專業、自然且能引發共鳴的留言。',
                backstory='你是一位懂技術也懂人心的專家。留言從不推銷，而是透過客觀的總經數據或基本面分析建立權威感，語氣成熟穩重。',
                allow_delegation=False,
                llm=llm
            )

            # 分派任務
            task1 = Task(
                description=f'分析以下這篇貼文：\n\n{user_post}\n\n提取核心疑問，並提供兩個回覆的專業切入點。',
                expected_output='一段簡短的分析報告。',
                agent=researcher
            )

            task2 = Task(
                description='閱讀分析師提供的報告，為這篇貼文草擬一段 100 字以內的回覆。提供具體的市場觀點。',
                expected_output='一段準備好可以直接複製貼上的繁體中文留言草稿。',
                agent=pr_writer
            )

            # 組建團隊並執行
            pr_crew = Crew(
                agents=[researcher, pr_writer],
                tasks=[task1, task2],
                process=Process.sequential 
            )

            result = pr_crew.kickoff()

            st.success("✨ 分析與草擬完成！")
            st.subheader("📝 建議回覆草稿：")
            st.write(result.raw) # 輸出最終結果
