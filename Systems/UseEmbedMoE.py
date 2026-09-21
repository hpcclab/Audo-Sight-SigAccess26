from setfit import SetFitModel
import os
from pathlib import Path
import numpy as np

# Assuming configHandler is in the same directory
try:
    from .configHandler import load_config
except ImportError:
    # Fallback if running as a standalone script without the package structure
    def load_config(path):
        config = {}
        with open(path, 'r') as f:
            for line in f:
                if "=" in line:
                    key, val = line.strip().split("=", 1)
                    config[key.strip()] = val.strip()
        return config

class MoEClassifier:
    # Path to the JSON files
    CONFIG_PATH = "config.txt"
    config = None
    persist_directory = None
    type = ""
    Threshold = {}
    
    # Model storage
    model = None
    
    # Mapping from Integer ID (SetFit) to String Label (Your System)
    # Based on the training order: 0=Object, 1=Face, 2=OCR
    id2label = {
        0: "object",
        1: "face",
        2: "ocr",
        3: "other"
    }

    def __init__(self):
        SCRIPT_DIR = Path(__file__).resolve().parent
        self.CONFIG_PATH = SCRIPT_DIR / "config.txt"
        
        # Ensure config exists
        if not os.path.exists(self.CONFIG_PATH):
            raise FileNotFoundError(f"Configuration file not found at: {self.CONFIG_PATH}")

        self.config = load_config(self.CONFIG_PATH)
        
        # Load the path for the MoE model folder (e.g., "my-moe-detector")
        self.persist_directory = self.config.get("MoE_embed_path")
        self.persist_directory = SCRIPT_DIR / self.persist_directory
        
        # Load thresholds
        self.Threshold["object"] = float(self.config.get("MoE_Object_Threshold", 0.5))
        self.Threshold["face"] = float(self.config.get("MoE_Face_Threshold", 0.5))
        self.Threshold["ocr"] = float(self.config.get("MoE_OCR_Threshold", 0.5))
        self.Threshold["other"] = float(self.config.get("MoE_Other_Threshold", 0.5))

    def LoadModel(self):
        """
        Loads the SetFit model.
        """
        print(f"Loading SetFit model from: {self.persist_directory}")
        if not os.path.exists(self.persist_directory):
            print(f"WARNING: Model directory does not exist: {self.persist_directory}")
            return

        try:
            # Load the local SetFit model
            self.model = SetFitModel.from_pretrained(str(self.persist_directory))
            print("SetFit Model loaded successfully.")
        except Exception as e:
            print(f"Error loading model: {e}")

    # Returns the chain_name and whether it passed the threshold. tuple: (chainName, Passed, Score)
    def Query(self, text, threshold=0):

        if self.model is None:
            print("Error: Model not loaded. Call LoadEmbeddings() first.")
            return None

        # SetFit returns probabilities for all classes
        # predict_proba returns shape (1, num_classes)
        probs = self.model.predict_proba([text])[0]
        
        # Find the class with the highest probability
        pred_id = np.argmax(probs)
        score = float(probs[pred_id]) # Convert numpy float to python float
        
        # Map ID to string label
        predicted_label = self.id2label.get(int(pred_id), "unknown")

        # Print the prediction
        print(f"Prediction: {predicted_label} (ID: {pred_id}) (Confidence: {score:.4f})")

        # Pass to checker
        return self.PassCheck(predicted_label, score, threshold)

    def PassCheck(self, chainName, KVal, threshold=0):
        """
        chainName: The predicted category (str)
        KVal: The probability score (float, 0.0 - 1.0)
        """

        chainName = chainName.lower()
        
        print(f"Found Category: {chainName} | Confidence: {KVal:.4f}")
        
        if chainName in self.Threshold:
            if threshold != 0:
                KThresh = threshold
            else:
                KThresh = self.Threshold[chainName]
            
            # LOGIC CHANGE: SetFit uses Probability (Higher is Better)
            # Old Chroma used Distance (Lower is Better)
            # Therefore: Passed if Score > Threshold
            passed = KVal > KThresh
            
            return (chainName, passed, KVal)
        else:
            print(f"Warning: No threshold defined for category '{chainName}'")
            # If unknown, usually fail safely
            return (chainName, False, KVal)

# --- Main Execution Block ---
if __name__ == "__main__":
    print("--- Starting SetFit MoE Classifier ---")
    
    # 1. Instantiate
    classifier = MoEClassifier()
    
    # 2. Load
    classifier.LoadModel()
    
    # 3. Test Loop
    print("\nEnter a phrase to test MoE (type 'q' to quit):")
    print(f"Current MoE Thresholds: {classifier.Threshold['object']}, {classifier.Threshold['face']}, {classifier.Threshold['ocr']}")
    
    while True:
        user_input = input("> ")
        if user_input.lower() == 'q':
            break
        
        result = classifier.Query(user_input)
        
        if result:
            category, _, score = result
            
            # Visual formatting
            if category == "object":
                print(f"🚲 RESULT: Object (Prob: {score:.4f})")
                print(">> ACTION: Object")
            elif category == "face":
                print(f"😄 RESULT: Face (Prob: {score:.4f})")
                print(">> ACTION: Face")
            elif category == "ocr":
                print(f"🆒 RESULT: OCR (Prob: {score:.4f})")
                print(">> ACTION: OCR")
            elif category == "other":
                print(f"🎲 RESULT: Other (Prob: {score:.4f})")
                print(">> ACTION: Other")
                
        print("-" * 30)