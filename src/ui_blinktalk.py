# ui_blinktalk.py
import threading
import time
import math
from collections import deque
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import cv2
import mediapipe as mp
import os
import webbrowser

# ----------------- Detection parameters (tweak if needed) -----------------
EYE_AR_THRESH = 1.47
MIN_BLINK_TIME = 0.2
SHORT_BLINK_LIMIT = 0.35
LETTER_GAP = 1.5
SMOOTHING_FRAMES = 5
# -------------------------------------------------------------------------

# Morse dictionary (for letters)
MORSE_CODE_DICT = {
    ".-":"A","-...":"B","-.-.":"C","-..":"D",".":"E","..-.":"F","--.":"G",
    "....":"H","..":"I",".---":"J","-.-":"K",".-..":"L","--":"M","-.":"N",
    "---":"O",".--.":"P","--.-":"Q",".-.":"R","...":"S","-":"T","..-":"U",
    "...-":"V",".--":"W","-..-":"X","-.--":"Y","--..":"Z"
}

# Command patterns (as you set earlier; adjust if needed)
COMMAND_PATTERNS = {
    "_ _": "LOCK",
    "_ . _ _ _ _": "YOUTUBE"
}

# MediaPipe setup
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(min_detection_confidence=0.6, min_tracking_confidence=0.6)

# Shared state (thread-safe-ish primitives)
state = {
    "running": False,
    "frame": None,
    "pattern": "",
    "text": "",
    "ear": None,
    "feedback": ""
}

# Detection worker (runs in background thread)
def detection_worker():
    cap = cv2.VideoCapture(0)
    ear_history = deque(maxlen=SMOOTHING_FRAMES)
    blink_start_time = None
    last_blink_time = time.time()
    pattern = ""
    detected_text = ""
    state["running"] = True

    while state["running"]:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)
        smoothed_EAR = None

        if results.multi_face_landmarks:
            lm = results.multi_face_landmarks[0].landmark
            left = [33,160,158,133,153,144]
            right = [362,385,387,263,373,380]
            # compute EAR
            def ear(landmarks, idx):
                p1,p2,p3,p4,p5,p6 = [landmarks[i] for i in idx]
                v1 = math.dist((p2.x,p2.y),(p4.x,p4.y))
                v2 = math.dist((p3.x,p3.y),(p5.x,p5.y))
                h_dist = math.dist((p1.x,p1.y),(p6.x,p6.y))
                return (v1 + v2) / (2.0 * (h_dist + 1e-8))

            leftEAR = ear(lm, left)
            rightEAR = ear(lm, right)
            avgEAR = (leftEAR + rightEAR) / 2.0

            # smoothing
            ear_history.append(avgEAR)
            smoothed_EAR = sum(ear_history) / len(ear_history)
            state["ear"] = round(smoothed_EAR, 3)

            # draw eye points
            for idx in left + right:
                px, py = int(lm[idx].x * w), int(lm[idx].y * h)
                cv2.circle(frame, (px, py), 2, (0,255,0), -1)

            # blink detection logic
            if smoothed_EAR < EYE_AR_THRESH:
                if blink_start_time is None:
                    blink_start_time = time.time()
            else:
                if blink_start_time:
                    dur = time.time() - blink_start_time
                    blink_start_time = None
                    if dur >= MIN_BLINK_TIME:
                        t = "_" if dur > SHORT_BLINK_LIMIT else "."
                        pattern += t + " "
                        last_blink_time = time.time()
                        print(f"[detector] got {t} ({dur:.2f}s)")
                        state["pattern"] = pattern.strip()

            # letter auto-detect
            if pattern.strip() and (time.time() - last_blink_time) > LETTER_GAP:
                morse = pattern.strip().replace(" ", "")
                letter = MORSE_CODE_DICT.get(morse, "")
                if letter:
                    detected_text += letter
                    state["text"] = detected_text
                    print(f"[detector] letter -> {letter}")
                else:
                    print(f"[detector] unknown morse: {morse}")
                pattern = ""
                state["pattern"] = ""

            # command pattern check
            for code, cmd in COMMAND_PATTERNS.items():
                if state["pattern"] == code:
                    state["feedback"] = f"COMMAND: {cmd}"
                    print(f"[detector] CMD {cmd}")
                    # action (non-blocking): simple actions - lock / open youtube
                    if cmd == "LOCK":
                        os.system("rundll32.exe user32.dll,LockWorkStation")
                    elif cmd == "YOUTUBE":
                        webbrowser.open("https://www.youtube.com")
                    # clear pattern after executing
                    pattern = ""
                    state["pattern"] = ""
                    time.sleep(1.5)

        # store the frame for UI to pick up (BGR -> RGB convert for PIL later)
        state["frame"] = frame

    cap.release()
    state["running"] = False
    print("[detector] stopped")

