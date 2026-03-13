# ai_core.py
import os
import ast
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import FileReadTool, SerperDevTool
from langchain_google_genai import ChatGoogleGenerativeAI

# 👉 引入員工名冊與配置設定
from agents import AGENT_ROSTER
from app_config import AI_MODELS

def evaluate_pipeline(user_post, selected_agent_keys, api_key):
    """呼叫架構師大腦，檢查邏輯並預估 Token"""
    os.environ["GOOGLE_API_KEY"] = api_key
    
    reviewer_llm = ChatGoogleGenerativeAI(
        model=AI_MODELS.REVIEWER_MODEL, 
        temperature=AI_MODELS.REVIEWER_TEMP,
        api_key=api_key
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
    如果邏輯完美，請大力稱讚。如果邏輯顛倒，請幽默點出盲點並建議正確順序。
    """
    
    response = reviewer_llm.invoke(prompt)
    raw_content = response.content
    
    # 過濾格式
    final_text = raw_content
    if isinstance(raw_content, list) and len(raw_content) > 0:
        final_text = raw_content[0].get("text", str(raw_content))
    elif isinstance(raw_content, str) and raw_content.startswith("[{'type':"):
        try:
            parsed = ast.literal_eval(raw_content)
            final_text = parsed[0].get("text", raw_content)
        except: pass
        
    base_text = prompt + "".join([str(AGENT_ROSTER[k]) for k in selected_agent_keys])
    base_tokens = int(len(base_text) * 1.5)
    
    return final_text, base_tokens

def execute_crew(user_post, selected_agent_keys, api_key, serper_api_key):
    """正式組裝並啟動 CrewAI 團隊，回傳結果與帳單"""
    # 設定環境變數
    os.environ["GEMINI_API_KEY"] = api_key
    os.environ["GOOGLE_API_KEY"] = api_key
    os.environ["SERPER_API_KEY"] = serper_api_key
    
    # 建立主大型語言模型實例
    llm = LLM(
        model=AI_MODELS.CREW_MAIN_MODEL, 
        temperature=AI_MODELS.CREW_TEMP, 
        api_key=api_key
    )
    
    # 🛡️ 檔案防護：檢查教戰守則檔案是否存在，若無則建立空白檔避免報錯
    guidelines_file = 'pr_guidelines.txt'
    if not os.path.exists(guidelines_file):
        with open(guidelines_file, 'w', encoding='utf-8') as f:
            f.write("目前暫無特定教戰守則。")
    
    # 初始化工具
    guidelines_tool = FileReadTool(file_path=guidelines_file)
    # 新版：強制只搜尋「過去一週 (qdr:w)」的結果，確保是最新時事！
    # 如果你想更極端，可以改成 "qdr:d" (過去 24 小時)
    search_tool = SerperDevTool(search_parameters={
        "num": 4, 
        "tbs": "qdr:d" 
    })


    active_agents = []
    active_tasks = []

    # 依據使用者選擇的順序建立 Agent 與 Task
    for key in selected_agent_keys:
        # 💡 這裡的 config 已經由 admin_dashboard.py 同步過 Google Sheets 的最新設定
        config = AGENT_ROSTER[key]
        
        agent_tools = []
        # 依據雲端開關狀態動態分配工具
        if config.get('needs_search', False): 
            agent_tools.append(search_tool)
        if config.get('needs_guidelines', False): 
            agent_tools.append(guidelines_tool)
        
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

    # 組裝智囊團
    pr_crew = Crew(
        agents=active_agents,
        tasks=active_tasks,
        process=Process.sequential, # 按順序執行
        memory=True,  
        embedder={    
            "provider": "google-generativeai", # 🚀 關鍵修正：從 'google' 改成這個
            "config": {
                "model": "models/embedding-001",
                "api_key": api_key
            }
        },
        verbose=True
    )

    # 啟動任務並獲取結果
    result = pr_crew.kickoff()
    usage = pr_crew.usage_metrics
    
    # 提取 Token 使用量資訊
    metrics = {
        "prompt_tokens": usage.prompt_tokens if hasattr(usage, 'prompt_tokens') else 0,
        "completion_tokens": usage.completion_tokens if hasattr(usage, 'completion_tokens') else 0,
        "total_tokens": usage.total_tokens if hasattr(usage, 'total_tokens') else 0
    }
    
    return result.raw, metrics
