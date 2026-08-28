"""Camera Service for IP camera operations.

This service handles all camera-related operations including:
- Fetching frames from IP cameras
- Saving captured frames to disk
- Managing camera URLs and configuration
"""

import os
import time
import logging
from typing import Optional, Dict, Any

import requests

logger = logging.getLogger(__name__)


class CameraService:
    """Service for IP camera operations."""
    
    # Default camera URLs (can be overridden via settings)
    DEFAULT_VIDEO_URL = "http://192.168.2.173:4747/video"
    DEFAULT_FRAME_URL = "http://192.168.2.173:4747/cam/1/frame.jpg"
    
    # Request timeout in seconds
    REQUEST_TIMEOUT = 3
    
    @classmethod
    def get_video_url(cls) -> str:
        """Get the video stream URL.
        
        Returns:
            Video stream URL from settings or default
        """
        from django.conf import settings
        return getattr(settings, 'CAMERA_VIDEO_URL', cls.DEFAULT_VIDEO_URL)
    
    @classmethod
    def get_frame_url(cls) -> str:
        """Get the frame capture URL.
        
        Returns:
            Frame capture URL from settings or default
        """
        from django.conf import settings
        return getattr(settings, 'CAMERA_FRAME_URL', cls.DEFAULT_FRAME_URL)
    
    @classmethod
    def capture_frame(cls) -> Dict[str, Any]:
        """Capture a single frame from the IP camera.
        
        Returns:
            Dictionary with 'success', 'image_data', and optional 'error' keys
        """
        frame_url = cls.get_frame_url()
        
        try:
            logger.info(f"Capturing frame from: {frame_url}")
            resp = requests.get(frame_url, timeout=cls.REQUEST_TIMEOUT)
            resp.raise_for_status()
            
            return {
                'success': True,
                'image_data': resp.content
            }
            
        except requests.exceptions.Timeout:
            error_msg = f"Camera connection timed out after {cls.REQUEST_TIMEOUT}s"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
            
        except requests.exceptions.ConnectionError:
            error_msg = f"Could not connect to camera at {frame_url}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Camera request failed: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    @classmethod
    def save_frame(cls, image_data: bytes) -> Dict[str, Any]:
        """Save a captured frame to the media directory.
        
        Args:
            image_data: Raw image bytes to save
            
        Returns:
            Dictionary with 'success', 'filename', 'filepath', 'file_url', 
            and optional 'error' keys
        """
        from django.conf import settings
        
        try:
            # Ensure captures directory exists
            save_dir = os.path.join(settings.MEDIA_ROOT, "captures")
            os.makedirs(save_dir, exist_ok=True)
            
            # Generate filename with timestamp
            filename = f"capture_{int(time.time())}.jpg"
            filepath = os.path.join(save_dir, filename)
            
            # Save the image
            with open(filepath, "wb") as f:
                f.write(image_data)
            
            file_url = settings.MEDIA_URL + "captures/" + filename
            
            logger.info(f"Frame saved: {filename}")
            
            return {
                'success': True,
                'filename': filename,
                'filepath': filepath,
                'file_url': file_url
            }
            
        except Exception as e:
            error_msg = f"Failed to save frame: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    @classmethod
    def capture_and_save(cls) -> Dict[str, Any]:
        """Capture a frame from the camera and save it.
        
        Convenience method that combines capture_frame and save_frame.
        
        Returns:
            Dictionary with capture and save results
        """
        # Capture frame
        capture_result = cls.capture_frame()
        if not capture_result['success']:
            return capture_result
        
        # Save frame
        save_result = cls.save_frame(capture_result['image_data'])
        if not save_result['success']:
            return save_result
        
        # Return combined results
        return {
            'success': True,
            'filename': save_result['filename'],
            'filepath': save_result['filepath'],
            'file_url': save_result['file_url']
        }