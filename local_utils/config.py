import os.path

import yaml
from pathlib import Path
from typing import Any, Dict
from logging import INFO, DEBUG, WARNING, ERROR, CRITICAL

class ConfigException(Exception):
    pass

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
        fc_cfg = config_dict.get("frame_controller", {})
        # Lo memorizziamo in un dict, così possiamo fare l'unpack per la funzione
        self.frame_controller_config = {
            "sources": fc_cfg.get("sources", ConfigException("sources is not set, they can be a list of integers or strings where integers are camera indexes and strings are paths to video files")),
            "yolo_model_name": fc_cfg.get("yolo_model_name", ConfigException("yolo_model_name is not set, choose one of the available models")),
            "max_queue_size": fc_cfg.get("max_queue_size", None),
            "fps": fc_cfg.get("fps", 30),
            "timeout": fc_cfg.get("timeout", 0.1),
            "scale_size": fc_cfg.get("scale_size", 100),
            "view": fc_cfg.get("view", False),
            "device": fc_cfg.get("device", "cpu"),
            "face_recogniser_threshold": fc_cfg.get("face_recogniser_threshold", 0.5)
        }
        for k, v in self.frame_controller_config.items():
            if isinstance(v, ConfigException):
                raise v

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
        frame_controller_config_str = "\n".join([f"{k}={v}" for k, v in self.frame_controller_config.items()])
        return '-'*10 + "config" + '-' * 10 + '\n' +\
                 f"Config(\ntelegram_bot_token={self.telegram_bot_token[:len(self.telegram_bot_token)//2]}\nauth_token={'*'*len(self.auth_token)}\ndb_path={self.db_path}\ndrop_db={self.drop_db}\nbasedir_enroll_path={self.basedir_enroll_path}\n"+\
            f"frame_controller_config={frame_controller_config_str}\n)\n" + \
            '-' * 10 + "config" + '-' * 10

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



