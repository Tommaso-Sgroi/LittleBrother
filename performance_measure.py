import time
from concurrent.futures import ProcessPoolExecutor

import cv2
import torch
from ultralytics import YOLO

from face_recognizer.face_recognizer import FaceRecognizer


def rescale_frame(frame, percent=50):
    width = int(frame.shape[1] * percent / 100)
    height = int(frame.shape[0] * percent / 100)
    dim = (width, height)
    return cv2.resize(frame, dim, interpolation=cv2.INTER_AREA)


def optical_flow_motion_detector(prev_frame, curr_frame, threshold=0.1):
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)

    flow = cv2.calcOpticalFlowFarneback(
        prev_gray,
        curr_gray,
        None,
        0.5,
        3,
        15,
        3,
        5,
        1.2,
        0,
    )

    mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])

    return mag.mean() > threshold


def mog2_motion_detector(bg_subtractor, frame, min_area=500):
    mask = bg_subtractor.apply(frame)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        if cv2.contourArea(cnt) > min_area:
            return True
    return False


def process_video_frames(video_path, motion_detector=None):
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
    total_frames = 0
    batch_frames = []
    batch_size = 3
    prev_frame = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        total_frames += 1
        frame = rescale_frame(frame, percent=50)

        if motion_detector is not None:
            if prev_frame is not None and not motion_detector(prev_frame, frame):
                prev_frame = frame
                continue
        prev_frame = frame

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
    average_fps = total_frames / total_time if total_time > 0 else 0
    print(f"\n[{video_path}] Average FPS: {average_fps:.2f}")
    print(f"[{video_path}] Total frames: {total_frames}")
    print(f"[{video_path}] Total time: {total_time:.2f}s\n")
    return average_fps


global_bg_subtractor = None


def mog2_detector_fn(prev_frame, curr_frame):
    global global_bg_subtractor
    if global_bg_subtractor is None:
        import cv2

        global_bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=10)
    return mog2_motion_detector(global_bg_subtractor, curr_frame)


def process_video_wrapper(args):
    video_path, detector = args
    return process_video_frames(video_path, detector)


if __name__ == "__main__":

    video_paths = [
        "./datasets/SamsungGear360.mp4",
        # "./datasets/new_video.mp4",
        # "./datasets/video1_1.mp4",
        # "./datasets/video1_3.mp4",
        # "./datasets/video1_5.mp4",
        # 1,  # MacBook webcam :)
    ]

    global_bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=10)

    motion_detector_options = {
        "No Motion Detector": None,
        "OpticalFlow": optical_flow_motion_detector,
        "MOG2": mog2_detector_fn,
    }

    results = {}
    for key, detector in motion_detector_options.items():
        print(f"\nRunning motion detection with {key}...")
        tasks = [(video, detector) for video in video_paths]
        with ProcessPoolExecutor(max_workers=len(video_paths)) as executor:
            fps_values = list(executor.map(process_video_wrapper, tasks))
        avg_fps = sum(fps_values) / len(fps_values) if fps_values else 0
        results[key] = avg_fps

    print("\nMotion Detection Average FPS Comparison:")
    for key, fps in results.items():
        print(f"  {key}: {fps} FPS")
