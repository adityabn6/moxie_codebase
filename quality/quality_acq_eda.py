import argparse
import bioread
import pandas as pd
import numpy as np
import os

from bokeh.plotting import figure, output_file, save
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, RangeTool, Span, Label


def plot_bokeh_signal(signals_df, fs, title, output_path,
                      downsample_fs=10, window_seconds=60):

    if signals_df is None or signals_df.empty:
        print("No signal data available.")
        return

    required_cols = ["EDA_Raw", "EDA_Clean", "SCR_Onsets", "SCR_Peaks"]
    for col in required_cols:
        if col not in signals_df.columns:
            print(f"Missing required column: {col}")
            return

    original_fs = fs

    # -------------------------------------------------
    # Full-resolution time (NEVER downsample discrete markers)
    # -------------------------------------------------
    full_time = np.arange(len(signals_df)) / original_fs

    # -------------------------------------------------
    # Downsample continuous signals only
    # -------------------------------------------------
    downsample_factor = int(original_fs / downsample_fs)
    if downsample_factor < 1:
        downsample_factor = 1

    df_down = signals_df.iloc[::downsample_factor].copy().reset_index(drop=True)
    down_time = np.arange(len(df_down)) / (original_fs / downsample_factor)

    df_down["time"] = down_time
    source = ColumnDataSource(df_down)

    # -------------------------------------------------
    # Main Figure
    # -------------------------------------------------
    p = figure(
        title=title,
        height=400,
        width=1000,
        tools="xpan,xwheel_zoom,box_zoom,reset",
        active_scroll="xwheel_zoom"
    )

    # Continuous signals
    p.line("time", "EDA_Raw", source=source, legend_label="EDA Raw")
    p.line("time", "EDA_Clean", source=source, legend_label="EDA Clean", line_width=2)

    # -------------------------------------------------
    # SCR Onsets (full resolution)
    # -------------------------------------------------
    onset_mask = signals_df["SCR_Onsets"] == 1
    p.scatter(
        full_time[onset_mask],
        signals_df.loc[onset_mask, "EDA_Clean"],
        size=8,
        marker="circle",
        legend_label="SCR Onset"
    )

    # -------------------------------------------------
    # SCR Peaks (full resolution)
    # -------------------------------------------------
    peak_mask = signals_df["SCR_Peaks"] == 1
    p.scatter(
        full_time[peak_mask],
        signals_df.loc[peak_mask, "EDA_Clean"],
        size=10,
        marker="triangle",
        legend_label="SCR Peak"
    )

    # -------------------------------------------------
    # Event Labels (full resolution, visible text)
    # -------------------------------------------------
    if "Event_Label" in signals_df.columns:

        event_mask = (
            signals_df["Event_Label"].notna() &
            (signals_df["Event_Label"].astype(str).str.strip() != "")
        )

        event_times = full_time[event_mask]
        event_labels = signals_df.loc[event_mask, "Event_Label"]

        y_top = signals_df["EDA_Clean"].min()

        for t, label_text in zip(event_times, event_labels):

            # Vertical dashed line
            vline = Span(
                location=t,
                dimension='height',
                line_color='red',
                line_dash='dashed',
                line_width=1
            )
            p.add_layout(vline)

            # Rotated label text
            label = Label(
                x=t,
                y=y_top,
                text=str(label_text),
                angle=np.pi / 2,
                text_font_size="8pt",
                text_color="red"
            )
            p.add_layout(label)

    # -------------------------------------------------
    # Formatting
    # -------------------------------------------------
    p.legend.click_policy = "hide"
    p.xaxis.axis_label = "Time (seconds)"
    p.yaxis.axis_label = "EDA"

    p.x_range.start = 0
    p.x_range.end = min(window_seconds, full_time[-1])

    # -------------------------------------------------
    # Range Tool (bottom slider)
    # -------------------------------------------------
    select = figure(
        height=130,
        width=1000,
        y_range=p.y_range,
        tools="",
        toolbar_location=None
    )

    select.line("time", "EDA_Clean", source=source)

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
        data = bioread.read_file(args.file_path)
        sampling_rate = data.samples_per_second
    except Exception as e:
        print(f"Error reading ACQ file: {e}")
        return

    signal = pd.read_csv(args.input_file, low_memory=False)

    output_path = os.path.join(
        args.output_dir,
        f"{args.participant_id}_{args.visit_type}_EDA_QC.html"
    )

    plot_bokeh_signal(
        signal,
        sampling_rate,
        title=f"EDA Signal for {args.participant_id} - {args.visit_type}",
        output_path=output_path
    )


if __name__ == "__main__":
    main()
