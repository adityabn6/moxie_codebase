import argparse
import bioread
import pandas as pd
import numpy as np
import os

from bokeh.plotting import figure, output_file, save
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, RangeTool, Span, Label


def plot_bokeh_emg(emg_df, fs, title, output_path, downsample_fs=1, window_seconds=60):
    if emg_df is None or emg_df.empty:
        print("No EMG data available.")
        return

    # Full-resolution time
    full_time = np.arange(len(emg_df)) / fs

    # Downsample only continuous signals (Raw + Clean)
    downsample_factor = max(int(fs / downsample_fs), 1)
    df_down = emg_df.iloc[::downsample_factor].copy().reset_index(drop=True)
    df_down["time"] = np.linspace(0, full_time[-1], len(df_down))
    source = ColumnDataSource(df_down)

    # -------------------------
    # Figure
    # -------------------------
    p = figure(
        title=title,
        height=400,
        width=1000,
        tools="xpan,xwheel_zoom,box_zoom,reset",
        active_scroll="xwheel_zoom"
    )

    # -------------------------
    # Column indices (channel 1 and 2)
    # -------------------------
    raw1_idx = 0
    clean1_idx = 1
    onsets1_idx = 4
    offsets1_idx = 5

    raw2_idx = 6
    clean2_idx = 7
    onsets2_idx = 10
    offsets2_idx = 11

    # Continuous signals (downsampled)
    p.line("time", df_down.columns[raw1_idx], source=source, legend_label="Raw Ch1")
    p.line("time", df_down.columns[clean1_idx], source=source, line_width=2, legend_label="Clean Ch1", line_color="green")
    p.line("time", df_down.columns[raw2_idx], source=source, legend_label="Raw Ch2", line_color="orange")
    p.line("time", df_down.columns[clean2_idx], source=source, line_width=2, legend_label="Clean Ch2", line_color="red")

    # Onsets and offsets (full resolution)
    onsets1_mask = emg_df.iloc[:, onsets1_idx] != 0
    offsets1_mask = emg_df.iloc[:, offsets1_idx] != 0
    onsets2_mask = emg_df.iloc[:, onsets2_idx] != 0
    offsets2_mask = emg_df.iloc[:, offsets2_idx] != 0

    p.scatter(
        full_time[onsets1_mask],
        emg_df.loc[onsets1_mask, emg_df.columns[clean1_idx]],
        size=8, marker="triangle", color="blue", legend_label="Onsets Ch1"
    )
    p.scatter(
        full_time[offsets1_mask],
        emg_df.loc[offsets1_mask, emg_df.columns[clean1_idx]],
        size=8, marker="inverted_triangle", color="blue", legend_label="Offsets Ch1"
    )
    p.scatter(
        full_time[onsets2_mask],
        emg_df.loc[onsets2_mask, emg_df.columns[clean2_idx]],
        size=8, marker="triangle", color="red", legend_label="Onsets Ch2"
    )
    p.scatter(
        full_time[offsets2_mask],
        emg_df.loc[offsets2_mask, emg_df.columns[clean2_idx]],
        size=8, marker="inverted_triangle", color="red", legend_label="Offsets Ch2"
    )

    # Event labels
    if emg_df.shape[1] > 12:  # Event_Label is last column
        event_mask = emg_df.iloc[:, -1].notna() & (emg_df.iloc[:, -1].astype(str).str.strip() != "")
        y_top = emg_df.iloc[:, clean1_idx].min()
        for t, label_text in zip(full_time[event_mask], emg_df.iloc[event_mask, -1]):
            vline = Span(location=t, dimension="height", line_color="purple", line_dash="dashed", line_width=1)
            p.add_layout(vline)
            label = Label(x=t, y=y_top, text=str(label_text), angle=np.pi/2, text_font_size="8pt", text_color="purple")
            p.add_layout(label)

    # Formatting
    p.legend.click_policy = "hide"
    p.xaxis.axis_label = "Time (seconds)"
    p.yaxis.axis_label = "EMG"
    p.x_range.start = 0
    p.x_range.end = min(window_seconds, full_time[-1])

    # Range tool
    select = figure(height=130, width=1000, y_range=p.y_range, tools="", toolbar_location=None)
    select.line("time", df_down.columns[clean1_idx], source=source, line_color="green")
    range_tool = RangeTool(x_range=p.x_range)
    range_tool.overlay.fill_alpha = 0.3
    range_tool.overlay.fill_color = "gray"
    select.add_tools(range_tool)
    select.x_range.start = 0
    select.x_range.end = full_time[-1]

    layout = column(p, select)
    output_file(output_path)
    save(layout)
    print(f"Saved interactive EMG plot to {output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--participant_id", required=True)
    parser.add_argument("--visit_type", required=True)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--input_file", required=True)
    parser.add_argument("--file_path", required=True)
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    try:
        data_acq = bioread.read_file(args.file_path)
        sampling_rate = data_acq.samples_per_second
    except Exception as e:
        print(f"Error reading ACQ file: {e}")
        return

    emg_data = pd.read_csv(args.input_file, low_memory=False)

    output_path = os.path.join(
        args.output_dir,
        f"{args.participant_id}_{args.visit_type}_acq_EMG_QC.html"
    )

    plot_bokeh_emg(
        emg_data,
        sampling_rate,
        title=f"EMG Signal for {args.participant_id} - {args.visit_type}",
        output_path=output_path
    )


if __name__ == "__main__":
    main()
