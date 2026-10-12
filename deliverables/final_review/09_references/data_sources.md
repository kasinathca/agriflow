# Data sources

- Government of India OGD / AGMARKNET daily mandi prices:
  https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi
- CEDA Agri Market API documentation: https://api.ceda.ashoka.edu.in/documentation/
  - CEDA / Ashoka University is the curated access route used here.
  - AGMARKNET / Directorate of Marketing & Inspection is the underlying government producer.
- NASA POWER Daily API: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
- geoBoundaries API and gbOpen ADM1 boundaries: https://www.geoboundaries.org/api.html
- IMD statewise rainfall reference: https://mausam.imd.gov.in/api/statewise_rainfall_api.php

The current exploratory evidence uses only authenticated CEDA/AGMARKNET REAL observations.
No DEMO observation is included. The source is not yet treated as paper-final because the
statewide download, coordinates, weather coverage and final empirical freeze are incomplete.
