"""Camera Service for IP camera operations.

This service handles all camera-related operations including:
- Fetching frames from IP cameras
- Saving captured frames to disk
- Managing camera URLs and configuration
"""

import os
import glob
import time
import shutil
import logging
import subprocess
from typing import Optional, Dict, Any

import requests

logger = logging.getLogger(__name__)


class CameraService:
    """Service for IP camera operations."""
    
    # Default camera URLs (can be overridden via settings)
    DEFAULT_VIDEO_URL = "http://192.168.2.173:4747/video"
    DEFAULT_FRAME_URL = "http://192.168.2.173:4747/cam/1/frame.jpg"
    
    # Default IP address and stream configuration
    DEFAULT_IP = "192.168.2.173"
    IP_PORT = 4747
    VIDEO_PATH = "/video"
    FRAME_PATH = "/cam/1/frame.jpg"
    
    # Request timeout in seconds
    REQUEST_TIMEOUT = 3

    @classmethod
    def _resolve_ip(cls, ip: Optional[str]) -> Optional[str]:
        """Return the effective IP address to use.

        Args:
            ip: The IP address provided by the user, or None.

        Returns:
            The provided (trimmed) IP if given, otherwise None.
        """
        if ip and str(ip).strip():
            return str(ip).strip()
        return None

    @classmethod
    def build_base_url(cls, ip: Optional[str] = None) -> str:
        """Build the base HTTP URL for an IP camera.

        Args:
            ip: The IP camera address. If None, falls back to settings/default.

        Returns:
            The base camera URL string (without path).
        """
        effective_ip = cls._resolve_ip(ip)
        if effective_ip is None:
            return f"http://{cls.DEFAULT_IP}:{cls.IP_PORT}"
        return f"http://{effective_ip}:{cls.IP_PORT}"

    @classmethod
    def build_video_url(cls, ip: Optional[str] = None) -> str:
        """Build a video stream URL from an IP address.

        Args:
            ip: The IP camera address. If None, falls back to settings/default.

        Returns:
            The video stream URL string.
        """
        from django.conf import settings
        effective_ip = cls._resolve_ip(ip)
        if effective_ip is None:
            return getattr(settings, 'CAMERA_VIDEO_URL', cls.DEFAULT_VIDEO_URL)
        return f"http://{effective_ip}:{cls.IP_PORT}{cls.VIDEO_PATH}"

    @classmethod
    def build_frame_url(cls, ip: Optional[str] = None) -> str:
        """Build a frame capture URL from an IP address.

        Args:
            ip: The IP camera address. If None, falls back to settings/default.

        Returns:
            The frame capture URL string.
        """
        from django.conf import settings
        effective_ip = cls._resolve_ip(ip)
        if effective_ip is None:
            return getattr(settings, 'CAMERA_FRAME_URL', cls.DEFAULT_FRAME_URL)
        return f"http://{effective_ip}:{cls.IP_PORT}{cls.FRAME_PATH}"

    @classmethod
    def get_video_url(cls, ip: Optional[str] = None) -> str:
        """Get the video stream URL.

        Args:
            ip: Optional IP address of the camera.

        Returns:
            Video stream URL from settings, built from the IP, or default
        """
        return cls.build_video_url(ip)
    
    @classmethod
    def get_frame_url(cls, ip: Optional[str] = None) -> str:
        """Get the frame capture URL.

        Args:
            ip: Optional IP address of the camera.

        Returns:
            Frame capture URL from settings, built from the IP, or default
        """
        return cls.build_frame_url(ip)
    
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

        from django.conf import settings
        base_dir = getattr(settings, 'BASE_DIR', None) or os.getcwd()
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
    def _grab_frame_from_stream(cls, ip: Optional[str] = None) -> Optional[bytes]:
        """Grab a single JPEG frame from the MJPEG video stream using ffmpeg.

        Some IP cameras (e.g. DroidCam) only expose a live MJPEG stream at
        ``/video`` and do not serve a still-frame endpoint, so we extract a
        single frame from the stream directly.

        Args:
            ip: Optional IP address of the camera.

        Returns:
            Raw JPEG bytes if a frame was captured, otherwise None.
        """
        ffmpeg_path = cls._get_ffmpeg_path()
        if not ffmpeg_path:
            logger.error("FFmpeg not found; cannot grab frame from stream")
            return None

        video_url = cls.get_video_url(ip)
        out_path = os.path.join(os.environ.get('TEMP', '/tmp'), f"camframe_{int(time.time() * 1000)}.jpg")
        logger.info(f"Grabbing frame from stream: {video_url}")

        try:
            # -loglevel error silences ffmpeg's banner; -nostdin avoids hangs
            cmd = f'"{ffmpeg_path}" -loglevel error -nostdin -y -i "{video_url}" -frames:v 1 -q:v 2 -update 1 "{out_path}"'
            subprocess.call(cmd, shell=True, timeout=cls.REQUEST_TIMEOUT + 5)

            if not os.path.exists(out_path):
                logger.error("FFmpeg did not produce a frame file")
                return None

            with open(out_path, "rb") as f:
                data = f.read()
            return data or None

        except Exception as e:
            logger.error(f"Failed to grab frame from stream: {e}")
            return None
        finally:
            try:
                if os.path.exists(out_path):
                    os.remove(out_path)
            except OSError:
                pass

    @classmethod
    def capture_frame(cls, ip: Optional[str] = None) -> Dict[str, Any]:
        """Capture a single frame from the IP camera.

        First attempts the standard still-frame endpoint (``/cam/1/frame.jpg``).
        If the camera does not provide one, falls back to extracting a frame
        from the live MJPEG stream using ffmpeg.

        Args:
            ip: Optional IP address of the camera.

        Returns:
            Dictionary with 'success', 'image_data', and optional 'error' keys
        """
        frame_url = cls.get_frame_url(ip)
        try:
            logger.info(f"Capturing frame from: {frame_url}")
            resp = requests.get(frame_url, timeout=cls.REQUEST_TIMEOUT)
            resp.raise_for_status()

            if not resp.content:
                raise requests.exceptions.RequestException("Empty frame from camera")

            return {
                'success': True,
                'image_data': resp.content
            }

        except requests.exceptions.RequestException as e:
            # Standard snapshot endpoint failed -> try grabbing from MJPEG stream.
            logger.warning(f"Snapshot endpoint failed ({e}); trying MJPEG stream grab")
            image_data = cls._grab_frame_from_stream(ip)
            if image_data is None:
                error_msg = (
                    f"Could not capture a frame from the camera. "
                    f"Snapshot ({frame_url}) failed and no MJPEG stream frame was returned."
                )
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            return {'success': True, 'image_data': image_data}

    @classmethod
    def test_connection(cls, ip: Optional[str] = None) -> Dict[str, Any]:
        """Check whether the IP camera is reachable.

        Contacts the camera's base HTTP page, which responds quickly and does
        not consume the live MJPEG stream (frame grabbing would compete with
        the browser's live feed on single-stream cameras). This is used to
        verify a camera is actually connected before saving the IP address.

        Args:
            ip: Optional IP address of the camera to check.

        Returns:
            Dictionary with 'success', 'video_url', and optional 'error' keys.
        """
        video_url = cls.get_video_url(ip)
        base_url = cls.build_base_url(ip)

        try:
            logger.info(f"Testing camera connection at: {base_url}")
            resp = requests.get(base_url, timeout=cls.REQUEST_TIMEOUT)
            resp.raise_for_status()
            return {'success': True, 'video_url': video_url}

        except requests.exceptions.Timeout:
            error_msg = "Camera connection timed out. Check the IP address and that the camera is online."
            logger.error(error_msg)
            return {'success': False, 'error': error_msg, 'video_url': video_url}

        except requests.exceptions.ConnectionError:
            error_msg = f"Could not connect to camera at {base_url}. Check the IP address and network."
            logger.error(error_msg)
            return {'success': False, 'error': error_msg, 'video_url': video_url}

        except requests.exceptions.RequestException as e:
            error_msg = f"Camera connection failed: {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg, 'video_url': video_url}

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
    def capture_and_save(cls, ip: Optional[str] = None) -> Dict[str, Any]:
        """Capture a frame from the camera and save it.
        
        Convenience method that combines capture_frame and save_frame.

        Args:
            ip: Optional IP address of the camera.
        
        Returns:
            Dictionary with capture and save results
        """
        # Capture frame
        capture_result = cls.capture_frame(ip)
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