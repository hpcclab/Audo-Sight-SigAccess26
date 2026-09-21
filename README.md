# Audo-Sight

Assistive conversational perception for blind and low-vision (BLV) people, through collaborative edge–cloud intelligence.

Audo-Sight lets a BLV user ask about their surroundings and hear a concise spoken answer. On the edge, a Cognition Module reads the query, decides whether it is urgent, and routes it to a specialist vision model or to multimodal language models. For urgent open questions, speech starts from a fast local model. A Response Fusion Engine then continues the same utterance with a slower, more accurate cloud answer, correcting conflicts and dropping repeated detail.

This repository is the software prototype evaluated in *Audo-Sight: Assistive Conversational Perception through Collaborative Edge-Cloud Intelligence* (SIGACCESS, 25–28 September 2026, Porto). The manuscript is [`SIGACCESS26_LLM4SmartSight_jacob_Mohsen (2).pdf`](<SIGACCESS26_LLM4SmartSight_jacob_Mohsen (2).pdf>).

Python 3.11.9.

## What it does

Each request is a text query paired with a scene image. The Cognition Module sends it down one of four pipelines.

| Track | When it is used | Models | How the answer is spoken |
| --- | --- | --- | --- |
| Normal expert | Face, text, or objects, and the query is not urgent | Face recognition, PaddleOCR, or YOLOE | A local LLM rewrites the raw detector output, then speech |
| Urgent expert | Face, text, or objects, and the query is urgent | The same specialist models | Spoken directly |
| Normal generic | An open question, and the query is not urgent | Cloud multimodal LLM (GPT-5) | Spoken as generated |
| Urgent generic | An open question, and the query is urgent | Edge Gemma 3 4B and cloud GPT-5 in parallel | Response Fusion Engine, then speech |

Urgent wording asks for a short, immediate answer, such as the direction to a departure gate. A non-urgent question can wait for a fuller answer, such as the ingredients of a menu item.

The glasses prototype in the paper is a 3D-printed frame with a Raspberry Pi Zero 2 W and a camera, linked to the edge machine over Wi-Fi or USB. A button press captures a frame, and Whisper turns the voice query into text. The evaluation, and this repository, run that edge–cloud software on pre-captured images.

## Architecture

The paper’s Figure 2 and Figure 3 split the system into three modules. The code under `Systems/` implements them.

**Input.** The query and frame are paired and handed to the Cognition Module. The study web app takes a typed query over a fixed scene. `Audosight.Analysis` is the same entry point for a scripted call.

**Cognition Module.**

- **Urgency Detector.** A SetFit classifier on `all-MiniLM-L6-v2`. In the paper’s experiments a query is urgent when its urgent-class probability is above 0.3. SetFit tuning brought detection from about 30 ms down to about 9 ms. MiniLM’s F1 was 0.94, against 0.93 for a RoBERTa baseline, and it was several times faster on CPU.
- **AI Router.** The same MiniLM backbone, trained to choose object detection, face recognition, OCR, or a generic fallback. In the paper, a specialist route is taken when the top class is above 0.86. Anything below that threshold goes to the multimodal models.
- **Reasoning Engine.** Specialist models stay on the edge. Generic questions go to Gemma 3 4B locally, to GPT-5 in the cloud, or to both when the query is urgent. If the network drops, the edge model can still answer.

**Response Management.**

- **Blind-Friendly Response Editor.** For a non-urgent specialist answer, a local LLM rewrites raw model output into a direct reply. A face match of “John Doe” for “Is there anyone I know here?” becomes “Yes, John Doe is here.” Urgent specialist answers skip this step so speech can start sooner.
- **Response Fusion Engine** (`Systems/HybridModelManager.py`). Used for urgent generic questions. Edge and cloud models stream at the same time. If the cloud phrase arrives first, the edge stream is stopped and the cloud text is spoken. If the edge phrase arrives first, it is spoken immediately. When the cloud reply finishes, the edge model is stopped and a local LLM continues from the characters already spoken, treating the cloud reply as the reference.
- **Speech.** The fusion handoff estimates how many characters have been spoken from `EstimatedTTSSpeed` (characters per second) and `EstimatedMergeTime` in `Systems/config.txt`. The paper counts 15 characters per second as a normal rate. The study web app synthesizes speech with gTTS.

## Results reported in the paper

Automated runs used 200 VizWiz images. Each image had one question aimed at a specialist model and one open question, and half of the questions in each group were phrased as urgent. The machine was Windows 11, an Intel Core i9-10850K, 32 GB RAM, and an NVIDIA RTX 3080 Ti (12 GB), with cloud calls to GPT-5 over a North Texas connection. Speech playback time is left out of the latency numbers.

- Time to the first token on urgent tasks is about 80% lower than cloud-only GPT-5. On normal tasks it is about 50% lower.
- Average end-to-end latency across the dataset is about half that of cloud-only GPT-5, because about half of the tasks are answered by the edge specialist models.
- Scored against GPT-5 answers on correctness, completeness, faithfulness, and an overall average, Audo-Sight is ahead of edge-only Gemma 3 4B. The edge-only model scores higher on clarity, which the paper ties to urgent answers skipping the response editor.
- At a normal speaking rate, 84% of fused replies play with no gap. Gaps stay uncommon until about 150 characters per second, about ten times a normal rate. Non-urgent routes support still higher rates: about 8.8× for generic cloud answers and about 10× for edited specialist answers.
- On merging quality (redundancy, contradictions, added detail, and fluency), the Gemma fusion used here averages 74.9, against 64.5 for speaking the cloud text after the edge text and 46.3 for FLAN-T5. Edge and cloud replies on the fusion set were equivalent 48% of the time, complementary 23%, about different parts of the scene 2%, and contradictory 27%.

