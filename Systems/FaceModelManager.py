import cv2 as cv
import os
# cuda_bin_path = r"C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v12.9\\bin"
# try:
#     os.add_dll_directory(cuda_bin_path)
# except AttributeError:
#     # os.add_dll_directory is only available in Python 3.8+
#     os.environ['PATH'] = cuda_bin_path + ';' + os.environ['PATH']

import dlib

import face_recognition
import pickle
import os
from pathlib import Path

class FaceModelManager:
    def __init__(self):
        self.detector = None
        self.data = None
    def LoadModel(self):
        # Facial recognition files
        SCRIPT_DIR = Path(__file__).resolve().parent
        encodings_path = SCRIPT_DIR / "models" / "FaceDetection" / "encodings.pickle"
        face_cascade_path = SCRIPT_DIR / "models" / "FaceDetection" / "haarcascade_frontalface_default.xml"
        self.data = pickle.loads(open(encodings_path, "rb").read())
        self.detector = cv.CascadeClassifier()
        self.detector.load(str(face_cascade_path))

    def recognize(self, image):
        if isinstance(image, str):
            img = cv.imread(image)
        else:
            img = image
        gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        rgb = cv.cvtColor(img, cv.COLOR_BGR2RGB)

        # Detect faces in the grayscale image
        rects = self.detector.detectMultiScale(gray, scaleFactor=1.3, 
                                                minNeighbors=6, minSize=(40, 40),
                                                flags=cv.CASCADE_SCALE_IMAGE)
        boxes = [(y, x + w, y + h, x) for (x, y, w, h) in rects]
        
        encodings = face_recognition.face_encodings(rgb, boxes)
        names = []
        tolerance = 0.5
        confidences = []
        currentname = "Unknown"


        for encoding in encodings:
            distances = face_recognition.face_distance(self.data["encodings"], encoding)
            
            matches = []
            for i in distances:
                m = True
                if i > tolerance:
                    m = False
                matches.append(m)
                if m:
                    confidences.append(1-i)
            
            name = "Unknown" 
            if True in matches:
                matchedIdxs = [i for (i, b) in enumerate(matches) if b]
                counts = {}
                for i in matchedIdxs:
                    name = self.data["names"][i]
                    counts[name] = counts.get(name, 0) + 1

                name = max(counts, key=counts.get)

                if currentname != name:
                    currentname = name
            names.append(name)
        startingOutput = "Detected "
        output = startingOutput
        for name in names:
            if name != "Unknown":
                output += f"{name}, "
        if output == startingOutput:
            return "No one was recognized."
        return output 