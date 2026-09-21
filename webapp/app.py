from flask import Flask, render_template, request, Response, redirect, url_for, session, flash, jsonify, stream_with_context
import os
import requests
import time
from gtts import gTTS
from io import BytesIO
from pathlib import Path
import base64
import sys
import uuid
import json
import re

# --- PATH SETUP ---
sys.path.append(str(Path(__file__).parent.parent))
from Systems.configHandler import load_config, save_config_setting
from Systems.DataHandler import DataHandler

# Import Real Systems
try:
    from Systems.AudoSight import Audosight
    from Systems.APIModelManager import APIModelManager
    print("Real Systems Loaded")
except ImportError:
    print("Could not load real systems. Check paths.")
    class APIModelManager(): pass
    class Audosight(): pass


app = Flask(__name__)
SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR.parent / "Systems" / "config.txt"
SENSITIVE_CONFIG_PATH = SCRIPT_DIR.parent / "Systems" / "configSensitive.txt"
DYNAMIC_CONFIG = SCRIPT_DIR / "configDynamic.txt"

config = load_config(CONFIG_PATH)
configS = load_config(SENSITIVE_CONFIG_PATH)
configDynamic = load_config(DYNAMIC_CONFIG)

# Initialize Managers
APIMM = APIModelManager()
AS = Audosight()
try:
    AS.LoadModels()
except:
    pass

# Global dictionary to hold DataHandler objects in memory
DataHandlers = {}

# I know these seem out of order, but we swapped the order of the tests so the airport is after the restaurant.
TEST_DATA = [
    {
        "images": ["test3_1.jpg", "test3_2.jpg", "test3_3.jpg"],
        "PromptsToUser": ["In this scene, you have just arrived at a fast food restaurant.", "You have walked to the menu to pick something to order.", "Now you are at the counter andready to pay for your food.", "End of simulation"],
        "Redirect": "https://unt.az1.qualtrics.com/jfe/form/SV_0JQzTOdLGKlHpRk"
    },
    {
        "images": ["test4_1.jpg", "test4_2.jpg", "test4_3.jpg"],
        "PromptsToUser": ["In this scene, you have just arrived at a fast food restaurant.", "You have walked to the menu to pick something to order.", "Now you are at the counter andready to pay for your food.", "End of simulation"],
        "Redirect": "https://unt.az1.qualtrics.com/jfe/form/SV_8HxmnDKLCmF9p2K"
    },
    {
        "images": ["test1_1.jpg", "test1_2.jpg", "test1_3.jpg"],
        "PromptsToUser": ["In this scene, you have just arrived at the airport. You are trying to find your traveling companion, Dr. Amini, and catch your flight on time. You could miss your flight, so ask what feels natural in an urgent situation.", "You have joined Dr. Amini and are walking down a hall looking for your gate, H190.", "You have sat down at the gate and now it's time to board, so quickly find your things. You turned around toward the chair next to you.", "End of simulation"],
        "Redirect": "https://unt.az1.qualtrics.com/jfe/form/SV_5jBc7Namtk4SsV8"
    },
    {
        "images": ["test2_1.jpg", "test2_2.jpg", "test2_3.jpg"],
        "PromptsToUser": ["In this scene, you have just arrived at the airport. You are trying to find your traveling companion, Dr. Amini, and catch your flight on time. You could miss your flight, so ask what feels natural in an urgent situation.", "You have joined Dr. Amini and are walking down a hall looking for your gate, E25.", "You have sat down at the gate and now it's time to board, so quickly find your things. You turned around toward the chair next to you.", "End of simulation"],
        "Redirect": "https://unt.az1.qualtrics.com/jfe/form/SV_3b10qqGV1gIUhzo"
    }
]

def GetAndUpdateUserSeq():
    NextUserSequence = int(configDynamic["NextUserSequence"])
    if NextUserSequence > 3:
        NextUserSequence = NextUserSequence % 4
    UserSeq = NextUserSequence
    NextUserSequence += 1
    if NextUserSequence > 3:
        NextUserSequence = NextUserSequence % 4
    save_config_setting("NextUserSequence", NextUserSequence, DYNAMIC_CONFIG)
    return UserSeq

def getImagePath():
    scenario = session["TestSeq"][(session["test"] - 1)]
    imgNum = session["img"] - 1
    return str(SCRIPT_DIR.parent / "images" / f"{TEST_DATA[scenario]['images'][imgNum]}")

app.secret_key = configS.get("FlaskKey")

