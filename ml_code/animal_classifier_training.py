
import os
import tensorflow as tf
import numpy as np

# --- Force TensorFlow to use CPU only ---
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

from tensorflow.keras import layers, models
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

# Parameters
IMG_SIZE = (160, 160)
BATCH_SIZE = 32
EPOCHS = 10

# Dataset paths
train_dir = "Animal/train"
val_dir = "Animal/val"

# Data generators (with augmentation)
train_datagen = ImageDataGenerator(
    preprocessing_function=preprocess_input,
    rotation_range=20,
    zoom_range=0.2,
    horizontal_flip=True,
)

val_datagen = ImageDataGenerator(preprocessing_function=preprocess_input)

train_data = train_datagen.flow_from_directory(
    train_dir,
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode='categorical'
)

val_data = val_datagen.flow_from_directory(
    val_dir,
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode='categorical',
    shuffle=False
)

# Save labels
labels = list(train_data.class_indices.keys())
with open("labels.txt", "w") as f:
    for label in labels:
        f.write(label + "\n")
print(f"Labels saved: {labels}")

# Load MobileNetV2 (pretrained)
base_model = MobileNetV2(
    input_shape=(*IMG_SIZE, 3),
    include_top=False,
    weights='imagenet'
)
base_model.trainable = False

# Build classifier
model = models.Sequential([
    base_model,
    layers.GlobalAveragePooling2D(),
    layers.Dropout(0.3),
    layers.Dense(train_data.num_classes, activation='softmax')
])

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.0001),
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

# Train
history = model.fit(
    train_data,
    validation_data=val_data,
    epochs=EPOCHS
)

# Evaluate and compute detailed metrics on validation data
val_data.reset()
y_prob = model.predict(val_data, verbose=1)
y_pred = np.argmax(y_prob, axis=1)
y_true = val_data.classes

conf_matrix = tf.math.confusion_matrix(
    labels=y_true,
    predictions=y_pred,
    num_classes=train_data.num_classes
).numpy()

total = np.sum(conf_matrix)
accuracy = np.trace(conf_matrix) / total if total else 0.0

tp = np.diag(conf_matrix)
fp = np.sum(conf_matrix, axis=0) - tp
fn = np.sum(conf_matrix, axis=1) - tp
tn = total - (tp + fp + fn)

precision_per_class = np.divide(tp, tp + fp, out=np.zeros_like(tp, dtype=float), where=(tp + fp) != 0)
recall_per_class = np.divide(tp, tp + fn, out=np.zeros_like(tp, dtype=float), where=(tp + fn) != 0)
f1_per_class = np.divide(
    2 * precision_per_class * recall_per_class,
    precision_per_class + recall_per_class,
    out=np.zeros_like(precision_per_class, dtype=float),
    where=(precision_per_class + recall_per_class) != 0
)

macro_precision = np.mean(precision_per_class)
macro_recall = np.mean(recall_per_class)
macro_f1 = np.mean(f1_per_class)

print("\n===== Validation Metrics =====")
print(f"Accuracy: {accuracy:.4f}")
print(f"Macro Precision: {macro_precision:.4f}")
print(f"Macro Recall: {macro_recall:.4f}")
print(f"Macro F1 Score: {macro_f1:.4f}")
print("\nConfusion Matrix:")
print(conf_matrix)

metrics_path = "metrics_report.txt"
with open(metrics_path, "w") as f:
    f.write("===== Validation Metrics =====\n")
    f.write(f"Accuracy: {accuracy:.6f}\n")
    f.write(f"Macro Precision: {macro_precision:.6f}\n")
    f.write(f"Macro Recall: {macro_recall:.6f}\n")
    f.write(f"Macro F1 Score: {macro_f1:.6f}\n\n")
    f.write("Confusion Matrix:\n")
    np.savetxt(f, conf_matrix, fmt="%d")
    f.write("\n\nPer-Class Metrics:\n")
    f.write("Class\tTP\tTN\tFP\tFN\tPrecision\tRecall\tF1\n")
    for i, label in enumerate(labels):
        f.write(
            f"{label}\t{int(tp[i])}\t{int(tn[i])}\t{int(fp[i])}\t{int(fn[i])}\t"
            f"{precision_per_class[i]:.6f}\t{recall_per_class[i]:.6f}\t{f1_per_class[i]:.6f}\n"
        )
print(f"Detailed metrics saved to '{metrics_path}'")

# Save model
model.save("mobilenet_animal_classifier_cpu.h5")
print(" Training complete! Model saved as 'mobilenet_animal_classifier_cpu.h5'")
