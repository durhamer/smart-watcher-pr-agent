# utils.py
import re
import sys
import time

class StreamToExpander:
    """攔截系統標準輸出，轉向 Streamlit，並加上極致的記憶體與渲染保護機制"""
    def __init__(self, expander):
        self.expander = expander
        self.buffer = []
        self.text_area = self.expander.empty()
        self.last_update_time = time.time()
        self.MAX_CHARS = 3000  # 👉 改用「字數」來限制，比行數更安全，確保前端不會被幾萬字撐爆

    def write(self, data):
        # 備份到後台終端機
        sys.__stdout__.write(data)
        
        # 過濾特定錯誤訊息
        if "Sync handler error" in data or "Event pairing mismatch" in data:
            return
            
        # 👉 終極亂碼過濾器：洗掉所有可能導致前端崩潰的 ANSI 控制碼與隱藏符號
        clean_data = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', data)
        self.buffer.append(clean_data)
        
        # 把目前所有的字串接起來
        full_text = "".join(self.buffer)
        
        # 👉 安全截斷機制：如果字數超過限制，只保留最新的部分
        if len(full_text) > self.MAX_CHARS:
            full_text = "...(前面的 Log 已自動隱藏以保護瀏覽器記憶體)...\n\n" + full_text[-self.MAX_CHARS:]
            self.buffer = [full_text]  # 重置 buffer，避免在背景越長越大
        
        # 👉 降載節流閥：每 1.0 秒才讓網頁重新畫一次畫面，給瀏覽器喘息的空間
        current_time = time.time()
        if current_time - self.last_update_time > 1.0:
            # 🚀 關鍵修復：改用 .text() 代替 .code()，拔掉沉重的語法高亮引擎，徹底解決 setIn 報錯！
            self.text_area.text(full_text)
            self.last_update_time = current_time

    def flush(self): 
        # 任務結束時，把最後的畫面印出來
        if self.buffer:
            self.text_area.text("".join(self.buffer))
        sys.__stdout__.flush()
