"""Video Service for video processing operations.

This service handles all video-related operations including:
- Extracting frames from videos using ffmpeg
- Managing temporary extraction directories
- Video file validation
"""

import os
import glob
import shutil
import subprocess
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class VideoService:
    """Service for video processing operations."""
    
    # Default extraction settings
    DEFAULT_FPS = 3  # Frames per second to extract
    EXTRACTED_DIR = 'data/extracted'
    BATCH_FILE = 'data/r.bat'
    
    @classmethod
    def _get_base_dir(cls) -> str:
        """Get the project base directory."""
        from django.conf import settings
        return str(settings.BASE_DIR)
    
    @classmethod
    def _get_extracted_path(cls) -> str:
        """Get the path for extracted frames."""
        return os.path.join(cls._get_base_dir(), cls.EXTRACTED_DIR)
    
    @classmethod
    def _get_batch_path(cls) -> str:
        """Get the path for the batch file."""
        return os.path.join(cls._get_base_dir(), cls.BATCH_FILE)
    
    @classmethod
    def _ensure_extracted_dir(cls) -> str:
        """Ensure the extracted frames directory exists.
        
        Returns:
            Path to the extracted directory
        """
        extracted_path = cls._get_extracted_path()
        
        # Clean up existing directory
        if os.path.exists(extracted_path):
            shutil.rmtree(extracted_path, ignore_errors=True)
        
        # Create fresh directory
        os.makedirs(extracted_path, exist_ok=True)
        
        return extracted_path

    @classmethod
    def _get_ffmpeg_path(cls) -> Optional[str]:
        """Locate the ffmpeg executable.
        
        Checks the system PATH first, then falls back to the bundled
        ffmpeg build shipped inside the project root (or BASE_DIR).
        
        Returns:
            Path to ffmpeg.exe if found, None otherwise
        """
        exe = shutil.which('ffmpeg')
        if exe:
            return exe
        
        base_dir = cls._get_base_dir()
        project_root = os.path.abspath(os.path.join(base_dir, os.pardir))
        
        patterns = [
            os.path.join(project_root, 'ffmpeg-*', 'bin', 'ffmpeg.exe'),
            os.path.join(project_root, 'ffmpeg-*', 'ffmpeg-*', 'bin', 'ffmpeg.exe'),
            os.path.join(base_dir, 'ffmpeg-*', 'bin', 'ffmpeg.exe'),
            os.path.join(base_dir, 'ffmpeg-*', 'ffmpeg-*', 'bin', 'ffmpeg.exe'),
        ]
        
        for pattern in patterns:
            matches = glob.glob(pattern)
            if matches:
                logger.info(f"Using bundled ffmpeg: {matches[0]}")
                return matches[0]
        
        return None
    
    @classmethod
    def convert(
        cls,
        video_path: str,
        fps: Optional[int] = None
    ) -> Dict[str, Any]:
        """Extract frames from a video file using ffmpeg.
        
        Args:
            video_path: Path to the video file
            fps: Frames per second to extract (default: 3)
            
        Returns:
            Dictionary with 'success', 'extracted_path', and optional 'error' keys
        """
        if fps is None:
            fps = cls.DEFAULT_FPS
        
        ffmpeg_path = cls._get_ffmpeg_path()
        if not ffmpeg_path:
            error_msg = "FFmpeg not found on system PATH or in project"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        
        try:
            extracted_path = cls._ensure_extracted_dir()
            
            # Build ffmpeg command
            cmd = f'"{ffmpeg_path}" -y -i "{video_path}" -vf fps={fps} "{extracted_path}/frame_%03d.jpg"'
            
            logger.info(f"Extracting frames from video: {video_path}")
            logger.debug(f"FFmpeg command: {cmd}")
            
            # Write command to batch file (Windows compatibility)
            batch_path = cls._get_batch_path()
            with open(batch_path, "w") as f:
                f.write(cmd)
            
            # Execute ffmpeg
            returncode = subprocess.call(cmd, shell=True)
            
            if returncode != 0:
                error_msg = f"FFmpeg exited with code {returncode}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }
            
            # Count extracted frames
            frame_count = len([f for f in os.listdir(extracted_path) 
                             if f.endswith(('.jpg', '.jpeg', '.png'))])
            
            logger.info(f"Extracted {frame_count} frames to: {extracted_path}")
            
            return {
                'success': True,
                'extracted_path': extracted_path,
                'frame_count': frame_count
            }
            
        except Exception as e:
            error_msg = f"Video conversion failed: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    @classmethod
    def cleanup_extracted(cls) -> bool:
        """Clean up the extracted frames directory.
        
        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            extracted_path = cls._get_extracted_path()
            if os.path.exists(extracted_path):
                shutil.rmtree(extracted_path, ignore_errors=True)
                logger.info("Cleaned up extracted frames directory")
            return True
        except Exception as e:
            logger.warning(f"Failed to cleanup extracted directory: {e}")
            return False
    
    @classmethod
    def get_video_path(cls, filename: str) -> str:
        """Get the full path to a video file in the media directory.
        
        Args:
            filename: Video filename
            
        Returns:
            Full path to the video file
        """
        from django.conf import settings
        return os.path.join(settings.MEDIA_ROOT, filename)