import base64
import requests
import json
from .configHandler import load_config

class APIModelManager:
    CONFIG_PATH = "configSensitive.txt"
    config = None
    OPENROUTER_API_KEY = ""
    
    def __init__(self):
        self.config = load_config(self.CONFIG_PATH)
        self.OPENROUTER_API_KEY = self.config.get("OpenRouterKey")
        # print(f"Got key: {self.OPENROUTER_API_KEY}")

    def encode_image_to_base64(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def get_completion(self, prompt, image_path, model="openai/gpt-5"):
        """
        Generator function that streams text from OpenRouter API.
        """
        try:
            api_key = self.OPENROUTER_API_KEY

            if not prompt:
                yield "error: No prompt provided."
                return

            base64_image = self.encode_image_to_base64(image_path)
            data_url = f"data:image/jpeg;base64,{base64_image}"
            
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                # "HTTP-Referer": "http://localhost:8000", # Optional for OpenRouter
            }
            completePrompt = f"Concisely answer this query in paragraph form using the image. {prompt}"
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": completePrompt},
                        {"type": "image_url", "image_url": {"url": data_url}}
                    ]
                }
            ]

            payload = {
                "model": model,
                "messages": messages,
                "stream": True  # <--- CRITICAL: Must be True
            }

            # stream=True in requests
            response = requests.post(url, headers=headers, json=payload, stream=True, timeout=29)
            response.raise_for_status()

            # Iterate over the network stream line by line
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    
                    # Parse Server-Sent Events (SSE)
                    if decoded_line.startswith('data: ') and decoded_line != 'data: [DONE]':
                        try:
                            json_str = decoded_line[6:] # Strip "data: "
                            json_data = json.loads(json_str)
                            
                            # Standard OpenAI/OpenRouter format: choices[0].delta.content
                            delta = json_data.get('choices', [{}])[0].get('delta', {})
                            content = delta.get('content', '')
                            
                            if content:
                                yield content
                                
                        except json.JSONDecodeError:
                            pass
                        except Exception as inner_e:
                            print(f"Parse error: {inner_e}")

        except Exception as e:
            print(f'API request failed: {e}')
            yield f" [API Error: {str(e)}] "