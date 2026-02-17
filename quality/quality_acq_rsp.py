import argparse
import bioread
import pandas as pd
import numpy as np
import os

from bokeh.plotting import figure, output_file, save
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, RangeTool, Span, Label


def plot_bokeh_rsp(signals_df, fs, title, output_path, downsample_fs=10, window_seconds=60):

    if signals_df is None or signals_df.empty:
        print("No signal data available.")
        return

    # Full-resolution time for discrete markers
    full_time = np.arange(len(signals_df)) / fs

    # Downsample continuous signals only
    downsample_factor = max(int(fs / downsample_fs), 1)
    df_down = signals_df.iloc[::downsample_factor].copy().reset_index(drop=True)
    df_down["time"] = np.linspace(0, full_time[-1], len(df_down))
    source = ColumnDataSource(df_down)

    # Figure
    p = figure(
        title=title,
        height=400,
        width=1000,
        tools="xpan,xwheel_zoom,box_zoom,reset",
        active_scroll="xwheel_zoom"
    )

    # -------------------------
    # Continuous signals (Raw + Clean for both channels)
    # -------------------------
    # Assuming columns are in order: Raw1, Clean1, ..., Raw2, Clean2, ...
    # Adjust indices if order changes
    raw1_idx = 0
    clean1_idx = 1
    peaks1_idx = 9  # zero/one column for channel 1 peaks
    raw2_idx = 11
    clean2_idx = 12
    peaks2_idx = 20  # zero/one column for channel 2 peaks

    p.line("time", df_down.columns[raw1_idx], source=source, legend_label="Raw Ch1")
    p.line("time", df_down.columns[clean1_idx], source=source, line_width=2, legend_label="Clean Ch1")
    p.line("time", df_down.columns[raw2_idx], source=source, legend_label="Raw Ch2", line_color="green")
    p.line("time", df_down.columns[clean2_idx], source=source, line_width=2, legend_label="Clean Ch2", line_color="darkgreen")

    # -------------------------
    # Peaks (full resolution)
    # -------------------------
    peaks1_mask = signals_df.iloc[:, peaks1_idx] == 1
    p.scatter(
        full_time[peaks1_mask],
        signals_df.loc[peaks1_mask, signals_df.columns[clean1_idx]],
        size=8, marker="triangle", color="blue", legend_label="Peaks Ch1"
    )

    peaks2_mask = signals_df.iloc[:, peaks2_idx] == 1
    p.scatter(
        full_time[peaks2_mask],
        signals_df.loc[peaks2_mask, signals_df.columns[clean2_idx]],
        size=8, marker="triangle", color="darkgreen", legend_label="Peaks Ch2"
    )

    # -------------------------
    # Event labels (full resolution)
    # -------------------------
    if "Event_Label" in signals_df.columns:
        event_mask = (
            signals_df["Event_Label"].notna() &
            (signals_df["Event_Label"].astype(str).str.strip() != "")
        )
        event_times = full_time[event_mask]
        event_labels = signals_df.loc[event_mask, "Event_Label"]
        y_top = signals_df.iloc[:, clean1_idx].min()
        for t, label_text in zip(event_times, event_labels):
            vline = Span(location=t, dimension="height", line_color="red", line_dash="dashed", line_width=1)
            p.add_layout(vline)
            label = Label(x=t, y=y_top, text=str(label_text), angle=np.pi/2, text_font_size="8pt", text_color="red")
            p.add_layout(label)

    # -------------------------
    # Formatting
    # -------------------------
    p.legend.click_policy = "hide"
    p.xaxis.axis_label = "Time (seconds)"
    p.yaxis.axis_label = "RSP"
    p.x_range.start = 0
    p.x_range.end = min(window_seconds, full_time[-1])

    # -------------------------
    # Range tool
    # -------------------------
    select = figure(height=130, width=1000, y_range=p.y_range, tools="", toolbar_location=None)
    select.line("time", df_down.columns[clean1_idx], source=source, line_color="darkblue")
    range_tool = RangeTool(x_range=p.x_range)
    range_tool.overlay.fill_alpha = 0.3
    range_tool.overlay.fill_color = "gray"
    select.add_tools(range_tool)
    select.x_range.start = 0
    select.x_range.end = full_time[-1]

    layout = column(p, select)
    output_file(output_path)
    save(layout)
    print(f"Saved interactive plot to {output_path}")


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

    signal = pd.read_csv(args.input_file, low_memory=False)

    output_path = os.path.join(
        args.output_dir,
        f"{args.participant_id}_{args.visit_type}_RSP_QC.html"
    )

    plot_bokeh_rsp(signal, sampling_rate,
                   title=f"RSP Signal for {args.participant_id} - {args.visit_type}",
                   output_path=output_path)


if __name__ == "__main__":
    main()
