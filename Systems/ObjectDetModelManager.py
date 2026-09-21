from ultralytics import YOLO
import cv2 as cv
from pathlib import Path
from .configHandler import load_config
from collections import Counter
import time

class ObjectDetModelManager:
    SCRIPT_DIR = Path(__file__).resolve().parent
    config = None
    minConf = None
    CONFIG_PATH = "config.txt"
    model = None

    # UPDATED: Pointing to the specific model from yoloeTest
    yolo_model_path = SCRIPT_DIR / "models" / "yoloe-v8l-seg-pf.pt"

    def __init__(self):
        self.config = load_config(self.CONFIG_PATH)
        # Default to 0.15 if not set, matching yoloeTest's open-vocab preference
        self.minConf = float(self.config.get("yolo_min_conf", 0.15))

    def LoadModel(self):
        print(f"Loading model from: {self.yolo_model_path}")
        self.model = YOLO(self.yolo_model_path)

    def detect(self, image):
        try:
            # BENCHMARK: Wall-Clock Start (Technique from yoloeTest)
            start_infer = time.time()

            frame = cv.imread(image)
            
            if frame is not None and frame.size > 0:
                # UPDATED: Use .predict() explicitly with conf threshold
                # verbose=False prevents it from printing the standard YOLO table to stdout, 
                # keeping your console cleaner for the custom print below.
                results = self.model.predict(source=frame, conf=self.minConf, verbose=False)

                # BENCHMARK: Wall-Clock End
                end_infer = time.time()
                total_pipeline_time = (end_infer - start_infer) * 1000

                object_counts = Counter()

                if results:
                    result = results[0]

                    # BENCHMARK: Internal Engine Breakdown (Technique from yoloeTest)
                    # Accessing the internal speed dictionary for accurate profiling
                    speed = result.speed
                    print(f"[Perf] Wall: {total_pipeline_time:.2f}ms | "
                          f"Pre: {speed['preprocess']:.2f}ms | "
                          f"Inference: {speed['inference']:.2f}ms | "
                          f"Post: {speed['postprocess']:.2f}ms")

                    # UPDATED: Robust Name Handling (Technique from yoloeTest)
                    # Safely handle cases where names might not be populated
                    names = result.names
                    
                    for box in result.boxes:
                        class_id = int(box.cls[0])
                        
                        if names:
                            class_name = names[class_id]
                        else:
                            class_name = f"Class {class_id}"
                        
                        # Confidence is already filtered by model.predict(conf=...), 
                        # but accessible here if you need double verification.
                        # conf = float(box.conf[0])
                        
                        object_counts[class_name] += 1

                output = " " + ", ".join(
                    [f"{count} {o}" if count > 1 else o for o, count in object_counts.items()]
                )
                
                if len(object_counts) < 1:
                    return "No objects detected."
                return output
                
        except Exception as e:
            print(f"An unexpected error occurred in the object detection: {e}")
            return "Error during detection."