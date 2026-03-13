# config.py

class AI_MODELS:
    """集中管理所有使用的 AI 模型名稱與參數"""
    
    # 1. 系統架構師大腦：負責「檢查流水線邏輯」與「預估 Token」
    # 特性：需要聰明、邏輯好，但不用執行複雜工具
    REVIEWER_MODEL = "gemini-2.5-flash-lite"
    REVIEWER_TEMP = 0.2  # 溫度越低越嚴謹
    
    # 2. 團隊主力大腦：負責實際執行 CrewAI 任務的小編與查核員
    # 特性：需要支援外部工具呼叫，注意 CrewAI 呼叫 Gemini 的字串前綴
    CREW_MAIN_MODEL = "gemini/gemini-2.5-flash"
    CREW_TEMP = 0.6  # 稍微高一點，讓小編的回覆比較生動自然
