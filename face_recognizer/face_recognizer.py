import os

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from facenet_pytorch import MTCNN, InceptionResnetV1

from utils.logger import Logger


class FaceRecognizer(Logger):
    def __init__(self, threshold: float = 0.8, min_face_size: int = 20):
        """
        Initialize the face recognizer.
        Args:
            threshold: The cosine similarity threshold for face recognition.
        """

        Logger.__init__(self, name=f"{self.__class__.__name__}")

        os.makedirs("registered_faces", exist_ok=True)
        self.mtcnn = MTCNN(keep_all=True, min_face_size=min_face_size)
        self.resnet = InceptionResnetV1(pretrained="vggface2").eval()
        self.threshold = threshold
        self.min_face_size = min_face_size

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
                self.logger.warning(
                    f"Label '{img_label}' already exists. Skipping enrollment."
                )
                continue

            faces = self.mtcnn(image)

            if faces is None:
                self.logger.error("No faces detected in image")
                raise ValueError("No faces detected in image")

            if len(faces) > 1:
                self.logger.error("Multiple faces detected in image.")
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

    def recognize_faces(self, images) -> list:
        """
        Recognize faces in an image or a batch of images.
        Args:
            images: A single PIL Image or a list of PIL Images
        Returns:
            A list of results for each face in the input image(s)
        """
        faces_list = self.mtcnn(images)

        # Filter out empty results
        if faces_list is None or (
                isinstance(faces_list, list) and all(f is None for f in faces_list)
        ):
            self.logger.info("No faces detected in input")
            return []

        # Convert single output to list
        if not isinstance(faces_list, list):
            faces_list = [faces_list]

        # Filter out None faces
        faces_list = [f for f in faces_list if f is not None]
        if not faces_list:
            self.logger.info("No valid faces found in the input")
            return []

        all_results = []
        for faces in faces_list:
            # batch reshaping:
            # [batch_size, num_faces, channels, height, width] -> [batch_size * num_faces, channels, height, width]
            if len(faces.shape) == 5:
                original_dim = faces.shape
                faces = faces.reshape(-1, *original_dim[2:])

            # faces = torch.tensor(faces, dtype=torch.float)
            faces = faces.detach().to(dtype=torch.float)

            embeddings = self.resnet(faces)
            similarities = F.cosine_similarity(
                embeddings.unsqueeze(1), self.enrolled_embeddings.unsqueeze(0), dim=-1
            )

            results = []
            for i in range(len(embeddings)):
                max_similarity, idx = torch.max(similarities[i], dim=0)

                label, confidence = None, None
                if max_similarity >= self.threshold:
                    label = self.enrolled_labels[idx]
                    confidence = float(max_similarity)
                result = {
                    'label': label,
                    'confidence': confidence,
                }
                results.append(result)
            if (
                    len(faces.shape) == 4
                    and "original_dim" in locals()  # this is so cool 🤯; By tommie: Pythonic kind of stuff T_T
                    and len(original_dim) == 5
            ):
                results = [
                    results[i: i + original_dim[1]]
                    for i in range(0, len(results), original_dim[1])
                ]
            all_results.append(results)

        return all_results if len(all_results) > 1 else all_results[0]
