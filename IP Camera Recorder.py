import cv2
import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog
from threading import Thread, Event
from datetime import datetime
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

class IPcamRecorder:
    def __init__(self, root):
        self.root = root
        self.root.title("IP Camera Recorder")
        
        self.ip_var = tk.StringVar#(value="http://192.168.X.X:8080/browserfs.html")                       # Uncomment and edit value to enable Auto Filled IP Camera URL
        self.folderpath_var = tk.StringVar#(value="D:\\Location\\For Saving\\Your Recordings")            # Uncomment and edit value to enable Auto Filled Folder Path
        
        tk.Label(root, text="IP Camera URL:").grid(row=0, column=0)
        self.ip_entry = tk.Entry(root, textvariable=self.ip_var, width=50)
        self.ip_entry.grid(row=0, column=1)
        
        tk.Label(root, text="Save to folder:").grid(row=1, column=0)
        self.folderpath_entry = tk.Entry(root, textvariable=self.folderpath_var, width=50)
        self.folderpath_entry.grid(row=1, column=1)
        tk.Button(root, text="Browse", command=self.browse_folder).grid(row=1, column=2)
        
        self.record_button = tk.Button(root, text="Record", command=self.start_recording)
        self.record_button.grid(row=2, column=0)
        self.stop_button = tk.Button(root, text="Stop", command=self.stop_recording, state=tk.DISABLED)
        self.stop_button.grid(row=2, column=1)
        
        self.is_recording = False
        self.capture = None
        self.out = None
        self.stop_event = Event()
        
    def browse_folder(self):
        folderpath = filedialog.askdirectory()
        self.folderpath_var.set(folderpath)
    
    def start_recording(self):
        ip = self.ip_var.get()
        folderpath = self.folderpath_var.get()
        
        if not ip or not folderpath:
            messagebox.showerror("Error", "IP Camera URL and folder path are required.")
            return
        
        self.is_recording = True
        self.record_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        stream_url = self.get_stream_url(ip)
        if not stream_url:
            messagebox.showerror("Error", "Failed to extract the stream URL.")
            self.record_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            return
        
        self.capture = cv2.VideoCapture(stream_url)
        if not self.capture.isOpened():
            messagebox.showerror("Error", "Failed to connect to the IP camera.")
            self.record_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            return

        # Get the video properties for the VideoWriter
        width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self.capture.get(cv2.CAP_PROP_FPS)
        if fps <= 0:  # Sometimes fps can be 0, set a default value
            fps = 30.0

        now = datetime.now()
        filename = now.strftime("[%d-%m-%Y] (%H-%M-%S).mp4")
        filepath = os.path.join(folderpath, filename)
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.out = cv2.VideoWriter(filepath, fourcc, fps, (width, height))
        
        self.stop_event.clear()
        self.thread = Thread(target=self.record)
        self.thread.start()
    
    def get_stream_url(self, ip):
        # Ensure the URL has a scheme (http://)
        parsed_url = urlparse(ip)
        if not parsed_url.scheme:
            ip = 'http://' + ip
        
        try:
            response = requests.get(ip)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to find <video> tag
            video_tag = soup.find('video')
            if video_tag and 'src' in video_tag.attrs:
                stream_url = video_tag['src']
                # If the stream URL is relative, make it absolute
                if not urlparse(stream_url).scheme:
                    stream_url = urljoin(ip, stream_url)
                print(f"Extracted stream URL: {stream_url}")
                return stream_url

            # Try to find <img> tag for MJPEG streams
            img_tag = soup.find('img')
            if img_tag and 'src' in img_tag.attrs:
                stream_url = img_tag['src']
                # If the stream URL is relative, make it absolute
                if not urlparse(stream_url).scheme:
                    stream_url = urljoin(ip, stream_url)
                print(f"Extracted stream URL: {stream_url}")
                return stream_url

        except Exception as e:
            print(f"Error extracting stream URL: {e}")
        return None
    
    def record(self):
        while not self.stop_event.is_set():
            ret, frame = self.capture.read()
            if ret:
                self.out.write(frame)
            else:
                print("Failed to read frame from stream.")
                break
    
    def stop_recording(self):
        self.is_recording = False
        self.record_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
        self.stop_event.set()
        self.thread.join()
        
        if self.capture:
            self.capture.release()
        if self.out:
            self.out.release()
        cv2.destroyAllWindows()
    
if __name__ == "__main__":
    root = tk.Tk()
    app = IPcamRecorder(root)
    root.mainloop()