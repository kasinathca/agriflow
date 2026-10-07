# Data Source Register

Checked/reverified for project planning on 2026-10-06. External interfaces can change; connectors therefore fail explicitly and raw snapshots should be retained.

| Source | Role in AgriFlow | Verified interface / reference | Key limitation |
|---|---|---|---|
| Government of India OGD / AGMARKNET | Official daily mandi min/max/modal prices | `https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070` | Requires free API key; daily administrative reporting can be sparse/delayed. |
| OGD catalog page | Dataset provenance and publisher metadata | `https://data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi` (page showed update date 2026-09-18 when rechecked) | Catalog metadata is not a historical bulk-analysis API by itself. |
| CEDA Agri Market Data | Historical AGMARKNET analytical access, including price/quantity endpoints | Swagger lists `/agmarknet/commodities`, `/geographies`, `/markets`, `/prices`, `/quantities`; client targets `https://api.ceda.ashoka.edu.in/v1` | Credential/rate limits can change; resumable checkpoints and CSV import are retained as stable fallbacks. |
| NASA POWER | Historical daily gridded rainfall/temperature | `https://power.larc.nasa.gov/docs/services/api/temporal/daily/` | Grid-cell weather is not a mandi weather-station observation. |
| India Meteorological Department | Official Indian rainfall reference/current state/district rainfall | `https://mausam.imd.gov.in/api/statewise_rainfall_api.php` | Historical bulk data may require IMD data-supply procedures. |
| NIC / Bharat Maps | India state/UT boundary GeoJSON | `https://mapservice.gov.in/gismapservice/rest/services/BharatMapService/Admin_Boundary_District/MapServer/0` | Network service can be unavailable; cache after a successful fetch. |
| Nominatim / OpenStreetMap | One-time market/district coordinate resolution | `https://nominatim.openstreetmap.org/` | Public service must be used slowly and cached; district fallbacks are approximate. |
| PIB, Ministry of Agriculture & Farmers Welfare | Contextual AGMARKNET deployment evidence | Press release dated 2025-12-16 reports 4,367 mandis linked at that time | Context only; not used as an analytical observation source. |

## Source precedence
1. Keep source records and provenance intact.
2. Prefer official Government of India observations for current data.
3. Use CEDA as a cleaned historical access layer over AGMARKNET, not as an independent market-data-generating authority.
4. Never merge DEMO fixtures into REAL observations.
5. Record retrieval date and configuration for every final-paper run.


## Phase 3 source additions / policy notes
### NASA POWER
- Daily API: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
- API request guidance and meteorology resolution: https://power.larc.nasa.gov/docs/tutorials/service-data-request/api/
- Use: historical gridded precipitation and temperature; meteorology is approximately 0.5° × 0.625° source resolution.

### geoBoundaries
- API: https://www.geoboundaries.org/api.html
- Product: gbOpen India ADM1
- Licence: CC BY 4.0; attribution required.
- Use: reproducible open vector state-boundary fallback for visualization.

### NIC/BharatMaps
- Portal: https://mapservice.gov.in/
- Use: Indian government geospatial reference when endpoint/access is available. The BharatMaps FAQ/SOP indicates institutional authorization restrictions for GIS services, so AgriFlow does not assume unrestricted production access.

### OpenStreetMap Foundation Nominatim
- Policy: https://operations.osmfoundation.org/policies/nominatim/
- Use: optional small one-time coordinate validation only. Public bulk geocoding is discouraged; AgriFlow requires explicit policy acknowledgement, caching, throttling and a small request cap.

## Phase 5 authority-tier policy
- `PRIMARY_OFFICIAL`: direct Government of India OGD/AGMARKNET API or retained official OGD export.
- `CURATED_OFFICIAL_DERIVED`: CEDA Agri-Market API/portal data derived from AGMARKNET.
- `SECONDARY_MIRROR`: third-party archives that reproduce official feeds; bootstrap/exploration only.
- `USER_SUPPLIED`: generic local files without source-specific verification; exploration only.

The CEDA Data Portal states that its Agri-Market tool provides prices and quantities for 300+ agricultural commodities from 2,700+ mandis and spans data from 2000 onward. The official CEDA API registration page provides an email/OTP key-generation flow. The Government OGD help page states that registered users can generate API keys. These routes remain the preferred empirical acquisition paths; undocumented frontend endpoints and anonymous scraping are intentionally not required by AgriFlow.
