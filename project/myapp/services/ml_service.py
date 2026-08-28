"""Machine Learning Service for animal classification.

This service handles all ML-related operations including:
- Loading the MobileNetV2 model
- Predicting animals from images
- Predicting animals from video frames

The model and labels are loaded lazily on first use.
"""

import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class MLService:
    """Service for ML-based animal classification."""
    
    _model = None
    _labels = None
    
    # Default paths (can be overridden via settings)
    DEFAULT_MODEL_PATH = 'backend/ml/mobilenet_animal_classifier_cpu.h5'
    DEFAULT_LABELS_PATH = 'backend/ml/labels.txt'
    
    # Confidence threshold for predictions
    CONFIDENCE_THRESHOLD = 65.0
    
    @classmethod
    def _get_base_dir(cls) -> str:
        """Get the project base directory."""
        from django.conf import settings
        return str(settings.BASE_DIR)
    
    @classmethod
    def load_model(cls, model_path: Optional[str] = None) -> None:
        """Load the ML model and labels.
        
        Args:
            model_path: Optional path to the model file. 
                       If None, uses default path.
        """
        try:
            from tensorflow.keras.models import load_model
            
            if model_path is None:
                base_dir = cls._get_base_dir()
                model_path = os.path.join(base_dir, cls.DEFAULT_MODEL_PATH)
            
            labels_path = os.path.join(cls._get_base_dir(), cls.DEFAULT_LABELS_PATH)
            
            logger.info(f"Loading model from: {model_path}")
            cls._model = load_model(model_path)
            
            with open(labels_path, "r") as f:
                cls._labels = [line.strip() for line in f.readlines()]
            
            logger.info(f"Model loaded successfully. Labels: {cls._labels}")
            
        except Exception as e:
            logger.error(f"Failed to load ML model: {e}")
            raise
    
    @classmethod
    def _ensure_model_loaded(cls) -> None:
        """Ensure the model is loaded before making predictions."""
        if cls._model is None:
            cls.load_model()
    
    @classmethod
    def predict_from_file(
        cls, 
        model_path: Optional[str] = None,
        labels_path: Optional[str] = None,
        input_image: str = "test/r01.jpg"
    ) -> Dict[str, str]:
        """Predict animal from a single image file.
        
        Args:
            model_path: Optional path to model file
            labels_path: Optional path to labels file
            input_image: Path to the image file to classify
            
        Returns:
            Dictionary with 'animal' and 'match' keys
        """
        try:
            import numpy as np
            from tensorflow.keras.preprocessing import image
            from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
            
            cls._ensure_model_loaded()
            
            # Load and preprocess image
            img = image.load_img(input_image, target_size=(160, 160))
            img_array = image.img_to_array(img)
            img_array = np.expand_dims(img_array, axis=0)
            img_array = preprocess_input(img_array)
            
            # Make prediction
            pred = cls._model.predict(img_array)
            class_idx = np.argmax(pred)
            confidence = np.max(pred) * 100
            
            animal = cls._labels[class_idx]
            logger.info(f"Prediction: {animal} ({confidence:.2f}% confidence)")
            
            # Apply confidence threshold
            if confidence > cls.CONFIDENCE_THRESHOLD:
                return {
                    'animal': animal,
                    'match': f'{confidence:.2f}%'
                }
            else:
                return {
                    'animal': 'Not Detected',
                    'match': '0%'
                }
                
        except Exception as e:
            logger.error(f"Prediction failed for {input_image}: {e}")
            return {
                'animal': 'Error',
                'match': '0%'
            }
    
    @classmethod
    def predict_from_dir(
        cls,
        model_path: Optional[str] = None,
        labels_path: Optional[str] = None,
        input_dir: str = "data/extracted"
    ) -> Dict[str, str]:
        """Predict animal from video frames in a directory.
        
        Analyzes frames extracted from a video and returns the first
        detection that exceeds the confidence threshold.
        
        Args:
            model_path: Optional path to model file
            labels_path: Optional path to labels file
            input_dir: Directory containing extracted video frames
            
        Returns:
            Dictionary with 'animal' and 'match' keys
        """
        try:
            import numpy as np
            from tensorflow.keras.preprocessing import image
            from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
            
            cls._ensure_model_loaded()
            
            result = {'animal': 'Not Detected', 'match': '0%', 'best_frame': None}
            best_confidence = 0.0
            best_frame_path = None
            best_animal = 'Not Detected'
            
            # Walk through directory and predict on each frame
            for dirpath, dirnames, filenames in os.walk(input_dir):
                for filename in filenames:
                    if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                        continue
                        
                    file_path = os.path.join(dirpath, filename)
                    
                    try:
                        # Load and preprocess image
                        img = image.load_img(file_path, target_size=(160, 160))
                        img_array = image.img_to_array(img)
                        img_array = np.expand_dims(img_array, axis=0)
                        img_array = preprocess_input(img_array)
                        
                        # Make prediction
                        pred = cls._model.predict(img_array)
                        class_idx = np.argmax(pred)
                        confidence = np.max(pred) * 100
                        
                        animal = cls._labels[class_idx]
                        logger.debug(f"Frame {filename}: {animal} ({confidence:.2f}%)")
                        
                        # Track the frame with the highest confidence
                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_frame_path = file_path
                            best_animal = animal
                            
                    except Exception as e:
                        logger.warning(f"Failed to process frame {filename}: {e}")
                        continue
            
            result['best_frame'] = best_frame_path
            
            # Use the best (most confident) detection above threshold
            if best_confidence > cls.CONFIDENCE_THRESHOLD:
                result['animal'] = best_animal
                result['match'] = f'{best_confidence:.2f}%'
            
            logger.info(f"Best frame: {best_frame_path} ({best_animal} {best_confidence:.2f}%)")
            return result
            
        except Exception as e:
            logger.error(f"Directory prediction failed for {input_dir}: {e}")
            return {
                'animal': 'Error',
                'match': '0%',
                'best_frame': None
            }