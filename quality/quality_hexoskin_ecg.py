import argparse
import bioread
import pandas as pd
import numpy as np
import os

from bokeh.plotting import figure, output_file, save
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, RangeTool, Span, Label, DataRange1d


def plot_bokeh_ecg(ecg_df, fs, title, output_path, downsample_fs=1, window_seconds=60):
    if ecg_df is None or ecg_df.empty:
        print("No ECG data available.")
        return

    # Full-resolution time
    full_time = np.arange(len(ecg_df)) / fs

    # Downsample only continuous signals (Raw + Clean)
    downsample_factor = max(int(fs / downsample_fs), 1)
    df_down = ecg_df.iloc[::downsample_factor].copy().reset_index(drop=True)
    df_down["time"] = np.linspace(0, full_time[-1], len(df_down))
    source = ColumnDataSource(df_down)

    # -------------------------
    # Dynamic y-range
    # -------------------------
    y_range = DataRange1d()
    p = figure(
        title=title,
        height=400,
        width=1000,
        tools="xpan,xwheel_zoom,box_zoom,reset",
        active_scroll="xwheel_zoom",
        y_range=y_range
    )

    # -------------------------
    # Column indices
    # -------------------------
    raw_idx = 0
    clean_idx = 1
    r_peaks_idx = 4
    p_peaks_idx = 5

    # Continuous signals (downsampled)
    p.line("time", df_down.columns[raw_idx], source=source, legend_label="Raw ECG")
    p.line("time", df_down.columns[clean_idx], source=source, line_width=2, legend_label="Clean ECG", line_color="green")

    # Peaks (full resolution)
    r_mask = ecg_df.iloc[:, r_peaks_idx] != 0
    p.scatter(
        full_time[r_mask],
        ecg_df.loc[r_mask, ecg_df.columns[clean_idx]],
        size=8, marker="triangle", color="red", legend_label="R Peaks"
    )

    p_mask = ecg_df.iloc[:, p_peaks_idx] != 0
    p.scatter(
        full_time[p_mask],
        ecg_df.loc[p_mask, ecg_df.columns[clean_idx]],
        size=8, marker="triangle", color="blue", legend_label="P Peaks"
    )

    # Event labels
    if "Event_Label" in ecg_df.columns:
        event_mask = ecg_df["Event_Label"].notna() & (ecg_df["Event_Label"].astype(str).str.strip() != "")
        y_top = ecg_df.iloc[:, clean_idx].min()
        for t, label_text in zip(full_time[event_mask], ecg_df.loc[event_mask, "Event_Label"]):
            vline = Span(location=t, dimension="height", line_color="purple", line_dash="dashed", line_width=1)
            p.add_layout(vline)
            label = Label(x=t, y=y_top, text=str(label_text), angle=np.pi/2, text_font_size="8pt", text_color="purple")
            p.add_layout(label)

    # -------------------------
    # Formatting
    # -------------------------
    p.legend.click_policy = "hide"
    p.xaxis.axis_label = "Time (seconds)"
    p.yaxis.axis_label = "ECG"
    p.x_range.start = 0
    p.x_range.end = min(window_seconds, full_time[-1])

    # Range tool (bottom slider)
    select = figure(height=130, width=1000, y_range=p.y_range, tools="", toolbar_location=None)
    select.line("time", df_down.columns[clean_idx], source=source, line_color="green")
    range_tool = RangeTool(x_range=p.x_range)
    range_tool.overlay.fill_alpha = 0.3
    range_tool.overlay.fill_color = "gray"
    select.add_tools(range_tool)
    select.x_range.start = 0
    select.x_range.end = full_time[-1]

    layout = column(p, select)
    output_file(output_path)
    save(layout)
    print(f"Saved interactive ECG plot to {output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--participant_id", required=True)
    parser.add_argument("--visit_type", required=True)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--input_file", required=True)
    parser.add_argument("--file_path", required=True)

    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    

    ecg_data = pd.read_csv(args.input_file, low_memory=False)
    

    output_path = os.path.join(
        args.output_dir,
        f"{args.participant_id}_{args.visit_type}_hex_ECG_QC.html"
    )

    plot_bokeh_ecg(
        ecg_data,
        256,
        title=f"ECG Signal for {args.participant_id} - {args.visit_type}",
        output_path=output_path
    )


if __name__ == "__main__":
    main()
