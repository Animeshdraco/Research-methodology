# Simulated dataset dictionary

File: `analysis/data/simulated_readings.csv`  
Rows: 504  
Devices: 3  
Sampling interval: one hour  
Generator seed: 42  
Time range: seven simulated days per device

| Column | Meaning | Unit / type |
|---|---|---|
| `device_id` | Simulated unit identifier (`JW-01` to `JW-03`) | string |
| `district` | Illustrative area label | string |
| `timestamp` | Generated observation time | UTC timestamp |
| `hour_index` | Hour within the generated week | integer |
| `data_source` | Always `simulated` in this release | categorical |
| `raw_ph` | Simulated pH before treatment | pH units |
| `raw_turbidity_ntu` | Simulated raw-water turbidity | NTU |
| `raw_tds_mg_l` | Simulated raw-water total dissolved solids | mg/L |
| `raw_temp_c` | Simulated raw-water temperature | °C |
| `purified_ph` | Simulated pH after the assumed treatment train | pH units |
| `purified_turbidity_ntu` | Simulated treated-water turbidity | NTU |
| `purified_tds_mg_l` | Simulated treated-water TDS; missing for injected dropout rows | mg/L |
| `purified_temp_c` | Simulated treated-water temperature | °C |
| `membrane_removal_assumption` | Assumed TDS removal ratio used by the generator | fraction |
| `dropout_flag` | 1 when a simulated TDS reading is missing | 0/1 |
| `anomaly_type` | Injected event label, or `none` | string |
| `anomaly_label` | Ground-truth event flag for scoring only | 0/1 |

## Injected scenarios

- JW-01: six-hour raw-turbidity surge and a stuck pH sensor segment.
- JW-02: a TDS drift segment and a short TDS dropout segment.
- JW-03: gradual reduction in the assumed membrane removal ratio.

The unit names are illustrative, not coordinates or verified sample locations. The event labels are known because the generator created them; they are not independently verified contamination labels.
