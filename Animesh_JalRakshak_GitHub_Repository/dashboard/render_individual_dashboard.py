"""Render a static individual dashboard capture from the shipped synthetic CSV."""
from pathlib import Path
import argparse
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import math

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "analysis" / "data" / "simulated_readings.csv"
W, H = 1600, 1120
BG = "#eef3f5"
INK = "#17333d"
MUTE = "#647b84"
LINE = "#d9e3e7"
CARD = "#ffffff"
BRAND = "#0f7f86"
BRAND_SOFT = "#e0f1f1"
OK = "#237a4b"
OK_SOFT = "#e2f3e8"
WARN = "#9b6500"
WARN_SOFT = "#fbf0d8"
RED = "#b3392a"
RED_SOFT = "#f9e4e0"
RAW = "#bb8548"


def font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for f in candidates:
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def rr(draw, box, radius=16, fill=CARD, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def text(draw, xy, value, size=18, fill=INK, bold=False):
    draw.text(xy, str(value), font=font(size, bold), fill=fill)


def chart_panel(img, box, rows, series_a, series_b, title, unit, limit=None):
    x1, y1, x2, y2 = box
    d = ImageDraw.Draw(img)
    rr(d, box, 16, CARD, LINE)
    text(d, (x1 + 24, y1 + 18), title, 22, INK, True)
    text(d, (x1 + 24, y1 + 52), f"Last 48 hourly readings · {unit}", 14, MUTE)
    plot = (x1 + 58, y1 + 100, x2 - 28, y2 - 58)
    px1, py1, px2, py2 = plot
    vals = list(series_a) + list(series_b)
    if limit is not None:
        vals.append(limit)
    vmin = min(vals)
    vmax = max(vals)
    pad = max((vmax - vmin) * 0.15, 0.05)
    vmin -= pad
    vmax += pad
    # horizontal grid and y labels
    for i in range(5):
        yy = py2 - i * (py2 - py1) / 4
        d.line((px1, yy, px2, yy), fill="#e7edef", width=1)
        v = vmin + i * (vmax - vmin) / 4
        label = f"{v:.0f}" if unit == "mg/L" else f"{v:.1f}"
        text(d, (x1 + 12, int(yy - 9)), label, 12, MUTE)
    if limit is not None:
        yy = py2 - (limit - vmin) / (vmax - vmin) * (py2 - py1)
        d.line((px1, yy, px2, yy), fill=RED, width=2)
        text(d, (px2 - 130, int(yy - 20)), f"Limit {limit:g}", 12, RED, True)

    def pts(values):
        out = []
        for i, v in enumerate(values):
            xx = px1 + i * (px2 - px1) / max(1, len(values) - 1)
            yy = py2 - (float(v) - vmin) / (vmax - vmin) * (py2 - py1)
            out.append((int(xx), int(yy)))
        return out
    d.line(pts(series_a), fill=RAW, width=3, joint="curve")
    d.line(pts(series_b), fill=BRAND, width=3, joint="curve")
    text(d, (px1, y2 - 34), "48 h ago", 12, MUTE)
    text(d, (px2 - 45, y2 - 34), "Now", 12, MUTE)
    # Legend
    leg_y = y1 + 78
    d.line((x1 + 285, leg_y + 9, x1 + 315, leg_y + 9), fill=RAW, width=4)
    text(d, (x1 + 322, leg_y), "Raw water", 13, MUTE)
    d.line((x1 + 430, leg_y + 9, x1 + 460, leg_y + 9), fill=BRAND, width=4)
    text(d, (x1 + 467, leg_y), "Purified water", 13, MUTE)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--student-name", default="Animesh Giri")
    parser.add_argument("--sap-id", default="590012563")
    parser.add_argument("--device-id", default="JW-03", choices=["JW-01", "JW-02", "JW-03"])
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    output = args.output or (ROOT / "dashboard" / ("JalRakshak_Dashboard_Animesh.jpg" if args.sap_id == "590015167" else f"JalRakshak_Dashboard_{args.sap_id}.jpg"))
    df = pd.read_csv(CSV)
    one = df[df.device_id == args.device_id].sort_values("hour_index")
    last = one.iloc[-1]
    latest_ph = float(last.purified_ph)
    latest_ntu = float(last.purified_turbidity_ntu)
    latest_tds = float(last.purified_tds_mg_l)
    latest_temp = float(last.purified_temp_c)
    status = "Within limits" if (6.5 <= latest_ph <= 8.5 and latest_ntu <= 1 and latest_tds <= 500) else "Caution"

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # Sidebar
    d.rectangle((0, 0, 246, H), fill="#123640")
    text(d, (30, 28), "JalRakshak", 28, "#ffffff", True)
    text(d, (30, 68), "WATER QUALITY MONITOR", 11, "#9ec7ca", True)
    d.line((24, 105, 222, 105), fill="#355761", width=1)
    text(d, (30, 132), "INDIVIDUAL WORKSPACE", 11, "#8fb9bd", True)
    display_name = args.student_name
    name_parts = display_name.split()
    text(d, (30, 160), " ".join(name_parts[:2]), 17, "#ffffff", True)
    text(d, (30, 185), " ".join(name_parts[2:]) or " ", 17, "#ffffff", True)
    text(d, (30, 220), f"SAP ID: {args.sap_id}", 13, "#c0d9db")
    d.line((24, 260, 222, 260), fill="#355761", width=1)
    nav = ["Dashboard", "Analytics", "Devices", "Alerts", "Forecast & anomalies", "Project progress"]
    y = 292
    for i, item in enumerate(nav):
        if i == 0:
            rr(d, (18, y - 10, 228, y + 32), 10, BRAND)
            text(d, (38, y), item, 16, "#ffffff", True)
        else:
            text(d, (38, y), item, 15, "#d1e1e3")
        y += 58
    rr(d, (22, 958, 224, 1088), 12, "#1b4651")
    text(d, (38, 976), "Software prototype", 14, "#ffffff", True)
    text(d, (38, 1005), "100% implemented", 15, "#8de0d9", True)
    text(d, (38, 1033), "Simulated readings only", 11, "#d2e5e6")
    text(d, (38, 1055), "Field validation pending", 11, "#d2e5e6")

    # Header
    text(d, (282, 34), "Water Quality Overview", 30, INK, True)
    text(d, (282, 76), f"{args.student_name}  ·  B.Tech CSE (CCVT), Third Year", 15, MUTE)
    rr(d, (1300, 36, 1555, 73), 18, WARN_SOFT)
    text(d, (1320, 47), "SIMULATED DATA", 13, WARN, True)
    selected_device = one.iloc[0]
    name_by_id = {"JW-01": "Jharia Block Unit · Dhanbad", "JW-02": "Noamundi Mine Village Unit · West Singhbhum", "JW-03": "Patratu Community Unit · Ramgarh"}
    text(d, (282, 112), f"Selected unit: {args.device_id} · {name_by_id[args.device_id]}, Jharkhand", 15, INK, True)
    rr(d, (282, 145, 1555, 205), 12, WARN_SOFT)
    text(d, (305, 160), "Research prototype: all readings shown here are synthetic. This dashboard does not certify drinking-water safety.", 15, WARN, True)
    text(d, (305, 183), "pH, turbidity, TDS and temperature do not detect pathogens or heavy metals; laboratory testing is still required.", 12, MUTE)

    # Status panel + KPI cards
    rr(d, (282, 225, 1555, 330), 14, CARD, LINE)
    status_fill = OK_SOFT if status == "Within limits" else WARN_SOFT
    status_color = OK if status == "Within limits" else WARN
    rr(d, (305, 247, 490, 305), 12, status_fill)
    text(d, (324, 255), status, 21, status_color, True)
    text(d, (324, 282), "for monitored parameters", 12, MUTE)
    text(d, (520, 244), "Purification stages", 14, MUTE, True)
    text(d, (520, 270), "Sediment  →  Carbon  →  UF/RO  →  UV", 17, INK, True)
    text(d, (520, 297), "Stage remaining life is a simulated estimate.", 12, MUTE)
    text(d, (1200, 246), "Current reading", 13, MUTE, True)
    text(d, (1200, 272), f"pH {latest_ph:.2f}  ·  {latest_ntu:.2f} NTU  ·  {latest_tds:.1f} mg/L", 14, INK, True)
    text(d, (1200, 296), f"Temperature {latest_temp:.1f} °C", 12, MUTE)

    kpis = [
        ("pH", f"{latest_ph:.2f}", "Raw: %.2f" % float(last.raw_ph), "Preferred range 6.5–8.5"),
        ("Turbidity", f"{latest_ntu:.2f} NTU", "Raw: %.2f NTU" % float(last.raw_turbidity_ntu), "Preferred limit 1 NTU"),
        ("TDS", f"{latest_tds:.1f} mg/L", "Raw: %.1f mg/L" % float(last.raw_tds_mg_l), "Preferred limit 500 mg/L"),
        ("Temperature", f"{latest_temp:.1f} °C", "Raw: %.1f °C" % float(last.raw_temp_c), "Information only"),
    ]
    x = 282
    for title, val, raw, sub in kpis:
        rr(d, (x, 348, x + 303, 480), 14, CARD, LINE)
        text(d, (x + 20, 365), title, 15, MUTE, True)
        text(d, (x + 20, 394), val, 26, INK, True)
        text(d, (x + 20, 433), raw, 13, MUTE)
        text(d, (x + 20, 455), sub, 12, BRAND)
        x += 318

    # Charts
    last48 = one.tail(48)
    chart_panel(img, (282, 500, 902, 820), last48,
                last48.raw_tds_mg_l.tolist(), last48.purified_tds_mg_l.tolist(),
                "TDS trend", "mg/L", 500)
    chart_panel(img, (920, 500, 1555, 820), last48,
                last48.raw_turbidity_ntu.tolist(), last48.purified_turbidity_ntu.tolist(),
                "Turbidity trend", "NTU", 1)

    # Lower panels
    rr(d, (282, 840, 902, 1088), 14, CARD, LINE)
    text(d, (305, 862), "Purification stage condition", 20, INK, True)
    stages_by_device = {"JW-01": [72, 55, 81, 64], "JW-02": [60, 68, 74, 90], "JW-03": [85, 77, 22, 58]}
    stages = list(zip(["Sediment filter", "Activated carbon", "UF / RO membrane", "UV disinfection"], stages_by_device[args.device_id]))
    yy = 910
    for label, pct in stages:
        text(d, (305, yy), label, 14, INK)
        rr(d, (505, yy + 3, 805, yy + 17), 7, "#e7eef0")
        rr(d, (505, yy + 3, 505 + int(3 * pct), yy + 17), 7, BRAND)
        text(d, (827, yy - 2), f"{pct}%", 13, MUTE, True)
        yy += 42
    text(d, (305, 1064), "Estimated remaining life; inspect when below 30%.", 12, MUTE)

    rr(d, (920, 840, 1555, 1088), 14, CARD, LINE)
    text(d, (944, 862), "Recent simulated alerts", 20, INK, True)
    alerts = [
        ("WARNING", "JW-01 · Turbidity surge", "Peak 2.40 NTU · Inspect sediment stage and sensor calibration", WARN, WARN_SOFT),
        ("WARNING", "JW-03 · Membrane degradation", "Purified TDS rose above the 500 mg/L preferred limit", WARN, WARN_SOFT),
        ("INFO", "JW-02 · TDS sensor dropout", "Three consecutive readings were missing in the test scenario", BRAND, BRAND_SOFT),
    ]
    yy = 908
    for tag, title, note, color, fill in alerts:
        rr(d, (944, yy, 1530, yy + 48), 9, fill)
        text(d, (958, yy + 8), tag, 11, color, True)
        text(d, (1050, yy + 6), title, 14, INK, True)
        text(d, (1050, yy + 27), note, 11, MUTE)
        yy += 58
    text(d, (944, 1070), "Alerts are generated from injected simulator events, not field contamination reports.", 11, MUTE)

    img.save(output, quality=93, optimize=True)
    print(f"Saved {output}")


if __name__ == "__main__":
    main()
