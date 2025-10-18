# BlinkTalk

**BlinkTalk** is an innovative human-computer interface that allows users to communicate and control applications using **eye blinks**. It detects short and long blinks, interprets them as **Morse code**, and maps them to letters or commands.

---

## Features
- **Real-time blink detection** using a webcam.
- **Morse code recognition** for letters (A-Z) and numbers (0-9).
- **Custom commands** triggered by specific blink patterns (e.g., LOCK, open YouTube).
- **Tkinter-based GUI** showing live camera feed, blink landmarks, detected pattern, and decoded text.
- Smooth detection using **EAR (Eye Aspect Ratio)** with noise filtering.
- Modular design for easy future extensions (TTS feedback, logging, or additional commands).

---

## Technology Stack
- Python 3.x  
- OpenCV (Computer Vision)  
- Mediapipe (Face Mesh / Eye landmarks)  
- Tkinter (GUI)  
- Standard Python libraries (threading, math, collections, time, os)

---

## How It Works
1. **Camera captures face landmarks** in real-time.
2. **Eye Aspect Ratio (EAR)** is computed to detect blinks.
3. **Short and long blinks** are mapped to `.` (dot) and `_` (dash).
4. **Patterns are converted to letters** using Morse code mapping.
5. **Special patterns trigger commands** like locking the system or opening YouTube.
6. GUI displays **live feed, EAR, blink pattern, and decoded text**.

---

## Usage
1. Run the GUI version:
```bash
python ui_blinktalk.py
