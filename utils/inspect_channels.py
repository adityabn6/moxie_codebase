import bioread
import sys

# File from previous steps
FILE = r"N:\Aditya\Participant Data\126641\TSST Visit\Acqknowledge\TSST_Acqknowledge_126641_11_4_2025.acq"

try:
    data = bioread.read_file(FILE)
    print("Channels found:")
    for c in data.channels:
        print(f" - {c.name} (Units: {c.units}, FS: {c.samples_per_second})")
        if any(x in c.name.upper() for x in ["BP", "BLOOD", "PRES", "SYS", "DIA", "NIBP"]):
            print(f"   *** Potential BP Channel ***")
            
    print("\nNamed Channels (keys):")
    print(list(data.named_channels.keys()))
    
    print("\nEvent Markers:")
    if hasattr(data, 'event_markers'):
        for m in data.event_markers:
            print(f" - {m.text} at {m.sample_index} ({m.date_created_str})")
    else:
        print(" - No event_markers attribute.")

except Exception as e:
    print(e)
