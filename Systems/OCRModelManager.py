import os
import numpy as np
import cv2 as cv
from threading import Lock

# Force single-thread mode for OpenMP to reduce conflict chance
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

from paddleocr import PaddleOCR

def calculate_iou(box_a, box_b):
    x_a = max(box_a[0], box_b[0])
    y_a = max(box_a[1], box_b[1])
    x_b = min(box_a[2], box_b[2])
    y_b = min(box_a[3], box_b[3])
    inter_area = max(0, x_b - x_a) * max(0, y_b - y_a)
    if inter_area == 0:
        return 0.0
    box_a_area = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    box_b_area = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    iou = inter_area / float(box_a_area + box_b_area - inter_area)
    return iou

def reading_order(boxes):
    centres = np.array([np.mean(b, axis=0) for b in boxes])               
    return np.lexsort((centres[:, 0], centres[:, 1] * 4)).tolist()

class OCRModelManager:
    conf_threshold = 0.6
    min_length = 2
    
    def __init__(self, conf_threshold=0.6, min_length=2):
        self.conf_threshold = conf_threshold
        self.min_length = min_length
        self.lock = Lock()
        self.ocr = None

    @staticmethod
    def _prep(img: np.ndarray) -> np.ndarray:
        """Light contrast boost"""
        img = cv.resize(img, None, fx=1.6, fy=1.6, interpolation=cv.INTER_CUBIC)
        lab = cv.cvtColor(img, cv.COLOR_BGR2LAB)
        l, a, b = cv.split(lab)
        l = cv.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(l)
        merged = cv.merge((l, a, b))
        return np.ascontiguousarray(merged)

    def read_text(self, image: str):
        img = cv.imread(image)
        if img is None:
            return "No text detected."

        img = self._prep(img)

        # CRITICAL FIX: Retry Logic
        with self.lock:
            # Safety check: if model isn't loaded yet
            if self.ocr is None:
                self.LoadModel()

            try:
                # Try running normally
                ocr_res = self.ocr.ocr(img, cls=True)
            except Exception as e:
                # If it crashes (wrong thread), catch it, reload, and retry.
                print(f"Thread Conflict Detected ({e}). Reloading Model on current thread...")
                self.LoadModel() 
                try:
                    ocr_res = self.ocr.ocr(img, cls=True)
                    print("Recovery successful.")
                except Exception as e2:
                    print(f"OCR FAILED FINAL: {e2}")
                    return "Error reading text."

        if not ocr_res or not ocr_res[0]:
            return "No text detected."

        kept = [
            (box, txt.strip())
            for box, (txt, conf) in ocr_res[0]
            if conf >= self.conf_threshold and len(txt) >= self.min_length
        ]
        if not kept:
            return "No text detected."

        order = reading_order([b for b, _ in kept])
        ordered_text = [kept[i][1].replace(".", "") for i in order]
        if not ordered_text:
            return "No text detected."

        OCROut = " ".join(ordered_text)
        return "Text detected. " + OCROut

    def LoadModel(self):
        # Re-initialize the PaddleOCR object
        # This binds it to the CURRENT active thread
        self.ocr = PaddleOCR(
            lang="en",
            gpu=False,
            enable_mkldnn=False, # Keep this False to minimize issues
            use_angle_cls=True,
            use_doc_orientation_classify=True,
            use_doc_unwarping=True,
            use_textline_orientation=True,
            text_detection_model_name="PP-OCRv5_server_det",
            text_recognition_model_name="PP-OCRv5_server_rec",
            show_log=False,
            det_db_box_thresh=0.30,
            det_db_unclip_ratio=2.0,
            rec_image_shape="3,64,640",
            rec_batch_num=8,
        )