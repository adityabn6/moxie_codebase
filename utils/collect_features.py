import argparse
import os
import shutil
import glob
from pathlib import Path

def collect_features(source_dir, dest_dir, pattern="features_*.csv", dry_run=False):
    """
    Recursively finds feature CSV files in source_dir and copies them to dest_dir.
    """
    source_path = Path(source_dir)
    dest_path = Path(dest_dir)
    
    if not source_path.exists():
        print(f"Error: Source directory '{source_dir}' does not exist.")
        return

    if not dest_path.exists():
        print(f"Creating destination directory: {dest_dir}")
        if not dry_run:
            dest_path.mkdir(parents=True, exist_ok=True)
            
    print(f"Searching for files matching '{pattern}' in {source_dir}...")
    
    # helper to find files recursively
    files_found = list(source_path.rglob(pattern))
    
    if not files_found:
        print("No files found matching the pattern.")
        return

    print(f"Found {len(files_found)} files.")
    
    copied_count = 0
    for file_path in files_found:
        filename = file_path.name
        destination_file = dest_path / filename
        
        # Check for name collision (though names should be unique based on ID/Visit suffix)
        if destination_file.exists():
            print(f"Warning: File '{filename}' already exists in destination. Overwriting.")
            
        print(f"Copying {file_path} -> {destination_file}")
        
        if not dry_run:
            try:
                shutil.copy2(file_path, destination_file)
                copied_count += 1
            except Exception as e:
                print(f"Error copying {file_path}: {e}")
                
    if not dry_run:
        print(f"\nSuccessfully copied {copied_count} files to {dest_dir}")
    else:
        print(f"\n[Dry Run] matched {len(files_found)} files that would be copied.")

def main():
    parser = argparse.ArgumentParser(description="Collect feature CSV files recursively from a source directory to a destination folder.")
    
    parser.add_argument("source_dir", help="Root directory to search for feature files (e.g., Processed_Data)")
    parser.add_argument("dest_dir", help="Destination folder to copy files into")
    parser.add_argument("--pattern", default="features_*.csv", help="Glob pattern to match filenames (default: 'features_*.csv')")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without actual copying")
    
    args = parser.parse_args()
    
    collect_features(args.source_dir, args.dest_dir, args.pattern, args.dry_run)

if __name__ == "__main__":
    main()
