# Physical integration and laboratory validation protocol

This document is a required next-stage test plan. It is not a claim that hardware has been assembled or tested. The provided ESP32 source is an integration template and must be reviewed against the exact sensor datasheets before electrical connection.

## 1. Bench readiness

- Identify exact ESP32 board, pH interface, turbidity sensor, TDS/EC module, temperature probe, ADC board and power supply models. Retain datasheets and serial/batch identifiers.
- Check sensor output voltage range and ADC input common-mode limits. Add suitable conditioning/protection; do not connect an unknown 5 V sensor output directly to ESP32/ADC inputs.
- Verify common ground, I2C address, supply current, polarity, enclosure ingress protection and separation of low-voltage sensor electronics from mains/UV equipment.
- Confirm the selected treatment train with source-water analysis. UF is not an assumed substitute for dissolved-solids or dissolved-metal removal. Select RO or contaminant-specific media only after a laboratory panel.

## 2. Probe calibration

| Channel | Minimum calibration evidence |
|---|---|
| pH | At least two traceable buffer solutions bracketing the expected range; slope/intercept; temperature; date; repeatability |
| Turbidity | Traceable reference standards covering the expected NTU range; clean-cell procedure; repeatability |
| TDS/EC | Certified conductivity standard; compensation method; reference temperature; calibration factor |
| Temperature | Reference thermometer comparison at two or more points; probe offset |

Record raw voltage/counts and converted units. Put coefficients in firmware only after the calibration report is reviewed. The firmware defaults intentionally prevent transmission while pH/turbidity coefficients are zero. Validate the TDS polynomial and temperature compensation for the actual probe module; do not assume a generic coefficient applies to all sensors.

## 3. API integration acceptance

1. Replace the development device key with a unique strong key; configure a trusted server certificate and HTTPS endpoint.
2. Confirm the ESP32 obtains UTC via NTP and sends an ISO-8601 timestamp.
3. Send one calibrated reading with `data_source=hardware`; verify HTTP 201 and the stored record.
4. Send the same timestamp again; verify HTTP 409.
5. Send an out-of-range value; verify validation rejection and no database insert.
6. Disconnect Wi-Fi and verify that the firmware does not mislabel missing/failed samples as valid measurements. Decide whether and how to buffer locally before longer tests.
7. Compare each channel with a reference instrument over at least 30 paired observations across the anticipated measurement range; report bias, MAE/RMSE and uncertainty.

## 4. Water treatment and laboratory study

- Collect raw and treated paired samples at documented sites and times using a written sampling protocol and chain-of-custody labels. Obtain permissions and protect community identities.
- Have a competent/accredited laboratory measure microbiological indicators and relevant mining-related chemical constituents (for example iron, manganese, arsenic, lead, fluoride, nitrate, hardness, sulphate and other site-specific contaminants). Sensor TDS is not a substitute for a chemical panel.
- Verify membrane rejection and recovery, reject-water handling, turbidity after pretreatment, UV intensity/dose at actual flow, UV lamp ageing and interlocks.
- Test multiple replicates and operating conditions, including filter ageing, flow changes and power interruptions. Compare pre-/post-treatment against the applicable amended IS 10500 and current WHO risk-management guidance.
- Do not provide drinking-water safety claims until independent laboratory results, process validation and a supervised field study support them.

## Current evidence status

| Item | Status in this archive |
|---|---|
| Software API, SQLite persistence, dashboard and rules | Implemented and local tests passed |
| Synthetic analysis and robustness scripts | Reproducible on generated data |
| ESP32 firmware source | Written integration template; not compiled or flashed |
| Physical sensors and purifier train | Not supplied / not assembled in this session |
| Calibration certificates | Not available |
| Real-water / laboratory results | Not collected |
| Field usability, energy and connectivity evaluation | Not conducted |
