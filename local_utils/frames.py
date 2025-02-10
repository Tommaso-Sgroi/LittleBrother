import cv2

def rescale_frame(frame, percent=50, interpolation=cv2.INTER_AREA):
    """
    Rescale the frame by a given percentage. 100 means no rescaling. 0 means width and height = 0.
    """
    percent = percent / 100
    if percent == 100: return frame

    width = int(frame.shape[1] * percent)
    height = int(frame.shape[0] * percent)
    dim = (width, height)
    return cv2.resize(frame, dim, interpolation=interpolation)