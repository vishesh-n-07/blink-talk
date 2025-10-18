import cv2, mediapipe as mp, math, time, os
from collections import deque

# ========== Setup ==========
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(min_detection_confidence=0.6, min_tracking_confidence=0.6)

EYE_AR_THRESH = 1.47
MIN_BLINK_TIME = 0.2
SHORT_BLINK_LIMIT = 0.35  # Below = dot, above = dash
LETTER_GAP = 1.5          # seconds pause = end of letter
SMOOTHING_FRAMES = 5

blink_start_time = None
pattern = ""
last_blink_time = time.time()
detected_text = ""
ear_history = deque(maxlen=SMOOTHING_FRAMES)

# Patterns for special commands
patterns = {
    "_ _ .": "LOCK",
    "_ . _ _ _ _": "YOUTUBE"
}

# Morse code dictionary
MORSE_CODE_DICT = {
    ".-": "A", "-...": "B", "-.-.": "C", "-..": "D", ".": "E",
    "..-.": "F", "--.": "G", "....": "H", "..": "I", ".---": "J",
    "-.-": "K", ".-..": "L", "--": "M", "-.": "N", "---": "O",
    ".--.": "P", "--.-": "Q", ".-.": "R", "...": "S", "-": "T",
    "..-": "U", "...-": "V", ".--": "W", "-..-": "X", "-.--": "Y", "--..": "Z",
    "-----": "0", ".----": "1", "..---": "2", "...--": "3", "....-": "4",
    ".....": "5", "-....": "6", "--...": "7", "---..": "8", "----.": "9"
}

def ear(landmarks, idx):
    p1, p2, p3, p4, p5, p6 = [landmarks[i] for i in idx]
    v1 = math.dist((p2.x, p2.y), (p4.x, p4.y))
    v2 = math.dist((p3.x, p3.y), (p5.x, p5.y))
    h = math.dist((p1.x, p1.y), (p6.x, p6.y))
    return (v1 + v2) / (2.0 * h)

cap = cv2.VideoCapture(0)
print("Camera warming up...")
time.sleep(3)
print("Ready! Blink detection + letter mapping started.")

while True:
    ok, frame = cap.read()
    if not ok:
        break
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = face_mesh.process(rgb)

    if res.multi_face_landmarks:
        lm = res.multi_face_landmarks[0].landmark
        left = [33, 160, 158, 133, 153, 144]
        right = [362, 385, 387, 263, 373, 380]
        leftEAR = ear(lm, left)
        rightEAR = ear(lm, right)
        avgEAR = (leftEAR + rightEAR) / 2.0

        ear_history.append(avgEAR)
        smoothed_EAR = sum(ear_history) / len(ear_history)

        for idx in left + right:
            x, y = int(lm[idx].x * w), int(lm[idx].y * h)
            cv2.circle(frame, (x, y), 1, (0, 255, 0), -1)

        cv2.putText(frame, f"EAR: {smoothed_EAR:.2f}", (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        # Blink detection
        if smoothed_EAR < EYE_AR_THRESH:
            if blink_start_time is None:
                blink_start_time = time.time()
        else:
            if blink_start_time:
                blink_duration = time.time() - blink_start_time
                blink_start_time = None

                if blink_duration >= MIN_BLINK_TIME:
                    blink_type = "_" if blink_duration > SHORT_BLINK_LIMIT else "."
                    pattern += blink_type + " "
                    last_blink_time = time.time()
                    print(f"Detected: {blink_type} ({blink_duration:.2f}s)")

        # Detect end of letter
        if (time.time() - last_blink_time) > LETTER_GAP and pattern.strip():
            morse = pattern.strip().replace(" ", "")
            letter = MORSE_CODE_DICT.get(morse, "")
            if letter:
                detected_text += letter
                print(f"✅ Letter Detected: {letter}")
            else:
                print(f"❌ Unrecognized pattern: {morse}")
            pattern = ""  # reset after decoding

        # Display
        cv2.putText(frame, f"Pattern: {pattern.strip()}", (30, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 200, 0), 2)
        cv2.putText(frame, f"Text: {detected_text}", (30, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 150), 2)

        # Command triggers
        for code, cmd in patterns.items():
            if pattern.strip() == code:
                cv2.putText(frame, f"COMMAND: {cmd}", (30, 160), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
                print(f"✅ Command recognized: {cmd}")
                pattern = ""
                if cmd == "LOCK":
                    os.system("rundll32.exe user32.dll,LockWorkStation")
                elif cmd == "YOUTUBE":
                    os.system("start https://www.youtube.com")
                time.sleep(2)

    cv2.imshow("BlinkTalk Letters+", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
