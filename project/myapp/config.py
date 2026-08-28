"""Configuration module for Ai-WildEye.

This module provides centralized configuration management.
Settings can be overridden via environment variables or Django settings.
"""

import os
import logging
from typing import List

logger = logging.getLogger(__name__)


class Config:
    """Centralized configuration class."""
    
    # Camera Configuration
    CAMERA_VIDEO_URL = os.environ.get(
        'WILDEYE_CAMERA_VIDEO_URL', 
        'http://192.168.2.173:4747/video'
    )
    CAMERA_FRAME_URL = os.environ.get(
        'WILDEYE_CAMERA_FRAME_URL',
        'http://192.168.2.173:4747/cam/1/frame.jpg'
    )
    CAMERA_TIMEOUT = int(os.environ.get('WILDEYE_CAMERA_TIMEOUT', '3'))
    
    # ML Model Configuration
    ML_MODEL_PATH = os.environ.get(
        'WILDEYE_ML_MODEL_PATH',
        'backend/ml/mobilenet_animal_classifier_cpu.h5'
    )
    ML_LABELS_PATH = os.environ.get(
        'WILDEYE_ML_LABELS_PATH',
        'backend/ml/labels.txt'
    )
    ML_CONFIDENCE_THRESHOLD = float(os.environ.get(
        'WILDEYE_ML_CONFIDENCE_THRESHOLD',
        '65.0'
    ))
    ML_INPUT_SIZE = (160, 160)
    
    # Video Processing Configuration
    VIDEO_FPS = int(os.environ.get('WILDEYE_VIDEO_FPS', '3'))
    VIDEO_EXTRACTED_DIR = 'data/extracted'
    VIDEO_BATCH_FILE = 'data/r.bat'
    
    # Email Configuration
    EMAIL_SMTP_HOST = os.environ.get('WILDEYE_EMAIL_SMTP_HOST', 'smtp.gmail.com')
    EMAIL_SMTP_PORT = int(os.environ.get('WILDEYE_EMAIL_SMTP_PORT', '587'))
    EMAIL_SENDER = os.environ.get('WILDEYE_EMAIL_SENDER', 'wildeye2026@gmail.com')
    EMAIL_PASSWORD = os.environ.get('WILDEYE_EMAIL_PASSWORD', 'rgww pfxi huno frig')
    
    # Alert Labels - Animals that trigger wild animal alerts
    ALERT_LABELS: List[str] = [
        'Buffalo',
        'ELEPHANT',
        'LION',
        'Rhino',
        'Zebra',
        'black',
        'grizzly',
        'panda',
        'polar',
        'Tiger'
    ]
    
    # Session Configuration
    SESSION_USER_NAME = 'user_name'
    SESSION_USER_ID = 'user_id'
    
    # Media Configuration
    MEDIA_CAPTURES_DIR = 'captures'
    
    @classmethod
    def get_alert_labels(cls) -> List[str]:
        """Get the list of alert labels.
        
        Returns:
            List of animal labels that trigger alerts
        """
        return cls.ALERT_LABELS.copy()
    
    @classmethod
    def is_alert_label(cls, label: str) -> bool:
        """Check if a label is an alert label.
        
        Args:
            label: Animal label to check
            
        Returns:
            True if label triggers alerts, False otherwise
        """
        return label in cls.ALERT_LABELS