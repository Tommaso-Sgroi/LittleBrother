from facenet_pytorch import MTCNN, InceptionResnetV1
import numpy as np
from PIL import Image, ImageDraw

frames_tracked = []

# Load a sample image
frame1 = Image.open("image1.jpg")
frame2 = Image.open("image2.jpg")
frame3 = Image.open("image3.jpg")


mtcnn = MTCNN(keep_all=True)

img_cropped_1 = mtcnn(frame1)
img_cropped_2 = mtcnn(frame2)
img_cropped_3 = mtcnn(frame3)
print(img_cropped_3.shape)

# frame_draw = frame.copy()
# draw = ImageDraw.Draw(frame_draw)
# for box in boxes:
#     draw.rectangle(box.tolist(), outline=(255, 0, 0), width=6)

# # Add to frame list
# frames_tracked.append(frame_draw)

##############################################################################################################

resnet = InceptionResnetV1(pretrained="vggface2").eval()


frame1_emb = resnet(img_cropped_1)
frame2_emb = resnet(img_cropped_2)
frame3_emb = resnet(img_cropped_3)


# cosine similarity
import torch

cos = torch.nn.CosineSimilarity(dim=1, eps=1e-6)

print(f"Similarity between p1 and p2: {cos(frame1_emb, frame2_emb)}")
print(f"Similarity between p1 and p3: {cos(frame1_emb, frame3_emb)}")
print(f"Similarity between p2 and p3: {cos(frame2_emb, frame3_emb)}")
