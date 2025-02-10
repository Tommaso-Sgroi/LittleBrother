import os

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from facenet_pytorch import MTCNN, InceptionResnetV1

from local_utils.logger import Logger


class FaceRecognizer(Logger):
    def __init__(
            self,
            threshold: float = 0.8,
            min_face_size: int = 20,
            device=torch.device("cpu"),
    ):
        """
        Initialize the face recognizer.
        Args:
            threshold: The cosine similarity threshold for face recognition.
            min_face_size: Minimum face size for detection
        """
        Logger.__init__(self, name=f"{self.__class__.__name__}")

        self.faces_dir = "registered_faces"
        os.makedirs(self.faces_dir, exist_ok=True)

        self.device = device

        self.mtcnn = MTCNN(keep_all=True, min_face_size=min_face_size)

        self.resnet = InceptionResnetV1(
            pretrained="vggface2", device=self.device
        ).eval()
        self.threshold = threshold
        self.min_face_size = min_face_size

        self.enrolled_embeddings = None
        self.enrolled_labels = None
        self.load_enrolled_faces()

    def load_enrolled_faces(self):
        """Load all enrolled face embeddings from files"""
        self.enrolled_embeddings = torch.empty((0, 512))
        self.enrolled_labels = []

        for filename in os.listdir(self.faces_dir):
            if filename.endswith(".npy"):
                label = os.path.splitext(filename)[0]
                embedding_path = os.path.join(self.faces_dir, filename)
                try:
                    # Load and ensure correct shape
                    embedding_np = np.load(embedding_path).astype(np.float32)
                    if len(embedding_np.shape) == 1:
                        embedding_np = embedding_np.reshape(1, -1)
                    embedding = torch.from_numpy(embedding_np)

                    if embedding.shape[1] != 512:
                        raise ValueError(f"Invalid embedding shape: {embedding.shape}")

                    self.enrolled_embeddings = torch.cat(
                        [self.enrolled_embeddings, embedding]
                    )
                    self.enrolled_labels.append(label)
                except Exception as e:
                    self.logger.error(f"Error loading embedding for %s: %s", label, e)
                    continue

    def enroll_face(self, face_image: Image, label: str) -> bool:
        """
        Enroll a new face with the given label.
        Args:
            face_image: PIL Image containing the face
            label: Label/name for the face
        Returns:
            bool: True if enrollment successful, False otherwise
        """
        embedding = self._get_embedding(face_image)
        if embedding is None:
            return False

        # Ensure correct shape and type
        embedding_np = embedding.detach().cpu().numpy().astype(np.float32)

        # Save embedding to individual file
        file_path = os.path.join(self.faces_dir, f"{label}.npy")
        np.save(file_path, embedding_np)

        self.enrolled_embeddings = torch.cat([self.enrolled_embeddings, embedding])
        self.enrolled_labels.append(label)
        return True

    def get_enrolled_faces(self) -> list:
        """
        Get list of enrolled users
        Returns:
            list: List of enrolled user labels
        """
        return self.enrolled_labels

    def delete_face(self, label: str) -> bool:
        """
        Delete an enrolled face
        Args:
            label: Label/name of the face to delete
        Returns:
            bool: True if deletion successful, False otherwise
        """
        if label not in self.enrolled_labels:
            return False

        file_path = os.path.join(self.faces_dir, f"{label}.npy")
        try:
            os.remove(file_path)
        except OSError:
            return False

        idx = self.enrolled_labels.index(label)
        self.enrolled_labels.pop(idx)
        self.enrolled_embeddings = torch.cat(
            [self.enrolled_embeddings[:idx], self.enrolled_embeddings[idx + 1:]]
        )
        return True

    def _get_embedding(self, face_image: Image) -> torch.Tensor:
        """Helper method to get face embedding"""
        faces = self.mtcnn(face_image)
        if faces is None or len(faces) == 0:
            return None

        if len(faces) > 1:
            self.logger.warning(
                "More than one face detected in the image. Using the first face only."
            )

        face_tensor = faces[0].unsqueeze(0).to(self.device)
        embedding = self.resnet(face_tensor)
        return embedding.to("cpu")

    def recognize_faces(self, images) -> list[dict]:
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

            faces = faces.detach().to(dtype=torch.float).to(self.device)

            embeddings = self.resnet(faces)

            if self.enrolled_embeddings.shape[0] == 0:
                self.logger.debug("No faces enrolled in the system!")
                return []

            enrolled_embeddings_device = self.enrolled_embeddings.to(self.device)
            similarities = F.cosine_similarity(
                embeddings.unsqueeze(1), enrolled_embeddings_device.unsqueeze(0), dim=-1
            )

            results = []
            for i in range(len(embeddings)):
                max_similarity, idx = torch.max(similarities[i], dim=0)

                label, confidence = None, None
                if max_similarity >= self.threshold:
                    label = self.enrolled_labels[idx]
                    confidence = float(max_similarity.cpu())
                result = {
                    "label": label,
                    "confidence": confidence,
                }
                results.append(result)
            if (
                    len(faces.shape) == 4
                    and "original_dim"
                    in locals()  # this is so cool 🤯; By tommie: Pythonic kind of stuff T_T
                    and len(original_dim) == 5
            ):
                results = [
                    results[i: i + original_dim[1]]
                    for i in range(0, len(results), original_dim[1])
                ]
            all_results.append(results)

        return all_results if len(all_results) > 1 else all_results[0]
