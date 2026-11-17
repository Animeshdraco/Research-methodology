# Software verification report

Verification was run in the project container on 18 November 2026. The data generation, model evaluation, robustness sweep, database seeding, API checks and automated tests were executed as separate stages because the combined convenience script exceeded this environment’s single-command time limit. On a normal local computer, `./run_all.sh` runs those stages in sequence.

| Check | Acceptance criterion | Result |
|---|---|---|
| Synthetic data generation | Seed 42 gives 504 records / 3 devices / 168 hours each | Pass |
| Dataset integrity | Required IDs, sorted timestamps, data-source labels all simulated | Pass (pipeline tests) |
| Forecast model run | Chronological 70/30 split; no target backfill; missing targets excluded | Pass |
| Anomaly experiment | Isolation Forest threshold chosen on training scores only | Pass |
| Robustness sweep | Baseline + 9 perturbation scenarios created deterministically | Pass |
| Seed database | 504 readings inserted; second load skipped all duplicates | Pass |
| API health and device registry | Service state and three registered devices returned | Pass |
| Device authentication | Missing/invalid key rejected; key cannot impersonate another device | Pass |
| Input validation | Out-of-range, NaN and timezone-naive values rejected | Pass |
| Duplicate prevention | Repeated device/timestamp returns HTTP 409 | Pass |
| Alert flow | Threshold event generated; acknowledgement persists | Pass |
| Dashboard/API serving | HTML and OpenAPI endpoints return successfully | Pass |

The latest automated-test run was `python -m pytest backend/tests analysis/tests -q` from the repository root and returned **17 passed, 0 failed**. The data generator, model evaluator and robustness sweep were also executed separately; the robustness output contains 60 scenario/model rows. The SQLite seeder was run twice: the first run inserted 504 records and generated 8 alerts; the second run skipped all 504 duplicates. Direct HTTP checks returned 200 for `/`, `/api/health`, `/api/v1/dashboard?device_id=JW-03` and `/docs`. The three LaTeX entry points (`Main.tex`, `Beamer_Main.tex` and `overleaf/Main.tex`) compiled successfully; the paper PDFs contain five pages and the Beamer PDF contains five slides. Re-run `pytest -q` and the pipeline stages before submission if any source file is changed.

## Scope of verification

These checks validate Python-side software and simulated records in a local environment. They do not validate ESP32 compilation, electrical safety, sensor calibration, physical filtration, microbiological inactivation, heavy-metal removal, energy consumption, ruggedness, network availability at a remote site or compliance of treated water. The ESP32 firmware is source code only in this package.
