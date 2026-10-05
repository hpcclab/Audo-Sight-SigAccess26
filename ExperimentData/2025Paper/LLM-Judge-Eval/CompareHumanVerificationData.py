import os
import glob
import json
import pandas as pd
from [NAME] import Workbook
from [NAME].utils.dataframe import dataframe_to_rows
from [NAME].formatting.rule import ColorScaleRule
from [NAME].styles import Font, Alignment, PatternFill, Border, Side
from [NAME].utils import get_column_letter

def fix_mojibake(data):
    if isinstance(data, str):
        try:
            return data.encode('cp1252').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            return data.replace('\u00e2\u20ac\u2122', "'")
    elif isinstance(data, dict):
        return {k: fix_mojibake(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [fix_mojibake(item) for item in data]
    else:
        return data

def get_human_category(row):
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

def generate_eval_heatmap(folder_path, output_filename='Human_Eval_Heatmap.xlsx'):
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
    
    total_evaluators = len(xlsx_files)
    print(f"Aggregating data across {total_evaluators} files...")

    for xlsx_file in xlsx_files:
        df = pd.read_excel(xlsx_file)
        for _, row in df.iterrows():
            query = str(row.get('Query', '')).strip()
            
            if query not in heatmap_data:
                heatmap_data[query] = {cat: 0 for cat in categories}
                
            human_choice = get_human_category(row)
            if human_choice in categories:
                heatmap_data[query][human_choice] += 1

    # 2. Convert to DataFrame
    records = []
    for q, counts in heatmap_data.items():
        row_dict = {'Query': q}
        row_dict.update(counts)
        records.append(row_dict)
        
    df_heatmap = pd.DataFrame(records)

    # 3. Build and format Excel Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Consensus Heatmap"

    for r in dataframe_to_rows(df_heatmap, index=False, header=True):
        ws.append(r)

    # Apply Header Styling
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    thin_border = Border(left=Side(style='thin', color='D9D9D9'),
                         right=Side(style='thin', color='D9D9D9'),
                         top=Side(style='thin', color='D9D9D9'),
                         bottom=Side(style='thin', color='D9D9D9'))

    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border
    ws.row_dimensions[1].height = 30

    # Adjust Column widths & cell formatting
    ws.column_dimensions['A'].width = 65
    for col in range(2, 6):
        ws.column_dimensions[get_column_letter(col)].width = 25

    for row in range(2, len(records) + 2):
        ws.cell(row=row, column=1).alignment = Alignment(wrap_text=True)
        ws.cell(row=row, column=1).border = thin_border
        
        for col in range(2, 6):
            cell = ws.cell(row=row, column=col)
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border

    # 4. Add the Conditional Formatting (Heatmap Colors)
    # Scales from white (0 votes) to red (everyone voted for it)
    rule = ColorScaleRule(start_type='num', start_value=0, start_color='FFFFFF',
                          mid_type='num', mid_value=(total_evaluators/2), mid_color='FF9999',
                          end_type='num', end_value=total_evaluators, end_color='FF0000')

    ws.conditional_formatting.add(f'B2:E{len(records)+1}', rule)

    out_path = os.path.join(folder_path, output_filename)
    wb.save(out_path)
    print(f"Heatmap generated successfully: {out_path}")

if __name__ == "__main__":
    FOLDER_PATH = 'CompleteCatHumanEvals' 
    generate_eval_heatmap(FOLDER_PATH)