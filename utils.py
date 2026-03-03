# utils.py
import re
import sys
import time  # 👉 新增時間模組

class StreamToExpander:
    """攔截系統標準輸出，轉向 Streamlit，並同步保留給後台"""
    def __init__(self, expander):
        self.expander = expander
        self.buffer = []
        self.text_area = self.expander.empty()
        self.last_update_time = time.time()  # 👉 記錄上次更新網頁的時間

    def write(self, data):
        # 備份一份到原本的終端機，確保伺服器後台還是看得到完整 Log
        sys.__stdout__.write(data)
        
        # 精準過濾討厭的報錯
        if "Sync handler error" in data or "Event pairing mismatch" in data:
            return
            
        # 清除終端機專用的顏色亂碼
        clean_data = re.sub(r'\x1b\[[0-9;]*m', '', data)
        self.buffer.append(clean_data)
        
        # 🚀 效能保護機制 (節流閥)：每 0.5 秒才更新一次網頁，避免瀏覽器被海量 Log 弄到當機白屏！
        current_time = time.time()
        if current_time - self.last_update_time > 0.5:
            self.text_area.code("".join(self.buffer), language="text")
            self.last_update_time = current_time

    def flush(self): 
        # 任務結束時，強制把緩衝區剩下的文字全部印出來
        if self.buffer:
            self.text_area.code("".join(self.buffer), language="text")
        sys.__stdout__.flush()
