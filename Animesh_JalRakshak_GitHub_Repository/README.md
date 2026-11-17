# JalRakshak — Smart Water Purification and Quality Monitoring

**Individual repository owner:** Animesh Giri (SAP ID 590012563)  
**Group research authors:** Nischal Kumar Singhania and Animesh Giri  
**Programme:** B.Tech CSE (CCVT), Third Year

JalRakshak is a software prototype and research study for a low-cost water-quality monitoring and purification concept for rural and mining-affected areas of Jharkhand. The shared research is accompanied by this student's own dashboard view and repository copy.

> **Evidence boundary:** The included software prototype was run and tested against seeded synthetic readings. The ESP32 firmware is an integration template, not a physically validated sensor node. No real-water or laboratory measurements are included. The project does not certify drinking-water safety.

## Repository contents

- `backend/`: FastAPI application, authenticated device ingestion, validation, SQLite persistence, demo seeding and API tests.
- `dashboard/`: this student's individually labelled interactive HTML dashboard and screenshot-rendering script. The personal dashboard JPG is intentionally supplied as a separate submission file and is not included in this GitHub package.
- `analysis/`: deterministic data generation, forecasting, anomaly detection, robustness experiments, results, figures and tests.
- `firmware/`: ESP32 PlatformIO integration template and safe configuration example.
- `paper/`, `overleaf/`, `presentation/`: LaTeX source and figures for the paper and five-slide Beamer deck.
- `docs/`: API reference, data dictionary, local setup, reproducibility, data availability, hardware/lab acceptance checklist and submission guides.
- `JalRakshak_Research_Paper.pdf`, `JalRakshak_Beamer_5_Slides.pdf`: compiled outputs.

## Run locally

Requirements: Python 3.10 or later.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python analysis/scripts/01_generate_data.py --seed 42
python analysis/scripts/02_evaluate_models.py
python analysis/scripts/03_robustness_sweep.py
python backend/seed_demo.py --replace
python -m pytest backend/tests analysis/tests -q
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/` for the dashboard and `http://127.0.0.1:8000/docs` for API documentation. For Windows and detailed steps, see `docs/LOCAL_RUN.md`. `run_all.sh` runs the data pipeline, seeds the local database and executes tests on macOS/Linux environments with Bash.

## Reproducible research results

The generator uses seed 42 and creates 504 simulated readings (three illustrative units × 168 hourly records). The chronological forecast evaluation compares persistence, linear regression and random forest. In the reported run, persistence had lower one-hour errors than both regression models for TDS and turbidity. Isolation Forest achieved precision 0.796, recall 0.582 and F1 0.672 on the held-out synthetic anomaly set. Ten perturbation conditions examine noise, missing observations and drift. Full metrics and scripts are under `analysis/`.

The results demonstrate software behaviour on simulated data only. They are not field accuracy or purifier efficacy results.

## Personal dashboard

This repository copy is labelled for **Animesh Giri** and opens with device **JW-03** selected. The second group member has a separate repository package with their own identity and initial device selection. To generate a dashboard screenshot locally, follow the command in `docs/SUBMISSION_CHECKLIST.md` or run the renderer script with the student name, SAP ID and device arguments. The required JPG is submitted separately, not in this ZIP.

## Individual contribution

The approximately 200-word individual contribution statement is intentionally submitted separately and is not included in this repository package.

## Publishing this repository

1. Extract this ZIP.
2. Create a new empty GitHub repository under this student's own account.
3. Upload the **contents** of the extracted `Animesh_JalRakshak_GitHub_Repository` folder (not the outer ZIP file).
4. Commit the files to the repository's default branch.
5. Copy the resulting repository URL into the course submission form.

Do not upload `.env` or local database files. `.env.example` is safe to publish; use a new secret API key for any real device.
