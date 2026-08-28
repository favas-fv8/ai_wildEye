import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

from tensorflow.keras.preprocessing import image
from tensorflow.keras.models import load_model
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
import numpy as np

class Animal_Classifier:
    @staticmethod
    def predict_from_file(model_path="mobilenet_animal_classifier_cpu.h5", labels_path="labels.txt", input_image="test/r01.jpg"):
        # Load model and labels
        model = load_model(model_path)
        with open(labels_path, "r") as f:
            class_labels = [line.strip() for line in f.readlines()]

        # Preprocess and predict
        img_path = input_image
        img = image.load_img(img_path, target_size=(160, 160))
        img_array = image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array = preprocess_input(img_array)

        pred = model.predict(img_array)
        class_idx = np.argmax(pred)
        confidence = np.max(pred) * 100

        print(f"Predicted Animal: {class_labels[class_idx]} ({confidence:.2f}% confidence)")
        # apply confidence threshold to ignore low-confidence outputs
        if confidence > 65:
            result_d = {'animal':class_labels[class_idx],
                        'match':f'{confidence:.2f}%'}
        else:
            result_d = {'animal':'Not Detected','match':'0%'}
        return result_d

    @staticmethod
    def predict_from_dir(model_path="mobilenet_animal_classifier_cpu.h5", labels_path="labels.txt", input_dir="data\\extracted"):
        # Load model and labels
        model = load_model(model_path)
        with open(labels_path, "r") as f:
            class_labels = [line.strip() for line in f.readlines()]


        result_d = {}

        listOfFiles = list()
        result_list = []
        extracted_file_path = input_dir #os.path.join(BASE_DIR, 'data\\extracted')
        for (dirpath, dirnames, filenames) in os.walk(extracted_file_path):
            for file in filenames:
                infile = f'{input_dir}/{file}'

                img_path = infile
                img = image.load_img(img_path, target_size=(160, 160))
                img_array = image.img_to_array(img)
                img_array = np.expand_dims(img_array, axis=0)
                img_array = preprocess_input(img_array)

                pred = model.predict(img_array)
                class_idx = np.argmax(pred)
                confidence = np.max(pred) * 100

                print(f"Predicted Animal: {class_labels[class_idx]} ({confidence:.2f}% confidence)")
                
                if confidence > 65:
                    result_d = {'animal':class_labels[class_idx],
                        'match':f'{confidence:.2f}%'}
                    break

                result_d = {'animal':'Not Detected',
                        'match':f'{0}%'}
                    
                # result_list.append(f'{file} = {result}')
            listOfFiles += [os.path.join(dirpath, file) for file in filenames]
        pos = 0
        

        # Preprocess and predict
        return result_d
