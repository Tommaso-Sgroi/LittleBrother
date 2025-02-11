import os.path
from abc import abstractmethod, ABC

import yaml
from pathlib import Path
from typing import Any, Dict
from logging import INFO, DEBUG, WARNING, ERROR, CRITICAL



class ConfigException(Exception):
    pass

class SourceConfig(ABC):
    @abstractmethod
    def to_dict(self) -> dict:
        pass

class FrameSourceConfig(SourceConfig):
    def __init__(self, id, source):
        self.source = source
        self.id = id

    def to_dict(self) -> dict:
        """
        Returns a dict suitable for **kwargs unpacking.
        """
        return {
            "id": self.id,
            "source": self.source
        }

class QueuedFrameSourceConfig(FrameSourceConfig):
    def __init__(self, id, source, timeout:float, fps:int):
        super().__init__(id, source)
        self.timeout = timeout
        self.fps = fps
        # self.source_name = source_name

    def to_dict(self) -> dict:
        """
        Returns a dict suitable for **kwargs unpacking.
        """
        d = super().to_dict()
        d.update({
            "timeout": self.timeout,
            "fps": self.fps
        })
        return d


class VideoFrameSourceConfig(QueuedFrameSourceConfig):
    """
    Represents one camera/video source configuration (fields like 'source', 'name', etc.)
    """
    def __init__(
        self,
        id,
        source,
        name,
        device="cpu",
        yolo="yolo11n.pt",
        fps=30,
        timeout=0.1,
        scale_size=100,
        face_recogniser_threshold=0.5,
        motion_detector_threshold=0.5,
        motion_detector_min_area=500,
        motion_detector="mog2",
        view=True,
    ):
        super().__init__(id, source, timeout, fps)
        self.device = device
        self.name = name
        self.yolo = yolo
        self.scale_size = scale_size
        self.face_recogniser_threshold = face_recogniser_threshold
        self.motion_detector_threshold = motion_detector_threshold
        self.motion_detector_min_area = motion_detector_min_area
        self.motion_detector = motion_detector
        self.view = view

    def to_dict(self) -> dict:
        """
        Returns a dict suitable for **kwargs unpacking.
        """
        d = super().to_dict()
        d.update({
            "name": self.name,
            "device": self.device,
            "yolo": self.yolo,
            "scale_size": self.scale_size,
            "face_recogniser_threshold": self.face_recogniser_threshold,
            "motion_detector_threshold": self.motion_detector_threshold,
            "motion_detector_min_area": self.motion_detector_min_area,
            "motion_detector": self.motion_detector,
            "view": self.view,
        })
        return d


class VideoFrameControllerConfig:
    def __init__(self, max_queue_size, sources: list[QueuedFrameSourceConfig]):
        self.sources = sources
        self.max_queue_size = max_queue_size



class Config:
    """
    Classe di configurazione principale che raccoglie i parametri
    letti da un file YAML.
    """

    def __init__(self, config_dict: Dict[str, Any]):
        # Sezione bot
        self.telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN")
        self.auth_token: str = os.getenv("AUTH_TOKEN")

        if self.telegram_bot_token is None:
            raise ConfigException("TELEGRAM_BOT_TOKEN is not set")
        if self.auth_token is None:
            raise ConfigException("auth_token is not set")


        # Sezione database
        db_cfg = config_dict.get("database", {})
        self.db_path: str = db_cfg.get("path", os.getenv("DB_PATH"))
        self.drop_db: bool = db_cfg.get("drop_db", False)

        if self.db_path is None:
            raise ConfigException("DB_PATH is not set")

        # Sezione files
        files_cfg = config_dict.get("files", {})
        self.basedir_enroll_path: str = files_cfg.get("basedir_enroll_path", "registered_faces")
        os.makedirs(self.basedir_enroll_path, exist_ok=True)

        # Sezione frame_controller
        fc_cfg = config_dict.get("frame_controller", None)
        if fc_cfg is None:
            raise ConfigException("No frame_controller sources configured")

        frame_controllers_config = []
        for frame_crt in fc_cfg['sources']:
            if not isinstance(frame_crt, dict):
                raise ConfigException("Invalid frame_controller source configuration")
            source_cfg = VideoFrameSourceConfig(**frame_crt)
            frame_controllers_config.append(source_cfg)
        max_queue_size = fc_cfg.get("max_queue_size", None)

        self.video_frame_controller = VideoFrameControllerConfig(max_queue_size, frame_controllers_config)

        # Sezione logger
        logger_cfg = config_dict.get("logger", {})
        self.logger_config = {
            "level": logger_cfg.get("level", "INFO"),
            "format": logger_cfg.get("format", "%(asctime)s [%(levelname)s] %(name)s: %(message)s"),
            "datefmt": logger_cfg.get("datefmt", "%H:%M:%S"),
            "to_file": logger_cfg.get("to_file", False),
            "file_path": logger_cfg.get("file_path", "log.log"),
        }

        level = self.logger_config["level"]
        if level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ConfigException(f"Invalid log level: {level}")
        elif level == "DEBUG":
            self.logger_config["level"] = DEBUG
        elif level == "INFO":
            self.logger_config["level"] = INFO
        elif level == "WARNING":
            self.logger_config["level"] = WARNING
        elif level == "ERROR":
            self.logger_config["level"] = ERROR
        elif level == "CRITICAL":
            self.logger_config["level"] = CRITICAL

    def __str__(self):
        """
        Pretty-print the Config object, showing partially masked tokens,
        DB path, frame controllers, and logger config.
        """
        # Partially mask telegram bot token (show half)
        if self.telegram_bot_token:
            half_len = len(self.telegram_bot_token) // 2
            masked_bot_token = self.telegram_bot_token[:half_len] + "*" * (len(self.telegram_bot_token) - half_len)
        else:
            masked_bot_token = "None"

        # Completely mask auth_token
        masked_auth_token = "*" * len(self.auth_token) if self.auth_token else "None"

        # Build a string for each frame controller source
        frame_controller_config_str = f"{self.video_frame_controller.max_queue_size=}\n"
        for i, fc_source in enumerate(self.video_frame_controller.sources, start=1):
            frame_controller_config_str += f"  [Frame Source {i}]\n"
            # Convert the FrameControllerSource to dict and list out fields
            for key, val in fc_source.to_dict().items():
                frame_controller_config_str += f"    {key}={val}\n"
            frame_controller_config_str += "\n"

        logger_level = self.logger_config.get("level", "N/A")
        logger_format = self.logger_config.get("format", "N/A")

        return (
            f"{'-' * 10} Config {'-' * 10}\n" +
            f"Telegram Bot Token: {masked_bot_token}\n" +
            f"Auth Token: {masked_auth_token}\n" +
            f"DB Path: {self.db_path}\n" +
            f"Drop DB: {self.drop_db}\n" +
            f"Enroll Path: {self.basedir_enroll_path}\n" +
            f"Logger Level: {logger_level}\n" +
            f"Logger Format: {logger_format}\n" +
            f"\nFrame Controllers:\n{frame_controller_config_str}" +
            f"{'-' * 10} End Config {'-' * 10}\n"
        )


config: Config = None

def load_config(config_path: str = os.path.join('config', 'config.yaml')) -> Config:
    """
    Carica il file YAML 'config.yaml' e restituisce un oggetto Config.
    """
    global config
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    config = Config(data)
    return config



