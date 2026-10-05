import os
import glob
import pandas as pd
import json

def get_human_category(row):
    """Returns the marked category, or 'None/Unknown' if none/invalid."""
    categories = [
        'Equivalent', 
        'Complementary Collaborative', 
        'Distinct collaborative', 
        'Contradictory'
    ]
    for cat in categories:
        if row.get(cat) == 1 or str(row.get(cat)).strip() == '1':
            return cat
    return 'None/Unknown'

def generate_consensus_tally(folder_path):
    file_pattern = os.path.join(folder_path, 'completed_Human_Cat_*.xlsx')
    xlsx_files = glob.glob(file_pattern)
    
    if not xlsx_files:
        print(json.dumps({"error": f"No .xlsx files found in {folder_path}."}))
        return

    # 1. Aggregate votes from all files
    heatmap_data = {}
    categories = [
        'Equivalent', 
        'Complementary Collaborative', 
        'Distinct collaborative', 
        'Contradictory'
    ]
    
    for xlsx_file in xlsx_files:
        df = pd.read_excel(xlsx_file)
        for _, row in df.iterrows():
            query = str(row.get('Query', '')).strip()
            
            if query not in heatmap_data:
                heatmap_data[query] = {cat: 0 for cat in categories}
                heatmap_data[query]['None/Unknown'] = 0
                
            human_choice = get_human_category(row)
            if human_choice in categories:
                heatmap_data[query][human_choice] += 1
            else:
                heatmap_data[query]['None/Unknown'] += 1

    # 2. Determine Consensus and Format as JSON
    json_output = []
    
    for query, votes in heatmap_data.items():
        # Exclude 'None/Unknown' from the decision logic
        valid_votes = {cat: votes[cat] for cat in categories}
        max_votes = max(valid_votes.values()) if valid_votes else 0
        
        # Check if there is a clear winner or a tie
        top_categories = [cat for cat, count in valid_votes.items() if count == max_votes]
        
        if max_votes == 0 or len(top_categories) > 1:
            # Query is indecisive (either a tie or no valid votes at all)
            majority_vote = "n/a"
        else:
            # Clear consensus
            majority_vote = top_categories[0]

        # Append to our final list
        json_output.append({
            "query": query,
            "answers": votes,
            "majority_vote": majority_vote
        })

    # 3. Print Final JSON Output
    print(json.dumps(json_output, indent=4))
    output_file = os.path.join(folder_path, 'consensus_tally.json')
    with open(output_file, 'w') as f:
        json.dump(json_output, f, indent=4)

if __name__ == "__main__":
    FOLDER_PATH = 'CompleteCatHumanEvals' 
    generate_consensus_tally(FOLDER_PATH)