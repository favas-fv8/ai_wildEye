import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

from tensorflow.keras.preprocessing import image
from tensorflow.keras.models import load_model
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
import numpy as np

# Load model and labels
model = load_model("mobilenet_animal_classifier_cpu.h5")
with open("labels.txt", "r") as f:
    class_labels = [line.strip() for line in f.readlines()]

# Preprocess and predict
img_path = "test/r01.jpg"
img = image.load_img(img_path, target_size=(160, 160))
img_array = image.img_to_array(img)
img_array = np.expand_dims(img_array, axis=0)
img_array = preprocess_input(img_array)

pred = model.predict(img_array)
class_idx = np.argmax(pred)
confidence = np.max(pred) * 100

print(f"Predicted Animal: {class_labels[class_idx]} ({confidence:.2f}% confidence)")