# UI class
class BlinkUI:
    def __init__(self, root):
        self.root = root
        root.title("BlinkTalk — UI")
        root.protocol("WM_DELETE_WINDOW", self.on_exit)

        # Video panel
        self.video_label = ttk.Label(root)
        self.video_label.grid(row=0, column=0, columnspan=3, padx=8, pady=8)

        # Info labels
        self.ear_var = tk.StringVar(value="EAR: N/A")
        self.pattern_var = tk.StringVar(value="Pattern: ")
        self.text_var = tk.StringVar(value="Text: ")
        self.feedback_var = tk.StringVar(value="")

        self.ear_label = ttk.Label(root, textvariable=self.ear_var, font=("Helvetica", 12))
        self.ear_label.grid(row=1, column=0, sticky="w", padx=8)

        self.pattern_label = ttk.Label(root, textvariable=self.pattern_var, font=("Helvetica", 12))
        self.pattern_label.grid(row=1, column=1, sticky="w", padx=8)

        self.text_label = ttk.Label(root, textvariable=self.text_var, font=("Helvetica", 12))
        self.text_label.grid(row=1, column=2, sticky="w", padx=8)

        self.feedback_label = ttk.Label(root, textvariable=self.feedback_var, font=("Helvetica", 14), foreground="red")
        self.feedback_label.grid(row=2, column=0, columnspan=3, pady=(4,8))

        # Buttons
        self.start_btn = ttk.Button(root, text="Start Detection", command=self.start_detection)
        self.start_btn.grid(row=3, column=0, padx=6, pady=6)

        self.stop_btn = ttk.Button(root, text="Stop Detection", command=self.stop_detection, state="disabled")
        self.stop_btn.grid(row=3, column=1, padx=6, pady=6)

        self.exit_btn = ttk.Button(root, text="Exit", command=self.on_exit)
        self.exit_btn.grid(row=3, column=2, padx=6, pady=6)

        self.update_ui()  # start periodic UI update

    def start_detection(self):
        if not state["running"]:
            self.thread = threading.Thread(target=detection_worker, daemon=True)
            self.thread.start()
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.feedback_var.set("Detection started...")
        else:
            messagebox.showinfo("Info", "Already running")

    def stop_detection(self):
        if state["running"]:
            state["running"] = False
            self.stop_btn.config(state="disabled")
            self.start_btn.config(state="normal")
            self.feedback_var.set("Stopping...")
        else:
            messagebox.showinfo("Info", "Not running")

    def on_exit(self):
        if state["running"]:
            state["running"] = False
            time.sleep(0.3)
        try:
            self.root.destroy()
        except:
            pass

    def update_ui(self):
        # update video frame
        frame = state.get("frame")
        if frame is not None:
            # OpenCV BGR -> PIL RGB
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)
            img = img.resize((640, 480))
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)

        # update text info
        ear = state.get("ear")
        pattern = state.get("pattern", "")
        text = state.get("text", "")
        fb = state.get("feedback", "")

        if ear is not None:
            self.ear_var.set(f"EAR: {ear}")
        self.pattern_var.set(f"Pattern: {pattern}")
        self.text_var.set(f"Text: {text}")
        self.feedback_var.set(fb)

        # clear feedback after a short time
        if fb and time.time() - (state.get("fb_time", time.time())) > 2:
            state["feedback"] = ""

        self.root.after(50, self.update_ui)  # update every 50 ms

# Run the app
if __name__ == "__main__":
    root = tk.Tk()
    app = BlinkUI(root)
    root.mainloop()
