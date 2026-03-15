import argparse
import bioread
import pandas as pd
import numpy as np
import os

from bokeh.plotting import figure, output_file, save
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, RangeTool, Span, Label


def plot_bokeh_bp(bp_df, fs, title, output_path, downsample_fs=10, window_seconds=60):
    if bp_df is None or bp_df.empty:
        print("No BP data available.")
        return

    # Full-resolution time for discrete peaks
    full_time = np.arange(len(bp_df)) / fs

    # Downsample continuous signals only
    downsample_factor = max(int(fs / downsample_fs), 1)
    df_down = bp_df.iloc[::downsample_factor].copy().reset_index(drop=True)
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
    # Column indices (robust to changes in names)
    # -------------------------
    raw_idx = 0
    clean_idx = 1
    systolic_idx = 3
    diastolic_idx = 4
    event_idx = bp_df.columns.get_loc("Event_Label") if "Event_Label" in bp_df.columns else None

    # Continuous signals
    p.line("time", bp_df.columns[raw_idx], source=source, legend_label="BP Raw")
    p.line("time", bp_df.columns[clean_idx], source=source, line_width=2, legend_label="BP Clean", line_color="green")

    # Peaks
    systolic_mask = bp_df.iloc[:, systolic_idx] != 0
    diastolic_mask = bp_df.iloc[:, diastolic_idx] != 0

    p.scatter(
        full_time[systolic_mask],
        bp_df.loc[systolic_mask, bp_df.columns[clean_idx]],
        size=8,
        marker="triangle",
        color="red",
        legend_label="Systolic Peaks"
    )

    p.scatter(
        full_time[diastolic_mask],
        bp_df.loc[diastolic_mask, bp_df.columns[clean_idx]],
        size=8,
        marker="circle",
        color="blue",
        legend_label="Diastolic Peaks"
    )

    # Event labels
    if event_idx is not None:
        event_mask = bp_df.iloc[:, event_idx].notna() & (bp_df.iloc[:, event_idx].astype(str).str.strip() != "")
        y_top = bp_df.iloc[:, clean_idx].min()
        for t, label_text in zip(full_time[event_mask], bp_df.iloc[event_mask, event_idx]):
            vline = Span(location=t, dimension="height", line_color="red", line_dash="dashed", line_width=1)
            p.add_layout(vline)
            label = Label(x=t, y=y_top, text=str(label_text), angle=np.pi/2, text_font_size="8pt", text_color="green")
            p.add_layout(label)

    # Formatting
    p.legend.click_policy = "hide"
    p.xaxis.axis_label = "Time (seconds)"
    p.yaxis.axis_label = "BP"
    p.x_range.start = 0
    p.x_range.end = min(window_seconds, full_time[-1])

    # Range tool
    select = figure(height=130, width=1000, y_range=p.y_range, tools="", toolbar_location=None)
    select.line("time", bp_df.columns[clean_idx], source=source, line_color="darkgreen")
    range_tool = RangeTool(x_range=p.x_range)
    range_tool.overlay.fill_alpha = 0.3
    range_tool.overlay.fill_color = "gray"
    select.add_tools(range_tool)
    select.x_range.start = 0
    select.x_range.end = full_time[-1]

    layout = column(p, select)
    output_file(output_path)
    save(layout)
    print(f"Saved interactive BP plot to {output_path}")


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

    bp_data = pd.read_csv(args.input_file, low_memory=False)

    output_path = os.path.join(
        args.output_dir,
        f"{args.participant_id}_{args.visit_type}_acq_BP_QC.html"
    )

    plot_bokeh_bp(
        bp_data,
        sampling_rate,
        title=f"BP Signal for {args.participant_id} - {args.visit_type}",
        output_path=output_path
    )


if __name__ == "__main__":
    main()
