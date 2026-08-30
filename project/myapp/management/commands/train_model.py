"""Train and evaluate the Ai-WildEye animal classification model.

This management command is the training pipeline. It:

1. Reads a labeled image dataset (either a pre-split ``train/`` + ``val/``
   layout, or a single root of class folders with an automatic split).
2. Builds and fine-tunes a MobileNetV2 classifier.
3. Evaluates the model on the validation set.
4. Computes the confusion matrix plus precision / recall / F1 / accuracy.
5. Generates a confusion-matrix chart and training curves (PNG).
6. Writes a machine-readable metrics file (``backend/ml/model_metrics.json``)
   that the admin "Model Performance" page reads and renders.

Because every run writes a fresh metrics file (with a new timestamp/version
and the full confusion matrix), the admin dashboard data automatically
updates whenever a new model is trained.

Two dataset layouts are supported:

* Pre-split (recommended)::
      <dataset>/train/<class>/...    <dataset>/val/<class>/...
* Single root (auto-split)::
      <dataset>/<class>/...

The class label order is taken from the sorted set of class folder names.

Usage:
    python manage.py train_model [--epochs 5] [--batch-size 16]
                                 [--val-split 0.2] [--dataset ../ml_code/Animal]
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

import numpy as np

from myapp.config import Config


# Expected class sub-folder names relative to the dataset root.
DEFAULT_DATASET = '../ml_code/Animal'

# Output locations (relative to BASE_DIR).
DEFAULT_OUTPUTS = {
    'model': Config.ML_MODEL_PATH,
    'labels': Config.ML_LABELS_PATH,
    'metrics': 'backend/ml/model_metrics.json',
    'confusion_chart': 'backend/ml/confusion_matrix_latest.png',
    'curves_chart': 'backend/ml/training_curves_latest.png',
}

# Image input size used by MobileNetV2 (must match MLService / Config).
INPUT_SIZE = Config.ML_INPUT_SIZE

# File extensions treated as images.
IMAGE_EXTS = ('.jpg', '.jpeg', '.png')

# Seed for reproducible train/validation splitting in the single-root layout.
SPLIT_SEED = 1337


def compute_classification_metrics(y_true, y_pred, labels):
    """Compute accuracy and per-class precision/recall/F1 from numpy arrays.

    Args:
        y_true: 1D numpy array of true class indices.
        y_pred: 1D numpy array of predicted class indices.
        labels: List of class names aligned to index order.

    Returns:
        dict with 'overall' and 'per_class' metric structures plus the
        confusion matrix as a 2D list of ints.
    """
    n = len(labels)
    y_true = np.asarray(y_true, dtype=np.int64)
    y_pred = np.asarray(y_pred, dtype=np.int64)

    # Confusion matrix.
    cm = np.zeros((n, n), dtype=np.int64)
    for t, p in zip(y_true, y_pred):
        if 0 <= t < n and 0 <= p < n:
            cm[t, p] += 1

    # Overall accuracy.
    total = int(cm.sum())
    correct = int(np.trace(cm))
    accuracy = float(correct / total) if total > 0 else 0.0

    per_class = []
    for i, name in enumerate(labels):
        tp = int(cm[i, i])
        fp = int(cm[:, i].sum()) - tp
        fn = int(cm[i, :].sum()) - tp
        tn = total - tp - fp - fn

        precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        per_class.append({
            'label': name,
            'tp': tp,
            'fp': fp,
            'fn': fn,
            'tn': tn,
            'precision': round(precision, 4),
            'recall': round(recall, 4),
            'f1_score': round(f1, 4),
            'support': int(tp + fn),
        })

    # Weighted / macro averages.
    macro_precision = float(np.mean([c['precision'] for c in per_class])) if per_class else 0.0
    macro_recall = float(np.mean([c['recall'] for c in per_class])) if per_class else 0.0
    macro_f1 = float(np.mean([c['f1_score'] for c in per_class])) if per_class else 0.0

    overall = {
        'accuracy': round(accuracy, 4),
        'macro_precision': round(macro_precision, 4),
        'macro_recall': round(macro_recall, 4),
        'macro_f1': round(macro_f1, 4),
        'samples': total,
    }

    return {
        'labels': list(labels),
        'overall': overall,
        'per_class': per_class,
        'confusion_matrix': cm.astype(int).tolist(),
    }


def render_confusion_chart(cm, labels, output_path):
    """Render the confusion matrix as a PNG heat-map."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    cm = np.asarray(cm, dtype=np.int64)

    fig, ax = plt.subplots(figsize=(max(6, len(labels) * 0.9),
                                    max(6, len(labels) * 0.9)))
    im = ax.imshow(cm, interpolation='nearest', cmap='Blues')
    ax.figure.colorbar(im, ax=ax)

    tick_marks = np.arange(len(labels))
    ax.set_xticks(tick_marks)
    ax.set_yticks(tick_marks)
    ax.set_xticklabels(labels, rotation=45, ha='right')
    ax.set_yticklabels(labels)
    ax.set_xlabel('Predicted label')
    ax.set_ylabel('True label')
    ax.set_title('Confusion Matrix')

    thresh = cm.max() / 2.0 if cm.max() else 0
    for i in range(len(labels)):
        for j in range(len(labels)):
            color = 'white' if cm[i, j] > thresh else 'black'
            ax.text(j, i, str(int(cm[i, j])),
                    ha='center', va='center', color=color)
    fig.tight_layout()
    fig.savefig(output_path, dpi=120)
    plt.close(fig)


