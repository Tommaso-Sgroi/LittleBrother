import numpy as np
import cv2 as cv

cap = cv.VideoCapture(cv.samples.findFile("SamsungGear360.mp4"))
ret, frame1 = cap.read()
scale = 0.5  # Resize factor to speed up processing
frame1 = cv.resize(frame1, (0, 0), fx=scale, fy=scale)
prvs = cv.cvtColor(frame1, cv.COLOR_BGR2GRAY)

hsv = np.zeros_like(frame1)
hsv[..., 1] = 255

while True:
    ret, frame2 = cap.read()
    if not ret:
        print("No frames grabbed!")
        break

    frame2 = cv.resize(frame2, (0, 0), fx=scale, fy=scale)
    next = cv.cvtColor(frame2, cv.COLOR_BGR2GRAY)

    flow = cv.calcOpticalFlowFarneback(prvs, next, None, 0.5, 3, 15, 3, 5, 1.2, 0)

    mag, ang = cv.cartToPolar(flow[..., 0], flow[..., 1])
    hsv[..., 0] = ang * 180 / np.pi / 2
    hsv[..., 2] = cv.normalize(mag, None, 0, 255, cv.NORM_MINMAX)
    bgr = cv.cvtColor(hsv, cv.COLOR_HSV2BGR)

    cv.imshow("Optical Flow", bgr)
    k = cv.waitKey(30) & 0xFF
    if k == 27:  # ESC to quit
        break
    elif k == ord("s"):  # Save images
        cv.imwrite("opticalfb.png", frame2)
        cv.imwrite("opticalhsv.png", bgr)

    prvs = next

cap.release()
cv.destroyAllWindows()
