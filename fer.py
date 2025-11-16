import time
import collections
import cv2
from PIL import Image
from transformers import pipeline

from config import CAMERA_INDEX


# initialize face detector and FER pipeline
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
try:
    fer_pipe = pipeline("image-classification", model="trpakov/vit-face-expression")
except Exception:
    fer_pipe = None


def get_facial_expression(camera, duration: float = 5.0, sample_interval: float = 0.1):
    """Capture frames from provided OpenCV camera for duration seconds and return top two emotion labels."""
    end_time = time.time() + duration
    labels = []

    try:
        while time.time() < end_time:
            ret, frame = camera.read()
            if not ret:
                time.sleep(sample_interval)
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
            if len(faces) == 0:
                time.sleep(sample_interval)
                continue

            faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
            x, y, w, h = faces[0]
            face_img = frame[y:y+h, x:x+w]
            pil_face = Image.fromarray(cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB))

            try:
                if fer_pipe is not None:
                    res = fer_pipe(pil_face)
                    if res and isinstance(res, list) and 'label' in res[0]:
                        labels.append(res[0]['label'])
            except Exception:
                pass

            time.sleep(sample_interval)

        if not labels:
            return []
        counts = collections.Counter(labels)
        return [label for label, _ in counts.most_common(2)]
    except Exception:
        return []