def render_curves(history, output_path):
    """Render training/validation accuracy & loss curves as a PNG."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    epochs = range(1, len(history.get('accuracy', [])) + 1)

    fig, axes = plt.subplots(2, 1, figsize=(8, 9))

    if 'accuracy' in history and len(epochs):
        axes[0].plot(epochs, history['accuracy'], 'b-o', label='Training accuracy')
        if 'val_accuracy' in history and len(history['val_accuracy']) == len(epochs):
            axes[0].plot(epochs, history['val_accuracy'], 'r-o', label='Validation accuracy')
        axes[0].set_title('Accuracy over epochs')
        axes[0].set_xlabel('Epoch')
        axes[0].set_ylabel('Accuracy')
        axes[0].legend()
        axes[0].grid(True)

    if 'loss' in history and len(epochs):
        axes[1].plot(epochs, history['loss'], 'b-o', label='Training loss')
        if 'val_loss' in history and len(history['val_loss']) == len(epochs):
            axes[1].plot(epochs, history['val_loss'], 'r-o', label='Validation loss')
        axes[1].set_title('Loss over epochs')
        axes[1].set_xlabel('Epoch')
        axes[1].set_ylabel('Loss')
        axes[1].legend()
        axes[1].grid(True)

    fig.tight_layout()
    fig.savefig(output_path, dpi=120)
    plt.close(fig)


class Command(BaseCommand):
    help = 'Train and evaluate the Ai-WildEye animal classifier and write model metrics.'

    def add_arguments(self, parser):
        parser.add_argument('--epochs', type=int, default=5,
                            help='Number of training epochs (default: 5).')
        parser.add_argument('--batch-size', type=int, default=16,
                            help='Batch size (default: 16).')
        parser.add_argument('--val-split', type=float, default=0.2,
                            help='Fraction of data held out for validation (default: 0.2).')
        parser.add_argument('--dataset', default=DEFAULT_DATASET,
                            help='Path to the labeled dataset root (default: ../ml_code/Animal).')

    def handle(self, *args, **options):
        base_dir = Path(settings.BASE_DIR)
        dataset_path = base_dir / options['dataset']
        epochs = options['epochs']
        batch_size = options['batch_size']
        val_split = options['val_split']

        if not dataset_path.exists():
            raise CommandError(
                f'Dataset directory not found: {dataset_path}\n'
                'Place labeled images under <dataset>/train/<class>/ and '
                '<dataset>/val/<class>, or <dataset>/<class> for auto-split.'
            )

        # Deferred imports keep the web server (which doesn't run training)
        # from paying the TensorFlow import cost every request.
        import tensorflow as tf
        from tensorflow.keras import layers, models, optimizers
        from tensorflow.keras.applications import MobileNetV2
        from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
        from tensorflow.keras.preprocessing import image_dataset_from_directory

        def _class_dirs(root):
            return sorted(
                d.name for d in Path(root).iterdir()
                if d.is_dir() and list(d.glob('*'))
            )

        def _count_images(root):
            return sum(
                1 for p in Path(root).rglob('*')
                if p.is_file() and p.suffix.lower() in IMAGE_EXTS
            )

        def _make_dataset(root, shuffle, subset=None):
            """Build a memory-efficient streaming dataset.

            Instead of loading every image into RAM at once (which exhausted
            memory on the full dataset), images are read and preprocessed in
            small batches from disk on the fly.
            """
            kwargs = dict(
                directory=root,
                labels='inferred',
                label_mode='categorical',
                class_names=labels,
                image_size=INPUT_SIZE,
                batch_size=batch_size,
                shuffle=shuffle,
            )
            if subset is not None:
                kwargs.update(
                    validation_split=val_split,
                    subset=subset,
                    seed=SPLIT_SEED,
                )
            ds = image_dataset_from_directory(**kwargs)
            return ds.map(
                lambda x, y: (preprocess_input(x), y),
                num_parallel_calls=tf.data.AUTOTUNE,
            )

        # --- Detect dataset layout -------------------------------------------
        train_dir = dataset_path / 'train'
        val_dir = dataset_path / 'val'
        pre_split = train_dir.is_dir() and val_dir.is_dir()

        if pre_split:
            labels = _class_dirs(train_dir)
            if len(labels) < 2:
                raise CommandError(
                    f'Need at least 2 labeled classes under {train_dir}, found: {labels}'
                )
            self.stdout.write(
                f'Pre-split dataset detected. {len(labels)} classes: {labels}'
            )
            train_ds = _make_dataset(str(train_dir), shuffle=True)
            val_ds = _make_dataset(str(val_dir), shuffle=False)
            train_samples = _count_images(train_dir)
            val_samples = _count_images(val_dir)
        else:
            # Single-root layout: everything is in one set, auto-split.
            labels = _class_dirs(dataset_path)
            if len(labels) < 2:
                raise CommandError(
                    f'Need at least 2 labeled classes in {dataset_path}, found: {labels}'
                )
            self.stdout.write(f'Found {len(labels)} classes: {labels}')
            train_ds = _make_dataset(
                str(dataset_path), shuffle=True, subset='training'
            )
            val_ds = _make_dataset(
                str(dataset_path), shuffle=False, subset='validation'
            )
            total_images = _count_images(dataset_path)
            train_samples = int(total_images * (1 - val_split))
            val_samples = int(total_images * val_split)

        if train_samples == 0 or val_samples == 0:
            raise CommandError('No images found in the dataset.')

        self.stdout.write(
            f'Train: {train_samples} samples, Val: {val_samples} samples'
        )

        # --- Build model (fine-tune MobileNetV2) ----------------------------
        base_model = MobileNetV2(
            weights='imagenet', include_top=False, input_shape=(*INPUT_SIZE, 3)
        )
        base_model.trainable = False

        model = models.Sequential([
            base_model,
            layers.GlobalAveragePooling2D(),
            layers.Dropout(0.2),
            layers.Dense(len(labels), activation='softmax'),
        ])

        model.compile(
            optimizer=optimizers.Adam(learning_rate=1e-3),
            loss='categorical_crossentropy',
            metrics=['accuracy'],
        )

        # --- Train ----------------------------------------------------------
        start = time.time()
        history = model.fit(
            train_ds,
            validation_data=val_ds,
            epochs=epochs,
            verbose=1,
        ).history
        training_duration = round(time.time() - start, 2)

        # --- Evaluate (batched, memory-efficient) -----------------------------
        y_true = np.concatenate([
            np.argmax(y.numpy(), axis=1) for _x, y in val_ds
        ])
        y_pred = np.argmax(model.predict(val_ds, verbose=0), axis=1)

        metrics = compute_classification_metrics(y_true, y_pred, labels)

        # --- Save model + labels ---------------------------------------------
        model_path = base_dir / Config.ML_MODEL_PATH
        model_path.parent.mkdir(parents=True, exist_ok=True)
        model.save(str(model_path))

        labels_path = base_dir / Config.ML_LABELS_PATH
        with open(labels_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(labels))

        # --- Render charts -----------------------------------------------------
        chart_out = base_dir / DEFAULT_OUTPUTS['confusion_chart']
        chart_out.parent.mkdir(parents=True, exist_ok=True)
        render_confusion_chart(
            metrics['confusion_matrix'], labels, str(chart_out)
        )
        curves_chart = base_dir / DEFAULT_OUTPUTS['curves_chart']
        render_curves(history, str(curves_chart))

        # --- Write metrics JSON --------------------------------------------------
        metrics_payload = {
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'model_name': 'MobileNetV2 (fine-tuned)',
            'model_file': Config.ML_MODEL_PATH,
            'version': time.strftime('%Y%m%d-%H%M%S'),
            'input_size': list(INPUT_SIZE),
            'num_classes': len(labels),
            'classes': labels,
            'dataset_dir': str(dataset_path),
            'train_samples': int(train_samples),
            'val_samples': int(val_samples),
            'epochs': epochs,
            'batch_size': batch_size,
            'val_split': val_split,
            'training_duration_seconds': training_duration,
            'metrics': metrics,
            'final_history': {
                'accuracy': [float(x) for x in history.get('accuracy', [])],
                'val_accuracy': [float(x) for x in history.get('val_accuracy', [])],
                'loss': [float(x) for x in history.get('loss', [])],
                'val_loss': [float(x) for x in history.get('val_loss', [])],
            },
            'charts': {
                'confusion_matrix': DEFAULT_OUTPUTS['confusion_chart'],
                'training_curves': DEFAULT_OUTPUTS['curves_chart'],
            },
        }

        metrics_path = base_dir / DEFAULT_OUTPUTS['metrics']
        with open(metrics_path, 'w', encoding='utf-8') as f:
            json.dump(metrics_payload, f, indent=2)

        self.stdout.write(self.style.SUCCESS(
            f'Done. Model saved to {model_path}\n'
            f'Metrics written to {metrics_path}\n'
            f'Accuracy: {metrics["overall"]["accuracy"]:.4f} '
            f'Macro F1: {metrics["overall"]["macro_f1"]:.4f}'
        ))