Eight legally blind participants (ages 41–74; six women and two men; four blind from birth) used both Audo-Sight and GPT-5 on the same restaurant and airport image sequences, without being told which system was which. Order alternated between participants. On the question of which guidance they preferred overall, 62% of responses chose Audo-Sight, 23% rated both the same, and 15% chose GPT-5. Both systems scored 4.1 out of 5 for helping participants imagine the environment. Clarity was 4.1 for Audo-Sight and 4.3 for GPT-5. Participants rated Audo-Sight’s message quality about 15% higher.

## Repository layout

| Path | Role |
| --- | --- |
| `Systems/AudoSight.py` | Pipeline: urgency, routing, specialists, and hybrid fusion |
| `Systems/UseUrgencyModel.py` | SetFit urgency classifier |
| `Systems/UseEmbedMoE.py` | SetFit router (`object`, `face`, `ocr`, `other`) |
| `Systems/ObjectDetModelManager.py` | YOLOE object detection (`yoloe-v8l-seg-pf`) |
| `Systems/OCRModelManager.py` | PaddleOCR |
| `Systems/FaceModelManager.py` | Face recognition from saved encodings |
| `Systems/ModelManager.py` | Local Gemma 3 4B through Ollama, including fusion and editing |
| `Systems/APIModelManager.py` | Cloud GPT-5 through OpenRouter |
| `Systems/HybridModelManager.py` | Parallel edge–cloud streaming and fusion |
| `Systems/config.txt` | Thresholds, classifier paths, TTS estimates |
| `Systems/setfitUrgent.py`, `Systems/setfitMoE.py` | Offline classifier training |
| `Systems/Moe_train_v5.json` | Router training sentences (object, face, OCR, other) |
| `webapp/app.py` | Flask study app used with participants (port 8010) |
| `images/` | Restaurant and airport scenes for that study |
| `requirements.txt` | Pinned Python dependencies |

## Setup

1. Use Python 3.11.9 and install the pinned dependencies from the repository root:

   ```bash
   pip install -r requirements.txt
   ```

   The urgency and router modules import `setfit`, which is not pinned in `requirements.txt`. Install it if that import fails:

   ```bash
   pip install setfit
   ```

2. Install [Ollama](https://ollama.com/) and pull the edge model. Leave the Ollama service running. `Systems/ModelManager.py` calls `gemma3:4b`.

   ```bash
   ollama pull gemma3:4b
   ```

3. Put the YOLOE weights at `Systems/models/yoloe-v8l-seg-pf.pt`. Face encodings already live under `Systems/models/FaceDetection/`.

4. Create `Systems/configSensitive.txt`. Keep this file out of version control.

   ```text
   OpenRouterKey = <your OpenRouter API key>
   FlaskKey = <a long random string>
   ```

   The OpenRouter key is sent as `openai/gpt-5`. The Flask key signs the study-app session.

5. Classifiers load from the folders named in `Systems/config.txt` (`Urgency_embed_path` and `MoE_embed_path`, currently `my-urgency-detector` and `my-moe-detector`, resolved under `Systems/`). Train them from the `Systems/` directory so the saved folders land where the loaders look:

   ```bash
   python setfitUrgent.py
   python setfitMoE.py
   ```

   `setfitUrgent.py` trains on the urgent and non-urgent sentences written in that script. `setfitMoE.py` reads `Moe_train_v5.json`.

The paper’s reported runs used an urgency threshold of 0.3 and a router threshold of 0.86. The values in this checkout are `Urgency_Threshold` and the `MoE_*_Threshold` entries in `Systems/config.txt`, along with `yolo_min_conf`, `EstimatedTTSSpeed`, and `EstimatedMergeTime`.

## Run

Interactive pipeline from the repository root. It loads the models, then answers typed questions about `images/test2_3.jpg`. Type `q` to quit.

```bash
python Systems/AudoSight.py
```

Study web app:

```bash
python webapp/app.py
```

Open `http://localhost:8010`. The app walks through the restaurant and airport sequences in `images/` and streams a spoken answer for each typed question. The next participant’s scenario order is stored in `webapp/configDynamic.txt`.

From Python, `Audosight.Analysis(query, image_path)` yields response text and then a dictionary with the route taken and per-stage timings.

## Citation

```bibtex
@inproceedings{bradshaw2026audosight,
  author    = {Bradshaw, Jacob and Riahi Alam, Mohsen and Ainary, Bhanuja and Kim, Minseo and Amini Salehi, Mohsen},
  title     = {Audo-Sight: Assistive Conversational Perception through Collaborative Edge-Cloud Intelligence},
  booktitle = {SIGACCESS},
  year      = {2026},
  address   = {Porto, Portugal},
  month     = sep,
  pages     = {1--16}
}
```

Jacob Bradshaw, Mohsen Riahi Alam, Bhanuja Ainary, Minseo Kim, and Mohsen Amini Salehi are with the University of North Texas College of Engineering, Denton, Texas.

## Acknowledgments

Supported by NASA through the MUREP ACEIR 2.0 Program, Award 80NSSC25M0054, and by NSF CAREER Award 2419588.
