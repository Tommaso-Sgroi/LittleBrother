import cv2 as cv


def view(frame, *, scale=0.5, winname='Frame'):
    """
    :param frame: frame to draw on
    :param scale: scale factor to scale the frame by
    :return: stop the drawing of the frame
    :winname: name of the opencv window, use different names to create multiple windows
    """
    # Resize frame to    a normal view
    frame = cv.resize(frame, None, fx=scale, fy=scale, interpolation=cv.INTER_LINEAR)
    cv.imshow(winname, frame)
    key = cv.waitKey(1)
    if key in [27, ord('q'), ord('Q')]:
        return False
    return True