def getIPAddress() -> str:
    proxy_ip = request.remote_addr
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if (client_ip):
        return client_ip
    if proxy_ip:
        return proxy_ip
    return "IP_Unknown"

# --- TTS UTILS ---
def generate_tts_base64(text):
    if not text.strip():
        return None
    try:
        fp = BytesIO()
        tts = gTTS(text=text, lang='en', slow=False)
        tts.write_to_fp(fp)
        audio_content = fp.getvalue()
        return base64.b64encode(audio_content).decode('utf-8')
    except Exception as e:
        print(f"TTS Error: {e}")
        return None

# --- ROUTES ---

@app.route('/')
def index():
    return redirect(url_for('testing'))

@app.route('/testing', methods=['GET', 'POST'])
def testing():
    test = request.args.get('test')
    if (test):
        test = int(test)
    else:
        test = 1
    
    if "OneOurs" not in session or "UserID" not in session:
        session["UserID"] = str(uuid.uuid4())[:8] 
        seqVal = int(GetAndUpdateUserSeq())
        
        if seqVal == 0:
            session["OneOurs"] = True; session["InOrder"] = True; session["SystemSeq"] = [0, 1, 0, 1]; session["TestSeq"] = [0, 1, 2, 3]
        elif seqVal == 1:
            session["OneOurs"] = False; session["InOrder"] = True; session["SystemSeq"] = [1, 0, 1, 0]; session["TestSeq"] = [0, 1, 2, 3]
        elif seqVal == 2:
            session["OneOurs"] = True; session["InOrder"] = False; session["SystemSeq"] = [0, 1, 0, 1]; session["TestSeq"] = [1, 0, 3, 2]
        elif seqVal == 3:
            session["OneOurs"] = False; session["InOrder"] = False; session["SystemSeq"] = [1, 0, 1, 0]; session["TestSeq"] = [1, 0, 3, 2]

        session["DataHandlerID"] = session["UserID"]
        DataHandlers[session["DataHandlerID"]] = DataHandler(IPAddress=getIPAddress(), user_id=session["UserID"])

    if session.get("DataHandlerID") not in DataHandlers:
        DataHandlers[session["DataHandlerID"]] = DataHandler(IPAddress=getIPAddress(), user_id=session.get("UserID", "recovered"))

    DH = DataHandlers[session["DataHandlerID"]]
    current_test_idx = test - 1
    if current_test_idx < len(session["SystemSeq"]):
        system_type = session["SystemSeq"][current_test_idx]
        sys_name = "Audosight" if system_type == 0 else "Gemma-API"
        DH.start_new_version(run_id="MainExperiment", version_id=f"TestScenario_{test}", system_name=sys_name)
        DH.export_json()

    session["test"] = test
    session["img"] = 1
    session["NumQuestions"] = 0
    

    try:
        current_scenario_idx = session["TestSeq"][test - 1]
        initial_prompt = TEST_DATA[current_scenario_idx]["PromptsToUser"][0]
        initial_audio = generate_tts_base64(initial_prompt)
    except Exception as e:
        print(f"Error generating initial prompt: {e}")
        initial_prompt = "Welcome. Please describe what you see."
        initial_audio = None

    # Pass these to the template
    return render_template('index.html', initial_prompt=initial_prompt, initial_audio=initial_audio) 

@app.route('/handle_next', methods=['POST'])
def handle_next():
    # if session.get("NumQuestions", 0) < 2:
    #     return jsonify({'error': "You haven't sent enough queries yet."}), 400
    try:
        current_sequence = session.get("TestSeq")
        sequence_index = int(session.get("test")) - 1
        image_index = session.get("img") - 1                

        if current_sequence is None or sequence_index >= len(current_sequence):
            session["img"] = 0; session["test"] = 0
            return jsonify({'error': 'Session error'}), 400

        current_block_index = current_sequence[sequence_index]
        
        if image_index + 1 < len(TEST_DATA[current_block_index]["images"]):
            next_image_index = image_index + 1
            session["img"] = next_image_index + 1
            next_block_index = current_block_index
        else:
            session["NumQuestions"] = 0
            redir = TEST_DATA[session["test"] - 1]["Redirect"]
            return jsonify({'redirect_url': redir})

        session["NumQuestions"] = 0
        next_data_block = TEST_DATA[next_block_index]
        next_image = next_data_block["images"][next_image_index]
        next_prompt = next_data_block["PromptsToUser"][next_image_index] 
        
        # --- NEW LOGIC: Generate Audio for the Next Prompt ---
        next_audio = generate_tts_base64(next_prompt)

        response_data = {
            'next_image': next_image,
            'next_prompt': next_prompt,
            'next_audio': next_audio, # Send audio to frontend
            'status': f'Showing image {next_image_index + 1} of test block {next_block_index + 1}.'
        }
        return jsonify(response_data)
    except KeyError as e:
        return jsonify({'error': f'Session error: {e}'}), 400

