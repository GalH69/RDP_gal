import socket
import threading
import tkinter as tk
from PIL import Image, ImageTk
import io

class RemoteViewer:
    def __init__(self, host='0.0.0.0', tcp_port=8081, udp_port=8080):
        self.host, self.tcp_port, self.udp_port = host, tcp_port, udp_port

        # בניית ממשק המשתמש
        self.root = tk.Tk()
        self.root.title("Remote Desktop - Controller")
        self.panel = tk.Label(self.root)
        self.panel.pack(fill="both", expand="yes")

        # הגדרת אירוע סגירת חלון
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # הקמת Sockets
        self.client_tcp = None
        self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_sock.bind((self.host, self.tcp_port))
        self.tcp_sock.listen(1)
        
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.bind((self.host, self.udp_port))

        # הפעלת תהליכי רקע
        threading.Thread(target=self._wait_for_client, daemon=True).start()
        threading.Thread(target=self._receive_screen, daemon=True).start()
        
        # רישום אירועי עכבר ומקלדת
        self.panel.bind("<Motion>", lambda e: self._send_mouse(e, "move"))
        self.panel.bind("<Button-1>", lambda e: self._send_mouse(e, "left"))
        self.panel.bind("<Button-3>", lambda e: self._send_mouse(e, "right"))
        self.root.bind("<Key>", self._send_key)
        
        self.root.mainloop()

    def _on_close(self):
        """סגירת החיבור וביצוע Kill מרחוק ללקוח"""
        print("Sending shutdown command to client...")
        self._send_msg("SYSTEM:CLOSE")
        if self.client_tcp:
            self.client_tcp.close()
        self.root.destroy()

    def _send_mouse(self, event, action):
        """חישוב מיקום יחסי (Normalizing) ושליחה"""
        w = self.panel.winfo_width()
        h = self.panel.winfo_height()
        if w > 1 and h > 1:
            rel_x = event.x / w
            rel_y = event.y / h
            self._send_msg(f"M:{action}:{rel_x}:{rel_y}")

    def _send_key(self, event):
        """שליחת שם המקש (keysym) לעקיפת בעיות שפה"""
        self._send_msg(f"K:{event.keysym}")

    def _wait_for_client(self):
        print(f"Waiting for client on port {self.tcp_port}...")
        self.client_tcp, addr = self.tcp_sock.accept()
        print(f"Connected to: {addr}")

    def _send_msg(self, msg_str):
        """מימוש Framing אחיד ללא struct"""
        if not self.client_tcp: return
        try:
            payload = msg_str.encode('utf-8')
            header = len(payload).to_bytes(4, byteorder='big')
            self.client_tcp.sendall(header + payload)
        except:
            self.client_tcp = None

    def _receive_screen(self):
        """קבלת צילומי מסך ב-UDP והצגתם"""
        while True:
            try:
                data, _ = self.udp_sock.recvfrom(65535)
                img = Image.open(io.BytesIO(data))
                img_tk = ImageTk.PhotoImage(img)
                self.panel.config(image=img_tk)
                self.panel.image = img_tk
            except:
                continue

if __name__ == "__main__":
    RemoteViewer()