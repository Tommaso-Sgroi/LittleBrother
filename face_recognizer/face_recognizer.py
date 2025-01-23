import os

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from facenet_pytorch import MTCNN, InceptionResnetV1


def print_in_red(text):
    print("\033[91m {}\033[00m".format(text))


class FaceRecognizer:
    def __init__(self, threshold: float = 0.8):
        """
        Initialize the face recognizer.
        Args:
            threshold: The cosine similarity threshold for face recognition.
        """

        os.makedirs("registered_faces", exist_ok=True)
        self.mtcnn = MTCNN(keep_all=True)
        self.resnet = InceptionResnetV1(pretrained="vggface2").eval()
        self.threshold = threshold

        embeddings_path = "registered_faces/embeddings.npy"
        labels_path = "registered_faces/labels.npy"

        if os.path.exists(embeddings_path) and os.path.exists(labels_path):
            self.enrolled_embeddings = torch.tensor(
                np.load(embeddings_path), dtype=torch.float
            )
            self.enrolled_labels = np.load(labels_path, allow_pickle=True).tolist()
        else:
            self.enrolled_embeddings = torch.empty((0, 512))
            self.enrolled_labels = []

    def enroll_face(self, images, label, overwrite=False):
        """
        Enroll a face in the face recognizer.
        Args:
            images: A single PIL Image or a list of PIL Images
            label: The label for the enrolled face
            overwrite: If True, overwrites existing face with same label
        """
        if isinstance(images, Image.Image):
            images = [images]
            label = [label]

        if len(images) != len(label):
            raise ValueError("Number of images and labels must match")

        for image, img_label in zip(images, label):
            if img_label in self.enrolled_labels and not overwrite:
                print_in_red(
                    f"Label '{img_label}' already exists. Skipping enrollment."
                )
                continue

            faces = self.mtcnn(image)

            if faces is None:
                raise ValueError("No faces detected in image")

            if len(faces) > 1:
                raise ValueError(
                    "Multiple faces detected in image. Please provide an image with exactly one face."
                )

            embedding = self.resnet(faces[0].unsqueeze(0))

            if img_label in self.enrolled_labels:
                idx = self.enrolled_labels.index(img_label)
                self.enrolled_embeddings[idx] = embedding
            else:
                self.enrolled_embeddings = torch.cat(
                    [self.enrolled_embeddings, embedding], dim=0
                )
                self.enrolled_labels.append(img_label)

        np.save(
            "registered_faces/embeddings.npy",
            self.enrolled_embeddings.detach().numpy(),
        )
        np.save(
            "registered_faces/labels.npy",
            np.array(self.enrolled_labels, dtype=object),
        )

    def recognize_faces(self, image):
        """
        Recognize faces in an image.
        Args:
            image: A PIL Image
        Returns:
            A list of tuples containing the label and cosine similarity score for each recognized face
        """
        faces = self.mtcnn(image)

        if faces is None:
            raise ValueError("No faces detected in image")

        embeddings = self.resnet(faces)
        results = []

        similarities = F.cosine_similarity(
            embeddings.unsqueeze(1), self.enrolled_embeddings.unsqueeze(0), dim=-1
        )

        for i in range(len(embeddings)):
            max_similarity, idx = torch.max(similarities[i], dim=0)
            if max_similarity < self.threshold:
                results.append((None, None))
                continue

            results.append((self.enrolled_labels[idx], max_similarity.item()))

        return results
