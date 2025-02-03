import time
from concurrent.futures import ProcessPoolExecutor

import cv2
import torch
from ultralytics import YOLO

from face_recognizer.face_recognizer import FaceRecognizer


def process_video_frames(video_path):
    # Each process gets its own model and face recognizer
    device = (
        "cuda"
        if torch.cuda.is_available()
        else ("mps" if torch.backends.mps.is_available() else "cpu")
    )
    yolo_model = YOLO("yolo11n.pt")
    face_recognizer = FaceRecognizer(threshold=0.5)  # device=device)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error opening video: {video_path}")
        return

    start_time = time.time()
    frame_count = 0
    batch_frames = []
    batch_size = 3

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        batch_frames.append(frame)
        frame_count += 1

        # When the batch is full or end-of-video is reached, process the batch.
        if len(batch_frames) == batch_size:
            results = yolo_model(
                batch_frames, classes=[0], device=device, verbose=False
            )
            for result, frame in zip(results, batch_frames):
                boxes = result.boxes.xyxy.type(torch.int32)
                for box in boxes:
                    x1, y1, x2, y2 = box
                    if x2 - x1 < 20 or y2 - y1 < 20:
                        continue
                    detected_person_image = frame[y1:y2, x1:x2]
                    faces = face_recognizer.recognize_faces(detected_person_image)
                    for detected_face in faces:
                        if detected_face["label"] is not None:
                            print(
                                f"[{video_path}] Detected face: {detected_face['label']} with confidence {detected_face['confidence']}"
                            )
            batch_frames = []

    # Process any remaining frames in the batch
    if batch_frames:
        results = yolo_model(batch_frames, classes=[0], device=device, verbose=False)
        for result, frame in zip(results, batch_frames):
            boxes = result.boxes.xyxy.type(torch.int32)
            for box in boxes:
                x1, y1, x2, y2 = box
                if x2 - x1 < 20 or y2 - y1 < 20:
                    continue
                detected_person_image = frame[y1:y2, x1:x2]
                faces = face_recognizer.recognize_faces(detected_person_image)
                for detected_face in faces:
                    if detected_face["label"] is not None:
                        print(
                            f"[{video_path}] Detected face: {detected_face['label']} with confidence {detected_face['confidence']}"
                        )

    cap.release()
    total_time = time.time() - start_time
    average_fps = frame_count / total_time if total_time > 0 else 0
    print(f"\n[{video_path}] Average FPS: {average_fps:.2f}")
    print(f"[{video_path}] Total frames: {frame_count}")
    print(f"[{video_path}] Total time: {total_time:.2f}s\n")


if __name__ == "__main__":
    video_paths = [
        "./datasets/new_video.mp4",
        "./datasets/video1_1.mp4",
        # "./datasets/video1_5.mp4",
        # 1,  # MacBook webcam :)
    ]

    with ProcessPoolExecutor(max_workers=len(video_paths)) as executor:
        executor.map(process_video_frames, video_paths)
