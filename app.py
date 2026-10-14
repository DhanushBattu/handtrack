import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from controller import Controller

# Download model from:
# https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
MODEL_PATH = 'hand_landmarker.task'


class LandmarkWrapper:
    """Wraps the new-style NormalizedLandmark list to behave like the old
    mp.solutions.hands result so controller.py can use .landmark[i].x/.y."""
    def __init__(self, landmark_list):
        self.landmark = landmark_list


# Hand connections for drawing (matches old mpHands.HAND_CONNECTIONS)
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),        # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),        # Index
    (0, 9), (9, 10), (10, 11), (11, 12),   # Middle
    (0, 13), (13, 14), (14, 15), (15, 16), # Ring
    (0, 17), (17, 18), (18, 19), (19, 20), # Pinky
    (5, 9), (9, 13), (13, 17),             # Palm
]

# Configure HandLandmarker with VIDEO running mode (synchronous per-frame)
base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    num_hands=1,
    min_hand_detection_confidence=0.5,
    min_hand_presence_confidence=0.5,
    min_tracking_confidence=0.5,
)
landmarker = vision.HandLandmarker.create_from_options(options)

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise SystemExit("No webcam found. Connect a camera and try again.")
frame_timestamp_ms = 0

while True:
    success, img = cap.read()
    if not success:
        print("Could not read a frame from the webcam; stopping.")
        break
    img = cv2.flip(img, 1)

    imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=imgRGB)

    # Detect hand landmarks
    result = landmarker.detect_for_video(mp_image, frame_timestamp_ms)
    frame_timestamp_ms += 33  # ~30 fps

    if result.hand_landmarks:
        landmarks = result.hand_landmarks[0]  # First hand

        # Wrap landmarks for controller compatibility
        Controller.hand_Landmarks = LandmarkWrapper(landmarks)

        # Draw landmarks on the image
        h, w, _ = img.shape
        for connection in HAND_CONNECTIONS:
            start_idx, end_idx = connection
            start = landmarks[start_idx]
            end = landmarks[end_idx]
            start_point = (int(start.x * w), int(start.y * h))
            end_point = (int(end.x * w), int(end.y * h))
            cv2.line(img, start_point, end_point, (0, 255, 0), 2)

        for lm in landmarks:
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.circle(img, (cx, cy), 5, (255, 0, 255), cv2.FILLED)

        Controller.update_fingers_status()
        Controller.cursor_moving()
        Controller.detect_scrolling()
        Controller.detect_zoomming()
        Controller.detect_clicking()
        Controller.detect_dragging()

    cv2.imshow('Hand Tracker', img)
    if cv2.waitKey(5) & 0xff == 27:
        break

landmarker.close()
cap.release()
cv2.destroyAllWindows()