# --- CORE STREAMING LOGIC ---

@app.route('/process_input', methods=['POST'])
def process_input():
    start_time = time.time()
    data = request.json
    UserPrompt = data.get('prompt')
    
    # Session / Logic setup
    SystemSequence = session.get("SystemSeq")
    CurrTest = session.get('test') - 1
    imgPath = getImagePath()
    is_audosight = (SystemSequence[CurrTest] == 0)
    
    # Increase interaction count
    if session.get("NumQuestions") is not None:
        session["NumQuestions"] += 1
    else:
        session["NumQuestions"] = 1

    def generate_stream():
        nonlocal UserPrompt, imgPath, is_audosight, start_time

        # Select Generator source
        if is_audosight:
            generator = AS.Analysis(UserPrompt, imgPath)
        else:
            generator = APIMM.get_completion(UserPrompt, imgPath)

        buffer = ""
        full_response_text = ""
        log_data = None
        first_token_time = None
        
        # FIXED: Removed \s+ to allow splitting immediately on punctuation.
        sentence_end_regex = re.compile(r'(?<=[.!?])')

        # try:
        for item in generator:
            if first_token_time is None:
                first_token_time = time.time() - start_time

            if isinstance(item, dict):
                # Check for merge signal from HybridModelManager
                if item.get("type") == "merge_signal":
                    spoken_chars = item.get("spoken_chars", 0)
                    
                    # Truncate full_response_text to what was spoken
                    full_response_text = full_response_text[:spoken_chars]
                    
                    # Clear the TTS buffer so we don't speak pending text that might be replaced
                    buffer = ""
                    
                    # Send merge event to frontend
                    yield f"data: {json.dumps({'type': 'merge', 'payload': {'spoken_chars': spoken_chars}})}\n\n"
                    continue

                # Otherwise, this is the final log data from Audosight
                log_data = item
                continue

            # It is text chunk
            chunk = str(item)
            chunk.replace("*","")
            full_response_text += chunk
            
            # 1. Send text to Frontend immediately
            yield f"data: {json.dumps({'type': 'text', 'payload': chunk})}\n\n"

            # 2. Buffer for TTS
            buffer += chunk
            parts = sentence_end_regex.split(buffer)
            
            if len(parts) >= 1:
                # parts[:-1] are complete sentences
                # parts[-1] is the incomplete tail
                complete_sentences = parts[:-1]
                buffer = parts[-1]
                
                for sentence in complete_sentences:
                    # Strip whitespace to prevent gTTS issues with leading spaces
                    clean_sent = sentence.strip()
                    if clean_sent:
                        audio_b64 = generate_tts_base64(clean_sent)
                        if audio_b64:
                            yield f"data: {json.dumps({'type': 'audio', 'payload': audio_b64})}\n\n"
        
        # Process remaining buffer
        if buffer.strip():
            audio_b64 = generate_tts_base64(buffer.strip())
            if audio_b64:
                yield f"data: {json.dumps({'type': 'audio', 'payload': audio_b64})}\n\n"

        # --- LOGGING ---
        # If APIMM was used, we need to construct log_data manually as it doesn't return a dict
        if not log_data:
            log_data = {
                "Request": UserPrompt,
                "Response": full_response_text,
                "Path": "API-GPT",
                "Times": {
                    "Total": time.time() - start_time,
                    "FirstToken": first_token_time
                }
            }
        else:
            # Add server overhead time to Audosight data
            log_data["TotalServerTime"] = time.time() - start_time

        if session.get("DataHandlerID") not in DataHandlers:
            DataHandlers[session["DataHandlerID"]] = DataHandler(IPAddress=getIPAddress(), user_id=session.get("UserID", "recovered"))
        if session.get("DataHandlerID") in DataHandlers:
            DH = DataHandlers[session["DataHandlerID"]]
            DH.add_query(
                run_id="MainExperiment",
                version_id=f"TestScenario_{session['test']}",
                scene_number=session['img'],
                query_data=log_data
            )
            DH.export_json()

        
    return Response(stream_with_context(generate_stream()), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, port=8010, host='0.0.0.0')