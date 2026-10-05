import os
import glob
import pandas as pd

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
        print(f"No .xlsx files found in {folder_path}.")
        return

    # 1. Aggregate votes from all files
    heatmap_data = {}
    categories = [
        'Equivalent', 
        'Complementary Collaborative', 
        'Distinct collaborative', 
        'Contradictory'
    ]
    
    print(f"Aggregating data across {len(xlsx_files)} evaluators...")

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

    # 2. Determine Consensus and Tally Results
    consensus_tally = {cat: 0 for cat in categories}
    indecisive_count = 0
    total_queries = len(heatmap_data)
    
    for query, votes in heatmap_data.items():
        # Exclude 'None/Unknown' from the decision logic
        valid_votes = {cat: votes[cat] for cat in categories}
        max_votes = max(valid_votes.values())
        
        # Check if there is a clear winner or a tie
        top_categories = [cat for cat, count in valid_votes.items() if count == max_votes]
        
        if max_votes == 0 or len(top_categories) > 1:
            # Query is indecisive (either a tie or no valid votes at all)
            indecisive_count += 1
        else:
            # Clear consensus
            winning_category = top_categories[0]
            consensus_tally[winning_category] += 1

    # 3. Print Final Tally Output
    print("\n" + "="*45)
    print("FINAL CONSENSUS TALLY (Excluding Indecisive)")
    print("="*45)
    
    for cat in categories:
        print(f"{cat:<30}: {consensus_tally[cat]} queries")
        
    print("-" * 45)
    print(f"{'Indecisive/Tied (Excluded)':<30}: {indecisive_count} queries")
    print(f"{'Total Unique Queries Analyzed':<30}: {total_queries} queries")
    print("="*45)

if __name__ == "__main__":
    FOLDER_PATH = 'CompleteCatHumanEvals' 
    generate_consensus_tally(FOLDER_PATH)