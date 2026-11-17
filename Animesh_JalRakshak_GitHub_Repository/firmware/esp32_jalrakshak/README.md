# ESP32 sensor-node integration pack (bench-ready template)

This firmware source is **not represented as hardware-tested**. The exact probe models, ADC interface boards, calibration constants, trusted TLS certificate and NTP time source must be selected and verified before field use. The prototype API accepts hardware-origin records only when an authenticated device sends them; this repo currently includes only simulated readings.

## Suggested bench bill of materials

- ESP32 DevKit development board
- Two ADS1115 16-bit I2C ADC boards (addresses 0x48 and 0x49) for six analog channels across raw and purified water lines
- Two pH probe/interface modules, two turbidity probe/interface modules and two TDS/conductivity modules
- Two waterproof DS18B20 temperature probes plus 4.7 kOhm pull-up resistor
- Appropriate regulated low-voltage supply, enclosure, strain relief, connectors and probe holders
- Voltage conditioning/over-voltage protection selected from each sensor module's output specification

This is a component-level planning list, not a validated bill of materials. Confirm probe voltage ranges, supply requirements, ADC input limits, sensor compatibility and chemical resistance against the actual module datasheets. Do not connect a 5 V analog output directly to an ADC input unless the electrical limits and conditioning are verified. Keep mains wiring and UV power electronics outside the sensor prototype and use a qualified enclosure and interlock design.

## Provisional wiring map

| Interface | ESP32 | Device |
|---|---|---|
| I2C SDA/SCL | GPIO 21 / 22 | Both ADS1115 boards |
| ADS1115 address | — | Raw 0x48, purified 0x49 |
| Temperature bus | GPIO 4 | Both DS18B20 sensors; 4.7 kOhm pull-up to 3.3 V |
| Raw ADC | ADS raw A0/A1/A2 | pH / turbidity / TDS conditioned outputs |
| Treated ADC | ADS purified A0/A1/A2 | pH / turbidity / TDS conditioned outputs |

The ADS1115 boards must share ground with the ESP32 and use safe input conditioning. Verify actual board address straps before powering. Do not treat the provisional map as a substitute for the electrical design of the exact modules.

## Calibration required before firmware activation

1. Record sensor manufacturer, model, serial/batch and supply voltage.
2. Calibrate pH with at least two certified buffer solutions that bracket the expected operating range; store slope/intercept and calibration date.
3. Calibrate turbidity against traceable reference standards across the expected NTU range.
4. Calibrate TDS/EC with a reference conductivity solution and record temperature compensation method.
5. Compare both temperature probes against a reference thermometer.
6. Put the calibrated coefficients into `src/main.cpp`; make sure the API URL uses HTTPS, install the genuine server CA in `src/secrets.h`, supply an NTP-derived ISO-8601 UTC timestamp, and issue a distinct API key per node.
7. Run the integration test in `docs/HARDWARE_AND_LAB_VALIDATION.md` before collecting field water.

`secrets.example.h` is a template. Copy it to `src/secrets.h` and never commit the real Wi-Fi password, API key or certificate bundle. The current sketch intentionally blocks transmission while calibration coefficients remain unset.
