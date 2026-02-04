import socket
import threading
import pyautogui
import io
import time
import os
from PIL import ImageGrab
from pynput.keyboard import Controller, Key

class RemoteAgent:
    def __init__(self, host='127.0.0.1', tcp_port=8081, udp_port=8080):
        self.host, self.tcp_port, self.udp_port = host, tcp_port, udp_port
        self.keyboard = Controller()
        
        # ביטול הגנות מקומיות - השליטה היא של השרת בלבד
        pyautogui.FAILSAFE = False 
        self.screen_w, self.screen_h = pyautogui.size()

        self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.running = True
        
        try:
            print(f"Connecting to {host}...")
            self.tcp_sock.connect((self.host, self.tcp_port))
            threading.Thread(target=self._handle_commands, daemon=True).start()
            self._stream_screen()
        except Exception as e:
            print(f"Exit: {e}")

    def _recv_all(self, n):
        """מבטיח קריאת n בתים בדיוק מה-TCP"""
        data = bytearray()
        while len(data) < n:
            packet = self.tcp_sock.recv(n - len(data))
            if not packet: return None
            data.extend(packet)
        return data

    def _handle_commands(self):
        # מפת תרגום למקשים מיוחדים
        key_map = {"BackSpace": Key.backspace, "Return": Key.enter, "space": Key.space, "Escape": Key.esc}
        
        while self.running:
            try:
                # קריאת אורך ההודעה
                header = self._recv_all(4)
                if not header: break
                
                size = int.from_bytes(header, byteorder='big')
                msg = self._recv_all(size).decode('utf-8')
                
                parts = msg.split(":")
                
                # 1. בדיקת פקודת סגירה מערכתית
                if parts[0] == "SYSTEM" and parts[1] == "CLOSE":
                    print("Shutdown requested by server.")
                    self.running = False
                    break
                
                # 2. טיפול במקלדת
                elif parts[0] == "K":
                    key_val = key_map.get(parts[1], parts[1])
                    try:
                        self.keyboard.press(key_val)
                        self.keyboard.release(key_val)
                    except: pass
                
                # 3. טיפול בעכבר (חישוב מנורמל)
                elif parts[0] == "M":
                    action = parts[1]
                    target_x = float(parts[2]) * self.screen_w
                    target_y = float(parts[3]) * self.screen_h
                    
                    if action == "move":
                        pyautogui.moveTo(target_x, target_y)
                    else: # click (left/right)
                        pyautogui.click(target_x, target_y, button=action)
                        
            except:
                break
        
        # סגירה אגרסיבית של כל התהליך
        self.tcp_sock.close()
        os._exit(0)

    def _stream_screen(self):
        """צילום מסך ושליחה ב-UDP"""
        while self.running:
            try:
                img = ImageGrab.grab()
                # הקטנה לרזולוציה אחידה לשידור
                img = img.resize((800, 450)) 
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=30)
                
                frame_data = buf.getvalue()
                if len(frame_data) < 65000:
                    self.udp_sock.sendto(frame_data, (self.host, self.udp_port))
                
                time.sleep(0.05) # ~20 FPS
            except:
                break

if __name__ == "__main__":
    RemoteAgent()