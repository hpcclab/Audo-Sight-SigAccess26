import json
import csv
import random

def fix_mojibake(data):
    """Recursively traverses the JSON data to fix double-encoded strings."""
    if isinstance(data, str):
        try:
            # Revert the string to bytes using Windows-1252, then decode as UTF-8
            return data.encode('cp1252').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            # If the string isn't standard double-encoded mojibake, just return it
            # (or use a manual replacement fallback just in case)
            return data.replace('\u00e2\u20ac\u2122', "'")
    elif isinstance(data, dict):
        return {k: fix_mojibake(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [fix_mojibake(item) for item in data]
    else:
        return data

def process_and_shuffle_json(input_filepath, all_data_csv, answers_only_csv, seed_value):
    # 1. Load the JSON data
    try:
        with open(input_filepath, 'r', encoding='utf-8') as file:
            raw_data = json.load(file)
            # Apply the fix immediately after loading
            data = fix_mojibake(raw_data)
    except Exception as e:
        print(f"Error loading JSON file: {e}")
        return

    if not data:
        print("The JSON file is empty.")
        return

    # 2. Shuffle the data using the provided seed
    random.seed(seed_value)
    random.shuffle(data)

    # 3. Write File 1: All data and the seed
    all_data_headers = list(data[0].keys()) + ['seed']
    
    with open(all_data_csv, 'w', newline='', encoding='utf-8-sig') as file1:
        writer = csv.writer(file1)
        writer.writerow(all_data_headers)
        
        for item in data:
            row = []
            for key in data[0].keys():
                val = item.get(key, "")
                if isinstance(val, (dict, list)):
                    row.append(json.dumps(val))
                else:
                    row.append(val)
            row.append(seed_value)
            writer.writerow(row)
            
    print(f"Successfully created: {all_data_csv}")

    # 4. Write File 2: Only specific answer fields
    specific_headers = ['Query', 'Answer1', 'Answer2', 'Equivalent', 'Complementary Collaborative', 'Distinct collaborative', 'Contradictory']
    
    with open(answers_only_csv, 'w', newline='', encoding='utf-8-sig') as file2:
        writer = csv.DictWriter(file2, fieldnames=specific_headers)
        writer.writeheader()
        
        for item in data:
            answers = item.get('answers_used', {})
            writer.writerow({
                'Query': item.get('query', ""), 
                'Answer1': answers.get('ground_truth', ''),
                'Answer2': answers.get('local_llm', ''),
                'Equivalent': "",
                'Complementary Collaborative': "",
                'Distinct collaborative': "",
                'Contradictory': ""
            })
            
    print(f"Successfully created: {answers_only_csv}")

# --- Execution ---
if __name__ == "__main__":
    for seed in range(1, 4):
        print(f"\nProcessing with seed: {seed}")
        INPUT_JSON_FILE = 'test_filtered_out_noresponse_AS_scored_CO_2026-06-09_10-38-03.json'
        OUTPUT_ALL_DATA = f'shuffled_complete_data_seed_{seed}.csv'
        OUTPUT_ANSWERS = f'shuffled_Human_Cat_seed_{seed}.csv'
        
        process_and_shuffle_json(INPUT_JSON_FILE, OUTPUT_ALL_DATA, OUTPUT_ANSWERS, seed)