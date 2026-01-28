import argparse
import sys
import os
from pathlib import Path

try:
    import whisper
except ImportError:
    print("Error: whisper library not found. Install with: pip install openai-whisper")
    sys.exit(1)


def process_thoughts(wav_path, model):
    """
    Transcribe audio file using Whisper model.
    """
    print(f"Processing {wav_path}...")
    
    segments, info = model.transcribe(
        wav_path.as_posix(),
        language="en"
    )


    # Build output text file path
    txt_path = wav_path.with_suffix(".txt")

    # Write transcript
    with open(txt_path, "w", encoding="utf-8") as f:
        for segment in segments:
            f.write(segment.text.strip() + "\n")

    print(f"Saved transcript to: {txt_path}")
    print("-----------------------------------")
    
    return txt_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--participant_id", required=True)
    parser.add_argument("--visit_type", required=True)
    parser.add_argument("--wav_file", required=True)
    parser.add_argument("--events_file", required=True)
    parser.add_argument("--output_dir", required=True)
    
    args = parser.parse_args()
    
    # Load WAV file
    wav_path = Path(args.wav_file)
    if not wav_path.exists():
        print(f"Error: WAV file not found: {args.wav_file}")
        sys.exit(1)
    
    # Load model
    model = whisper.load_model("medium")
    
    # Process
    txt_path = process_thoughts(wav_path, model)
    
    # Move to output directory with proper naming
    output_filename = f"processed_thoughts_{args.participant_id}_{args.visit_type.replace(' ', '_')}.txt"
    output_file = os.path.join(args.output_dir, output_filename)
    
    # Copy the transcript to output directory
    with open(txt_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"Processed transcript saved to {output_file}")

if __name__ == "__main__":
    main()
