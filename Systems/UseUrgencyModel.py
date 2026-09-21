import os
from pathlib import Path
import json
import time

# --- NEW: Import SetFit instead of LangChain/Chroma ---
from setfit import SetFitModel

# Assuming configHandler is in the same directory
try:
    from .configHandler import load_config
except ImportError:
    # Fallback if running as a standalone script
    def load_config(path):
        config = {}
        with open(path, 'r') as f:
            for line in f:
                if "=" in line:
                    key, val = line.strip().split("=", 1)
                    config[key.strip()] = val.strip()
        return config

class UrgencyClassifier:
    CONFIG_PATH = "config.txt"
    config = None
    model_path = None
    Threshold = {}
    model = None

    def __init__(self):
        SCRIPT_DIR = Path(__file__).resolve().parent
        self.CONFIG_PATH = SCRIPT_DIR / "config.txt"
        
        # Ensure config exists
        if not os.path.exists(self.CONFIG_PATH):
            raise FileNotFoundError(f"Configuration file not found at: {self.CONFIG_PATH}")

        self.config = load_config(self.CONFIG_PATH)
        
        # Get the directory where setfitUrgent.py saved the model (e.g., "my-urgency-detector")
        relative_path = self.config.get("Urgency_embed_path")
        self.model_path = SCRIPT_DIR / relative_path

        # Load Thresholds
        # Note: SetFit outputs a probability (0.0 to 1.0).
        # We generally only need one threshold for the "Urgent" class (Class 1).
        self.Threshold["urgent"] = float(self.config.get("Urgency_Threshold", 0.5))

    def LoadModel(self):
        """Loads the SetFit classifier from disk."""
        print(f"Loading SetFit model from: {self.model_path}")
        
        if not os.path.exists(self.model_path):
            print(f"CRITICAL ERROR: Model directory does not exist: {self.model_path}")
            print("Did you run setfitUrgent.py to generate the model?")
            return

        try:
            # Load the pre-trained SetFit model
            self.model = SetFitModel.from_pretrained(str(self.model_path))
            print("SetFit Urgency Model loaded successfully.")
        except Exception as e:
            print(f"ERROR: Failed to load SetFit model: {e}")

    def Query(self, text):
        """
        Classifies the text using the loaded model.
        Returns: (Category, Passed_Threshold, Score)
        """
        if not self.model:
            print("Error: Model not loaded. Call LoadModel() first.")
            return None

        # Predict probabilities: Returns [[prob_class_0, prob_class_1]]
        # Class 0 = Non-Urgent, Class 1 = Urgent
        probs = self.model.predict_proba([text])[0]
        
        non_urgent_score = float(probs[0])
        urgent_score = float(probs[1])

        print(f"DEBUG: Scores -> Non-Urgent: {non_urgent_score:.4f} | Urgent: {urgent_score:.4f}")

        # LOGIC: If urgency probability exceeds threshold, it is Urgent.
        threshold = self.Threshold["urgent"]

        if urgent_score >= threshold:
            # It is Urgent
            return ("urgent", True, urgent_score)
        else:
            # It is Non-Urgent
            # We return "nonurgent" and True (meaning it successfully matched as non-urgent)
            # or you can return False if you only want to "Pass" on urgency.
            # Here we follow the pattern: Category detected, Score used.
            return ("nonurgent", True, urgent_score)

# --- Main Execution Block ---
if __name__ == "__main__":
    print("--- Starting SetFit Urgency Classifier ---")
    
    # 1. Instantiate
    classifier = UrgencyClassifier()
    
    # 2. Load
    classifier.LoadModel()
    
    # 3. Test Loop
    print("\nEnter a phrase to test urgency (type 'q' to quit):")
    print(f"Current Urgency Threshold: {classifier.Threshold['urgent']}")
    
    while True:
        user_input = input("> ")
        if user_input.lower() == 'q':
            break
        
        result = classifier.Query(user_input)
        
        if result:
            category, _, score = result
            
            # Visual formatting
            if category == "urgent":
                print(f"🔴 RESULT: URGENT (Prob: {score:.4f})")
                print(">> ACTION: Trigger Immediate Response")
            else:
                print(f"🟢 RESULT: Non-Urgent (Urgency Prob: {score:.4f})")
                print(">> ACTION: Normal Queue")
                
        print("-" * 30)