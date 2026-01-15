import argparse
import pandas as pd
import sys
import os

def view_csv_head(file_path, n_rows=5):
    """
    Reads and displays the first n_rows of a CSV file using pandas.
    """
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)

    try:
        # Load only the first n_rows + 1 (header) to avoid loading massive files
        df = pd.read_csv(file_path, nrows=n_rows)
        
        print(f"\n--- First {n_rows} rows of {file_path} ---\n")
        print(df.to_string())
        print(f"\n\n[Total columns: {len(df.columns)}]")
        print(f"Columns: {', '.join(df.columns)}")
        
    except Exception as e:
        print(f"Error reading CSV: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="View the head of a CSV file.")
    parser.add_argument("file", help="Path to the CSV file")
    parser.add_argument("-n", "--rows", type=int, default=5, help="Number of rows to display (default: 5)")
    
    args = parser.parse_args()
    
    view_csv_head(args.file, args.rows)
