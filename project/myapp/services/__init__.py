"""Ai-WildEye Services Package.

This package contains service modules that handle specific business logic.
Services are designed to be reusable and testable, while maintaining
backward compatibility with the existing views.
"""

from .ml_service import MLService
from .camera_service import CameraService
from .email_service import EmailService
from .video_service import VideoService
from .auth_service import AuthService

__all__ = [
    'MLService',
    'CameraService', 
    'EmailService',
    'VideoService',
    'AuthService',
]