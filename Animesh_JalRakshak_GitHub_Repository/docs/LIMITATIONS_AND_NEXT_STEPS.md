# Limitations and next steps

## Current limitations

1. **Synthetic data only.** No sensor was connected and no sample was collected from a real source. The simulated values and membrane removal ratios are assumptions.
2. **Limited duration and coverage.** Three simulated units and seven days cannot represent seasonal changes, mining operations or local groundwater chemistry.
3. **Sensor blind spots.** pH, turbidity, TDS and temperature do not identify pathogens or quantify metals such as arsenic, lead, iron and fluoride. Laboratory analysis is essential.
4. **Purification not validated.** Sediment, activated carbon, UF/RO and UV are a proposed treatment train. Flow, pressure, UV dose, membrane type, maintenance and waste handling still need engineering specification and validation.
5. **Software integration incomplete.** The standalone dashboard and Python experiment pipeline are present, but API ingestion, database persistence and device authentication are not delivered as a live service.
6. **Robustness incomplete.** The current dataset contains a few injected faults. A systematic experiment across noise, missingness and sensor drift rates has not been completed.

## Next steps before any field claim

- Specify a bill of materials, flow rate, pressure limits, power budget, treatment capacity and safe reject-water handling.
- Build the ESP32 node and calibrate each probe against reference instruments.
- Collect paired raw/treated samples with location permissions and a documented sampling protocol.
- Compare sensor outputs with an accredited laboratory for pH, turbidity, TDS, microbiological indicators and relevant metals.
- Verify treatment performance for the likely local contaminants; UV alone does not remove dissolved metals.
- Complete backend/API and device authentication, automated tests and secure deployment.
- Run a preregistered robustness evaluation and test on a later time period or a separately collected site.

Until these steps are complete, the system must be described as a software and system-design prototype, not a validated portable purifier.
