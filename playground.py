import torch
import time
import cv2 as cv
from ultralytics import YOLO
from face_recognizer.face_recognizer import FaceRecognizer
from PIL import Image

yolo_model = YOLO("yolo11n.pt")
video_demo_path = "./datasets/new_video.mp4"
face_recognizer = FaceRecognizer(threshold=0.5)

# lorenzo = Image.open("./demo_images/lorenzo.png")
# lorenzo = lorenzo.convert("RGB")
# face_recognizer.enroll_face(lorenzo, "Lorenzo", overwrite=True)

# nunzia = Image.open("./demo_images/nunzia.png")
# nunzia = nunzia.convert("RGB")
# face_recognizer.enroll_face(nunzia, "Nunzia", overwrite=True)


# Initialize FPS counter
start_time = time.time()
frame_count = 0

results = yolo_model(
    # 1,
    video_demo_path,
    batch=3,
    classes=[0],
    device="mps",
    stream=True,
    verbose=False,
    stream_buffer=True,
    show=False,
)

for result in results:
    frame_count += 1
    if len(result) > 0:
        frame = result.orig_img
        people_floats = result.boxes.xyxy
        people_int = people_floats.type(torch.int32)

        for person in people_int:
            x1, y1, x2, y2 = person
            if x2 - x1 < 20 or y2 - y1 < 20:
                continue
            detected_person_image = frame[y1:y2, x1:x2]
            faces = face_recognizer.recognize_faces(detected_person_image)

            if len(faces) > 0:
                for detected_face in faces:
                    if detected_face["label"] is not None:
                        print(
                            f"Detected face: {detected_face['label']} with confidence {detected_face['confidence']}"
                        )
                    else:
                        print(f"Detected unrecognized face! 😭")

    # Calculate and display FPS every second
    if frame_count % 30 == 0:  # Update FPS every 30 frames
        elapsed_time = time.time() - start_time
        fps = frame_count / elapsed_time
        print(f"FPS: {fps:.2f}")

# Final FPS calculation
total_time = time.time() - start_time
average_fps = frame_count / total_time
print(f"\nAverage FPS: {average_fps:.2f}")
print(f"Total frames: {frame_count}")
print(f"Total time: {total_time:.2f}s")
