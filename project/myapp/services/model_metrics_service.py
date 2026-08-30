"""Model Metrics Service.

Reads the metrics file written by the model training pipeline
(``backend/ml/model_metrics.json``) and exposes helpers for the admin
"Model Performance" page. Because the training pipeline overwrites this
file on every run, the data shown on the page always reflects the latest
trained model.
"""

import json
import os
import logging
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


class ModelMetricsService:
    """Service for reading and exposing the latest model performance data."""

    DEFAULT_METRICS_PATH = 'backend/ml/model_metrics.json'
    DEFAULT_CONFUSION_CHART = 'backend/ml/confusion_matrix_latest.png'
    DEFAULT_CURVES_CHART = 'backend/ml/training_curves_latest.png'

    @classmethod
    def _base_dir(cls) -> str:
        return str(settings.BASE_DIR)

    @classmethod
    def metrics_path(cls) -> str:
        return os.path.join(cls._base_dir(), cls.DEFAULT_METRICS_PATH)

    @classmethod
    def _chart_static_url(cls, rel_path: Optional[str]) -> Optional[str]:
        """Map an output rel-path (backend/ml/...) to a served static path.

        The chart PNGs are mirrored under ``frontend/static/myapp/images/`` so
        they can be referenced through Django's static filesystem. The value
        returned is relative to ``STATIC_URL`` (e.g. ``myapp/images/x.png``),
        ready to pass to ``{% static %}``. Returns None if the file is missing.
        """
        if not rel_path:
            return None
        # Mirror under the static images dir so the template can render it.
        source = os.path.join(cls._base_dir(), rel_path)
        target_dir = os.path.join(cls._base_dir(), 'frontend/static/myapp/images')
        target = os.path.join(target_dir, os.path.basename(rel_path))
        if os.path.exists(source) and os.path.abspath(source) != os.path.abspath(target):
            try:
                os.makedirs(target_dir, exist_ok=True)
                if not os.path.exists(target) or \
                   os.path.getmtime(source) > os.path.getmtime(target):
                    import shutil
                    shutil.copyfile(source, target)
            except Exception as e:  # pragma: no cover - defensive
                logger.warning(f'Could not mirror chart to static: {e}')
        if os.path.exists(target):
            return os.path.join('myapp/images', os.path.basename(target)).replace('\\', '/')
        return None

    @classmethod
    def load_metrics(cls) -> Optional[dict]:
        """Load the latest metrics JSON.

        Returns:
            A dict of metrics, or None if the file does not exist / is invalid.
        """
        path = cls.metrics_path()
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f'Failed to read model metrics: {e}')
            return None

        # Resolve chart URLs for rendering.
        charts = data.get('charts') or {}
        data['charts'] = {
            'confusion_matrix': cls._chart_static_url(charts.get('confusion_matrix', cls.DEFAULT_CONFUSION_CHART)),
            'training_curves': cls._chart_static_url(charts.get('training_curves', cls.DEFAULT_CURVES_CHART)),
        }
        return data

    @classmethod
    def get_context(cls) -> dict:
        """Build the template context for the model performance page.

        Returns a dict safe to render even when no metrics file exists yet.
        """
        data = cls.load_metrics()
        if data is None:
            return {'available': False}

        metrics = data.get('metrics') or {}
        overall = metrics.get('overall') or {}
        classes = metrics.get('labels') or data.get('classes') or []
        cm = metrics.get('confusion_matrix') or []
        confusion_rows = [
            {'label': classes[i] if i < len(classes) else str(i), 'row': row}
            for i, row in enumerate(cm)
        ]
        return {
            'available': True,
            'generated_at': data.get('generated_at'),
            'model_name': data.get('model_name'),
            'model_file': data.get('model_file'),
            'version': data.get('version'),
            'input_size': data.get('input_size'),
            'num_classes': data.get('num_classes'),
            'classes': classes,
            'train_samples': data.get('train_samples'),
            'val_samples': data.get('val_samples'),
            'epochs': data.get('epochs'),
            'batch_size': data.get('batch_size'),
            'val_split': data.get('val_split'),
            'training_duration_seconds': data.get('training_duration_seconds'),
            'dataset_dir': data.get('dataset_dir'),
            'accuracy': overall.get('accuracy'),
            'macro_precision': overall.get('macro_precision'),
            'macro_recall': overall.get('macro_recall'),
            'macro_f1': overall.get('macro_f1'),
            'samples': overall.get('samples'),
            'per_class': metrics.get('per_class') or [],
            'confusion_matrix': cm,
            'confusion_rows': confusion_rows,
            'final_history': data.get('final_history') or {},
            'confusion_chart': data['charts'].get('confusion_matrix'),
            'curves_chart': data['charts'].get('training_curves'),
        }
