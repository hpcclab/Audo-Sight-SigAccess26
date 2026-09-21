from ollama import chat
from ollama import ChatResponse
import os

class ModelManager:
    model = "gemma3:4b" # Ensure you have this model pulled in Ollama

    def load_models(self):
        # Trigger a small load to ensure model is in VRAM if needed
        try:
            chat(model=self.model, messages=[{'role':'user','content':'ping'}])
            print("Local LLM Loaded.")
        except:
            print("Could not load Local LLM. Ensure Ollama is running.")

    def Generate(self, prompt, imagePath):
        """
        Generator function that streams text from Ollama.
        """
        completePrompt = f"Concisely answer this query in paragraph form using the image. {prompt}"
        
        try:
            # enable stream=True
            stream = chat(
                model=self.model,
                messages=[
                    {
                        'role': 'user',
                        'content': completePrompt,
                        'images': [imagePath] 
                    }
                ],
                stream=True 
            )

            for chunk in stream:
                # Ollama yields objects with 'message' -> 'content'
                content = chunk.get('message', {}).get('content', '')
                if content:
                    content.replace("*","")
                    yield content

        except Exception as e:
            print(f"Ollama Error: {e}")
            yield f" [Local Error: {str(e)}] "

    def GenerateMergingText(self, prompt, alreadySpoken=""):
        """
        Generator function that streams text from Ollama (Text Only).
        """
        try:
            stream = chat(
                model=self.model,
                messages=[{'role': 'user', 'content': prompt}, {'role': 'assistant', 'content': alreadySpoken}],
                stream=True 
            )

            for chunk in stream:
                content = chunk.get('message', {}).get('content', '')
                if content:
                    yield content

        except Exception as e:
            print(f"Ollama Text Error: {e}")
            yield f" [Local Text Error: {str(e)}] "

    def GenerateText(self, prompt):
        """
        Generator function that streams text from Ollama (Text Only).
        """
        try:
            stream = chat(
                model=self.model,
                messages=[{'role': 'user', 'content': prompt}],
                stream=True 
            )

            for chunk in stream:
                content = chunk.get('message', {}).get('content', '')
                if content:
                    yield content

        except Exception as e:
            print(f"Ollama Text Error: {e}")
            yield f" [Local Text Error: {str(e)}] "