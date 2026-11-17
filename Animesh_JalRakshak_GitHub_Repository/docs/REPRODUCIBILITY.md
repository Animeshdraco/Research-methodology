# Reproducibility notes

## Environment

- Python 3.10+
- Packages in `requirements.txt`: NumPy, pandas, scikit-learn and Matplotlib
- LaTeX: pdfLaTeX with Beamer and standard article packages to rebuild the paper and slides

## Commands

```bash
python -m pip install -r requirements.txt
python analysis/scripts/01_generate_data.py --seed 42
python analysis/scripts/02_evaluate_models.py
```

The output paths are fixed relative to the repository root. The generator is deterministic for a given seed. The evaluation uses `random_state=42` in the random forest and Isolation Forest.

## Split protocol

For every device separately, the first 70% of the ordered hourly sequence is used for fitting and the final 30% is held out. Forecast feature rows use observations available at or before the forecast origin. Predictor gaps are forward-filled only; no later measurement is used to fill an earlier timestamp. Missing TDS target observations are excluded from that target's metric calculation (150 TDS targets remain); turbidity has 153 held-out targets. The persistence baseline uses the latest available reading as the next-hour prediction. Test rows are not used to fit the regression models or select the anomaly score threshold.

## Important interpretation limit

The labels and measurements share the same simulated generator. This can make anomaly detection easier than deployment on noisy and changing field sensors. A chronological split avoids future leakage within the generated records, but it does not create independent field evidence or prove generalisation to a new district.
