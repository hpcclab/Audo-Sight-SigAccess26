import threading
import queue
import time
import re
from .ModelManager import ModelManager
from .APIModelManager import APIModelManager
from .configHandler import load_config

class HybridModelManager:
    def __init__(self, local_model_manager: ModelManager, cloud_model_manager: APIModelManager):
        self.local_model = local_model_manager
        self.cloud_model = cloud_model_manager
        self.config = load_config("config.txt")
        self.tts_speed = float(self.config.get("EstimatedTTSSpeed", 15)) # chars per second
        self.merge_time = float(self.config.get("EstimatedMergeTime", 2)) # seconds



    def Generate(self, prompt, image_path, debug=False, moeData="", record_token_times=False):
        """
        Runs local and cloud models concurrently.
        Streams the first one to respond.
        If local finishes first, and cloud eventually finishes,
        it merges the results using the local model and streams the merge.
        """
        
        LocalResponseTime = 0
        MergeResponseTime = 0
        MergeTurnaroundTime = 0
        CloudTurnaroundTime = 0
        CloudResponseTime = 0
        LocalTurnaroundTime = 0
        
        token_times = []

        # Queues to capture chunks from generators
        local_queue = queue.Queue()
        cloud_queue = queue.Queue()
        
        # Flags and buffers
        local_done = threading.Event()
        cloud_done = threading.Event()
        
        local_buffer = []
        cloud_buffer = []
        
        analysis_data = {}
        updatedPrompt = moeData
        # Wrapper to run generator and put chunks in queue
        def run_model(generator_func, q, done_event, buffer_list, name):
            try:
                for chunk in generator_func(prompt, image_path):
                    q.put(chunk)
                    buffer_list.append(chunk)
            except Exception as e:
                q.put(f" [{name} Error: {e}] ")
            finally:
                done_event.set()
                q.put(None) # Sentinel

        # Start threads
        t_local = threading.Thread(target=run_model, args=(self.local_model.Generate, local_queue, local_done, local_buffer, "Local"))
        t_cloud = threading.Thread(target=run_model, args=(self.cloud_model.get_completion, cloud_queue, cloud_done, cloud_buffer, "Cloud"))
        
        start_time = time.time()
        t_local.start()
        t_cloud.start()
        
        
        # Determine winner
        winner = None # 'local' or 'cloud'
        
        while True:
            # Check if either has data
            local_has_data = not local_queue.empty()
            cloud_has_data = not cloud_queue.empty()

            if local_has_data and not winner:
                winner = 'local'
                LocalResponseTime = time.time() - start_time
                if debug: print(f"[DEBUG] Winner: {winner}")
            elif cloud_has_data and not winner:
                winner = 'cloud'
                CloudResponseTime = time.time() - start_time
                if debug: print(f"[DEBUG] Winner: {winner}")
            
            if winner:
                break
            
            # If both finished without data (error?), break
            if local_done.is_set() and cloud_done.is_set():
                break
            
            time.sleep(0.01)
            
        # Stream the winner
        active_queue = local_queue if winner == 'local' else cloud_queue
        active_done = local_done if winner == 'local' else cloud_done
        
        while True:
            try:
                if not cloud_has_data:
                    CloudResponseTime = time.time() - start_time
                chunk = active_queue.get(timeout=0.1)
                if chunk is None:
                    break
                if record_token_times and isinstance(chunk, str):
                    token_times.append({"token": chunk, "time": time.time() - start_time, "source": winner})
                yield chunk
            except queue.Empty:
                if active_done.is_set() and active_queue.empty():   
                    break
                continue
        LocalTurnaroundTime = time.time() - start_time
        # If Cloud won, we are done (Cloud is prioritized source anyway)
        if winner == 'cloud':
            if debug: print(f"\n[DEBUG] Cloud won. No merge needed.")
            return

        # If Local won, wait for Cloud to finish to see if we need to merge
        # We stream the local response, but now we check if cloud has something better
        if not cloud_has_data:
            while not cloud_done.is_set():
                cloud_has_data = not cloud_queue.empty()
                if cloud_has_data or CloudResponseTime >= 29:
                    break
                time.sleep(0.01)
                CloudResponseTime = time.time() - start_time
        
        t_cloud.join(timeout=1) # Wait for cloud to finish, but timeout after 29s
        cloud_finish_time = time.time()
        
        if t_cloud.is_alive() or not cloud_done.is_set():
            cloud_response = "No cloud response available."
            t_cloud.join()
        else:
            cloud_response = "".join(cloud_buffer)
        local_response = "".join(local_buffer)
        
        # Calculate seamless transition point
        current_time = time.time()
        elapsed_time = current_time - start_time
        CloudTurnaroundTime = cloud_finish_time - start_time
        
        # Estimate where the user is in the audio
        # We add EstimatedMergeTime because that's how long it will take to generate the merge
        target_time = elapsed_time + self.merge_time
        estimated_chars_spoken = int(target_time * self.tts_speed)

        # Snap to the next sentence break
        match = re.search(r'[.!?]', local_response[estimated_chars_spoken:])
        if match:
            estimated_chars_spoken += match.end()
        
        # Clamp to length of local response
        if estimated_chars_spoken > len(local_response):
            estimated_chars_spoken = len(local_response)
        
        spoken_text = local_response[:estimated_chars_spoken]

        if debug:
            print(f"\n[DEBUG] Time Before Merge: {elapsed_time:.2f}s")
            print(f"[DEBUG] Cloud Turnaround Time: {CloudTurnaroundTime:.2f}s")
            print(f"[DEBUG] Estimated Spoken Chars: {estimated_chars_spoken}")
            print(f"[DEBUG] Spoken Text: '{spoken_text}'")
            print(f"[DEBUG] Local Response Length: {len(local_response)}")
            print(f"[DEBUG] Cloud Response Length: {len(cloud_response)}")
            print(f"[DEBUG] Cloud Response: {cloud_response}")
            print(f"[DEBUG] Merge streaming starting now.")
        
        # Merge logic
        merge_prompt = (
            f"You are a helpful assistant. "
            f"You are in the middle of speaking this to the user: '{local_response}'. "
            f"The truth is: '{cloud_response}'. "
            f"You have already said this part of a response: '{spoken_text}'. Don't say it again. Continue from here "
            f"Pick up seamlessly from where you left off, merging the new information from the truth. "
            f"Do not repeat what you already said. Just continue the sentence."
            f"Also, if there is any conflict between your response and the truth, choose the truth."
            f"If you have stated any information that was shown to be incorrect, correct it in the merged response."
        )
        
        # Yield signal for app.py to handle TTS transition
        yield {"type": "merge_signal", "spoken_chars": estimated_chars_spoken}
        start_time = time.time()
        merge_response = ""
        # Stream the merge
        for chunk in self.local_model.GenerateMergingText(merge_prompt, alreadySpoken=spoken_text):
            if merge_response == "":
                MergeResponseTime = time.time() - start_time
            merge_response += chunk
            if record_token_times and isinstance(chunk, str):
                token_times.append({"token": chunk, "time": time.time() - start_time, "source": "merge"})
            yield chunk
        
        MergeTurnaroundTime = time.time() - start_time
        if debug: print(f"[DEBUG] Merge Response: {merge_response}")
        
        analysis_data = {
            "type": "analysis_data",
            "full_response_text": local_response + cloud_response, # What was given before the cloud responded + what was given by the merging llm
            "Local_response_text": local_response, # What was given by the local mllm
            "Merging_response_text": merge_response, # What was given by the merging llm
            "Cloud_response_text": cloud_response, # What was given by the cloud mllm
            "Complete_hybrid_response_text": local_response[:estimated_chars_spoken] + merge_response, # The final corrected response - cropped local mllm response + merged response
            "estimated_chars_spoken": estimated_chars_spoken,
            "Spoken_text": spoken_text,
            "LocalResponseTime": LocalResponseTime, # GOT IT
            "LocalTurnaroundTime": LocalTurnaroundTime, # GOT IT
            "MergeResponseTime": MergeResponseTime, # Got it
            "MergeTurnaroundTime": MergeTurnaroundTime, # GOT IT
            "CloudTurnaroundTime": CloudTurnaroundTime,
            "CloudResponseTime": CloudResponseTime
        }
        
        if record_token_times:
            analysis_data["token_times"] = token_times
            
        yield analysis_data
