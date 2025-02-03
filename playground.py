import threading
import time

import cv2

import torch
from ultralytics import YOLO

from face_recognizer.face_recognizer import FaceRecognizer


def process_video(video_path):
    # Each thread gets its own YOLO interpreter and FaceRecognizer
    yolo_model = YOLO("yolo11n.pt")
    face_recognizer = FaceRecognizer(threshold=0.5)

    start_time = time.time()
    frame_count = 0

    results = yolo_model(
        video_path,
        batch=3,
        classes=[0],
        device=(
            "cuda"
            if torch.cuda.is_available()
            else ("mps" if torch.mps.is_available() else "cpu")
        ),
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
                                f"[{video_path}] Detected face: {detected_face['label']} with confidence {detected_face['confidence']}"
                            )
                        # else:
                        #     print(f"[{video_path}] Detected unrecognized face! 😭")

        if frame_count % 30 == 0:
            elapsed_time = time.time() - start_time
            fps = frame_count / elapsed_time
            # print(f"[{video_path}] FPS: {fps:.2f}")

    total_time = time.time() - start_time
    average_fps = frame_count / total_time if total_time > 0 else 0
    print(f"\n[{video_path}] Average FPS: {average_fps:.2f}")
    print(f"[{video_path}] Total frames: {frame_count}")
    print(f"[{video_path}] Total time: {total_time:.2f}s\n")


def process_video_cv(video_path):
    # Each thread gets its own YOLO interpreter and FaceRecognizer
    yolo_model = YOLO("yolo11n.pt")
    face_recognizer = FaceRecognizer(threshold=0.5)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error opening video: {video_path}")
        return

    start_time = time.time()
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1

        results = yolo_model(
            frame,
            batch=3,
            classes=[0],
            device=(
                "cuda"
                if torch.cuda.is_available()
                else ("mps" if torch.mps.is_available() else "cpu")
            ),
            verbose=False,
        )

        for r in results:
            boxes = r.boxes.xyxy
            boxes_int = boxes.type(torch.int32)

            for box in boxes_int:
                x1, y1, x2, y2 = box
                if x2 - x1 < 20 or y2 - y1 < 20:
                    continue
                detected_person_image = frame[y1:y2, x1:x2]
                faces = face_recognizer.recognize_faces(detected_person_image)

                if len(faces) > 0:
                    for detected_face in faces:
                        if detected_face["label"] is not None:
                            print(
                                f"[{video_path}] Detected face: {detected_face['label']} with confidence {detected_face['confidence']}"
                            )
                        # else:
                        #     print(f"[{video_path}] Detected unrecognized face! 😭")

    cap.release()
    elapsed_time = time.time() - start_time
    average_fps = frame_count / elapsed_time if elapsed_time > 0 else 0
    print(f"\n[{video_path}] Average FPS: {average_fps:.2f}")
    print(f"[{video_path}] Total frames: {frame_count}")
    print(f"[{video_path}] Total time: {elapsed_time:.2f}s\n")


if __name__ == "__main__":
    video_paths = [
        "./datasets/new_video.mp4",
        # "./datasets/video1_1.mp4",
        # "./datasets/video1_5.mp4",
    ]
    threads = []

    for video in video_paths:
        t = threading.Thread(target=process_video, args=(video,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()
