import os
import sys

import time
# Get the directory of the current script (e.g., /.../Audosight/Systems)
current_dir = os.path.dirname(os.path.abspath(__file__))

# Move up one level to the project root (e.g., /.../Audosight)
# os.pardir is cross-platform for '..'
project_root = os.path.abspath(os.path.join(current_dir, os.pardir))

# Add the project root to the system path
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from pathlib import Path
from Systems.UseEmbedMoE import MoEClassifier
from Systems.UseUrgencyModel import UrgencyClassifier
from Systems.ModelManager import ModelManager
from Systems.APIModelManager import APIModelManager
from Systems.ObjectDetModelManager import ObjectDetModelManager
from Systems.OCRModelManager import OCRModelManager
from Systems.FaceModelManager import FaceModelManager
from Systems.HybridModelManager import HybridModelManager

class Audosight:
    #### DEBUG CONFIG - ALL SHOULD BE TRUE FOR FINAL
    ProcessLM = True
    Obj_enabled = True
    Face_enabled = True
    OCR_enabled = True
    Classifiers_enabled = True
    DisableDebugAlwaysUrgent = True
    MOEDisableNeverUrgent = True
    FaceDisabled = True

    OnlyObjectDetection = False

    HideDebugOutput = False
    #######################

    MoeClassifier = MoEClassifier()
    UrgencyClassifier = UrgencyClassifier()
    ModelM = ModelManager()
    APIModelM = APIModelManager()
    HybridM = None 
    TextM = OCRModelManager()
    ObjM = ObjectDetModelManager()
    FaceM = FaceModelManager()

    def __init__(self):
        self.HybridM = HybridModelManager(self.ModelM, self.APIModelM)

    def LoadModels(self):
        if (self.Classifiers_enabled):
            self.MoeClassifier.LoadModel()
            self.UrgencyClassifier.LoadModel()
        if (self.ProcessLM):
            self.ModelM.load_models()
        if (self.Obj_enabled):
            self.ObjM.LoadModel()
        if (self.Face_enabled):
            self.FaceM.LoadModel()
        if (self.OCR_enabled):
            self.TextM.LoadModel()

    def Analysis(self, input, image, forcePath="", record_token_times=False):
        if not self.HideDebugOutput:
            print(f"\n[DEBUG] Starting Analysis for: '{input}'")
        else:
            print(f"\nDebug disabled. Starting Analysis for: '{input}'")
        # yield "Processing..."
        # Timers
        object_Time = 0
        ocr_Time = 0
        face_Time = 0
        embeddingUrgency_Time = 0
        embeddingMOE_Time = 0
        LLMRT_Time = 0
        LLMTT_Time = 0
        MLLMRT_Time = 0
        MLLMTT_Time = 0
        MOE_Response_Record = ""
        
        Start_Time = time.time()
        Checkpoint_Time = time.time()

        Route = ""
        full_response_text = ""
        Local_response_text = ""
        Merging_response_text = ""
        Cloud_response_text = ""
        Complete_hybrid_response_text = ""
        estimated_chars_spoken = 0
        Spoken_text = ""
        analysis_data = None
        
        # --- 1. Urgency Classifier ---
        if (self.Classifiers_enabled):
            UrgencyClassData = self.UrgencyClassifier.Query(input)
            embeddingUrgency_Time = time.time() - Checkpoint_Time
        
            if (UrgencyClassData[1] and UrgencyClassData[0] == "urgent"):
                Urgent = True
                Route += "urgent (" + str(UrgencyClassData[0]) + ", " + str(UrgencyClassData[2]) + "), "
            else:
                Urgent = False
                Route += "non-urgent (" + str(UrgencyClassData[0]) + ", " + str(UrgencyClassData[2]) + "), "

            if not self.HideDebugOutput:
                print(f"[DEBUG] Urgency: {Urgent}({UrgencyClassData[0]}, {UrgencyClassData[2]}) (Route: {Route})")
        else:
            Route += "Urgency Classifier Disabled in settings, "
            print("[DEBUG] Urgency Classifier Disabled in settings")

        if (not self.DisableDebugAlwaysUrgent):
            Urgent = True
            Route += "Debug Forced Urgent, "
            print(f"[DEBUG] Debug Forced Urgent")

        # --- 2. MoE Classifier ---
        moe = None
        if (self.Classifiers_enabled):
            Checkpoint_Time = time.time()
            MoeClassData = self.MoeClassifier.Query(input)
            embeddingMOE_Time = time.time() - Checkpoint_Time 
            if (MoeClassData[1]):
                moe = MoeClassData[0]
        else:
            moe = None
            MoeClassData = [None, False]
            print("[DEBUG] MoE Classifier Disabled")

        if not self.HideDebugOutput and moe:
            print(f"[DEBUG] MoE: {moe}")

        if self.OnlyObjectDetection and not (moe is not None and moe == "object"):
            yield "Aborted: Object Detection Only"
            return

        if forcePath is not None and forcePath != "":
            if moe is not None:
                originalmoe = moe
                Route += f"Original MoE: {originalmoe}, "
            elif originalmoe is None:
                Route += f"Original MoE: None, "
            moe = forcePath
            Route += f"Forced MoE: {moe}, "
            if originalmoe is not None and originalmoe != moe:
                Route += f"MoE Mismatched, "
            elif originalmoe is not None and originalmoe == moe:
                Route += f"MoE Matched, "
            elif originalmoe is None:
                Route += f"MoE Mismatched, "
            if not self.HideDebugOutput: print(f"[DEBUG] Debug Forced MoE: {moe}")
        if forcePath == "other":
            moe = None
        Checkpoint_Time = time.time()
        
        # --- 3. Execute Specialized Models ---
        # These models return a single string (not a stream), so we yield it immediately.
        MoEOutput = None # No moe result by default
        if (not moe):
            Route += "MOE-None, "
        elif (moe == "other"):
            Route += f"MOE-Other ({MoeClassData[2]}), "
        elif (moe == "object" and self.Obj_enabled):
            Route += f"MOE-Object ({MoeClassData[2]}), "
            if not self.HideDebugOutput: print(f"[DEBUG] Running Object Detection...")
            if self.Obj_enabled:
                MoEOutput = self.ObjM.detect(image)
            else:
                MoEOutput = "Object Detection Disabled"
            object_Time = time.time() - Checkpoint_Time
        elif (moe == "face" and self.Face_enabled):
            Route += f"MOE-Face ({MoeClassData[2]}), "
            if self.FaceDisabled:
                Route += "Face Recognition Disabled - switched to other, "
            else:
                if not self.HideDebugOutput: print(f"[DEBUG] Running Face Recognition...")
                if self.Face_enabled:
                    MoEOutput = self.FaceM.recognize(image)
                else:
                    MoEOutput = "Face Recognition Disabled"
                face_Time = time.time() - Checkpoint_Time
        elif (moe == "ocr" and self.OCR_enabled):
            Route += f"MOE-OCR ({MoeClassData[2]}), "
            if not self.HideDebugOutput: print(f"[DEBUG] Running OCR...")
            if self.OCR_enabled:
                MoEOutput = self.TextM.read_text(image)
            else:
                MoEOutput = "OCR Disabled"
            ocr_Time = time.time() - Checkpoint_Time
        prompt = input
        Fusion = False
        # If a specialized model ran, yield its output immediately
        # FIXED: Append ". " to ensure TTS treats this as a standalone sentence.
        if MoEOutput:
            MOE_Response_Record = MoEOutput
            if not self.HideDebugOutput: print(f"[DEBUG] MoE Output: {MoEOutput}")
            if Urgent and self.MOEDisableNeverUrgent: # NeverUrgent = True when we want to override the urgency of moe. Make it always slow. MOEDisableNeverUrgent = False when we override.
                text_out = str(MoEOutput) + ". "
                full_response_text += text_out
                yield text_out
            else:
                NewPrompt = f"Use this data about the image to answer the query to the best of your ability. Please include all the image data you can to answer the question. Answer without an introduction or confirmation statement.[Image data: {str(moe)}: {str(MoEOutput)}] [query: {prompt}]"
                LLMStart = time.time()
                LLMResponded = False
                gen = self.ModelM.GenerateText(NewPrompt)
                for chunk in gen:
                    if not LLMResponded:
                        LLMRT_Time = time.time() - LLMStart
                        LLMResponded = True
                    if not isinstance(chunk, dict):
                        chunk = chunk.replace("*"," ")
                        full_response_text += chunk
                    yield chunk
                LLMTT_Time = time.time() - LLMStart
                


            # if "No text detected" in text_out:
            #     yield "... Retrying."

            # yield "... Processing deeper insights. "
            # prompt += f" You can use this information in your response: ({text_out})"
            # moe = None
        
        # --- 4. Execute LLM (Streaming) ---
        # If no specific MoE matched, or if we want to augment the response, we run the LLM.
        if (self.ProcessLM and not moe):
            Checkpoint_Time = time.time()
            
            # Inner helper to track LLM timing while yielding chunks
            def stream_processor(generator):
                nonlocal estimated_chars_spoken, Merging_response_text, analysis_data, prompt
                accumulated = ""
                first_token_time = None
                start_gen = time.time()
                
                # try:
                for chunk in generator:
                    if isinstance(chunk, dict): # Is this a message rather than a chunk of text?
                        if (chunk.get("type") == "merge_signal" or "spoken_chars" in chunk): # Is this a message containing estimated_chars_spoken?
                            estimated_chars_spoken = chunk["spoken_chars"]
                        elif (chunk.get("type") == "analysis_data"):
                            analysis_data = chunk
                        yield chunk
                        continue
                    if (estimated_chars_spoken != 0):
                        Merging_response_text += chunk # We know the merging response has started if we have estimated_chars_spoken.
                    chunk.replace("*"," ")
                    if first_token_time is None:
                        first_token_time = time.time()
                    accumulated += chunk
                    yield chunk
                # except Exception as e:
                #     yield f" [Error in LLM: {e}] "

                nonlocal MLLMTT_Time, MLLMRT_Time
                end_gen = time.time()
                MLLMTT_Time = end_gen - start_gen
                if first_token_time:
                    MLLMRT_Time = first_token_time - start_gen
                return accumulated
            if (Urgent):
                # Use Hybrid Model Manager
                Route += "hybrid-LLM, "
                Fusion = True
                if not self.HideDebugOutput: print(f"[DEBUG] Routing to Hybrid Model Manager...")
                gen = self.HybridM.Generate(prompt, image, not self.HideDebugOutput, record_token_times=record_token_times)
                for chunk in stream_processor(gen):
                    if not isinstance(chunk, dict):
                        full_response_text += chunk
                    yield chunk
            else:
                Route += "cloud-LLM, "
                if not self.HideDebugOutput: print(f"[DEBUG] Routing to Cloud LLM...")
                # Assumes APIModelM.get_completion is a generator
                gen = self.APIModelM.get_completion(prompt, image)
                for chunk in stream_processor(gen):
                    full_response_text += chunk
                    yield chunk

        # --- 5. Finalize Data for Logging ---
        timesData = {
            "object": object_Time,
            "ocr": ocr_Time,
            "face": face_Time,
            "embeddingUrgency": embeddingUrgency_Time,
            "embeddingMOE": embeddingMOE_Time,
            "LLMRT": LLMRT_Time,
            "LLMTT": LLMTT_Time,
            "MLLMRT": MLLMRT_Time,
            "MLLMTT": MLLMTT_Time,
            "MOE_Response": MOE_Response_Record
        }
        
        dataOut = {
            "Request": f"{input}", 
            "Response": f"{full_response_text}", 
            "Times": timesData,
            "Path": f"{Route}"
        }
        if (Fusion):
            dataOut["Fusion_analysis_data"] = analysis_data
        
        
        if not self.HideDebugOutput:
            print(f"[DEBUG] Analysis Complete. Total Time: {time.time() - Start_Time:.2f}s")
            print(f"[DEBUG] Final Route: {Route}")

        # CRITICAL: Yield the dictionary LAST. 
        # app.py checks "if isinstance(item, dict)" to handle this.
        yield dataOut


if __name__ == "__main__":
    AS = Audosight()
    print("Loading Models...")
    AS.LoadModels()
    SCRIPT_DIR = Path(__file__).resolve().parent
    img = str(SCRIPT_DIR.parent / "images" / "test2_3.jpg")
    while True:
        user_input = input("\n> ")
        if user_input.lower() == 'q':
            break
        gen = AS.Analysis(user_input, img, "object")
        for chunk in gen:
            if not isinstance(chunk, dict):
                print(chunk, end="", flush=True)
            else:
                print(str(chunk))




    # prompt = "Describe this image ASAP."
    # print(f"\nPrompt: {prompt}")
    # print("Streaming response from HybridModelManager...")
    
    # for chunk in AS.HybridM.Generate(prompt, img, debug=True):
    #     print(chunk, end="", flush=True)