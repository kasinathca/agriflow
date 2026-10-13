import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const workspaceDir = "C:\\Users\\kasin\\Projects\\DATA SCIENCE PROJECT";
const SKILL_DIR = "C:\\Users\\kasin\\.codex\\plugins\\cache\\openai-primary-runtime\\presentations\\26.1011.11113\\skills\\presentations";
const RUNTIME_PYTHON = "C:\\Users\\kasin\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe";
const buildDir = path.join(workspaceDir, ".presentation-build");
const renderDir = path.join(buildDir, "rendered");
const outputDir = path.join(workspaceDir, "deliverables", "final_review");
const FINAL_PPTX = path.join(outputDir, "AgriFlow_Final_Review.pptx");
const FONT = "Times New Roman";
const NAVY = "#17365D";
const GREEN = "#2F6B4F";
const PALE = "#EEF4F0";
const GRID = "#D8DEE6";
const DARK = "#20252B";
const MUTED = "#5E6875";
const WHITE = "#FFFFFF";

const artifactToolPath = "C:\\Users\\kasin\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\node\\node_modules\\@oai\\artifact-tool\\dist\\artifact_tool.mjs";
process.env.RUNTIME_NODE_MODULES = "C:\\Users\\kasin\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\node\\node_modules";
const { Presentation, PresentationFile } = await import(pathToFileURL(artifactToolPath).href);

const utils = await import(pathToFileURL(path.join(SKILL_DIR, "container_tools", "artifact_tool_utils.mjs")).href);
const { applyPresentationChartFont, makeNativeBulletParagraphs, finalizePresentation } = utils;

function parseCsv(text) {
  const rows = [];
  let row = [], value = "", quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i], next = text[i + 1];
    if (quoted) {
      if (c === '"' && next === '"') { value += '"'; i++; }
      else if (c === '"') quoted = false;
      else value += c;
    } else if (c === '"') quoted = true;
    else if (c === ',') { row.push(value); value = ""; }
    else if (c === '\n') { row.push(value.replace(/\r$/, "")); rows.push(row); row = []; value = ""; }
    else value += c;
  }
  if (value.length || row.length) { row.push(value); rows.push(row); }
  const headers = rows.shift();
  return rows.filter(r => r.length === headers.length).map(r => Object.fromEntries(headers.map((h, i) => [h, r[i]])));
}

async function csv(relative) {
  return parseCsv(await fs.readFile(path.join(workspaceDir, relative), "utf8"));
}

function addTextbox(slide, text, left, top, width, height, options = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position: { left, top, width, height },
    fill: options.fill ?? "none",
    line: options.line ?? { style: "solid", fill: "none", width: 0 },
  });
  shape.text = text;
  shape.text.style = {
    typeface: FONT,
    fontSize: options.fontSize ?? 24,
    bold: options.bold ?? false,
    color: options.color ?? DARK,
    alignment: options.alignment ?? "left",
    verticalAlignment: options.verticalAlignment ?? "top",
    autoFit: "shrinkText",
  };
  return shape;
}

function addBox(slide, text, left, top, width, height, options = {}) {
  const shape = slide.shapes.add({
    geometry: options.geometry ?? "rect",
    position: { left, top, width, height },
    fill: options.fill ?? WHITE,
    line: { style: "solid", fill: options.lineColor ?? GRID, width: options.lineWidth ?? 1 },
  });
  shape.text = text;
  shape.text.style = {
    typeface: FONT,
    fontSize: options.fontSize ?? 21,
    bold: options.bold ?? false,
    color: options.color ?? DARK,
    alignment: options.alignment ?? "center",
    verticalAlignment: "middle",
    autoFit: "shrinkText",
  };
  return shape;
}

function addBullets(slide, items, left, top, width, height, options = {}) {
  const box = slide.shapes.add({
    geometry: "textbox",
    position: { left, top, width, height },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  box.text = makeNativeBulletParagraphs(items, {
    marginLeftPoints: options.marginLeftPoints ?? 20,
    hangingPoints: options.hangingPoints ?? 10,
    spaceAfterPoints: options.spaceAfterPoints ?? 8,
  });
  box.text.style = {
    typeface: FONT,
    fontSize: options.fontSize ?? 24,
    color: options.color ?? DARK,
    autoFit: "shrinkText",
  };
  return box;
}

function addHeader(slide, title, number) {
  slide.background.fill = WHITE;
  addTextbox(slide, title, 62, 34, 1080, 48, { fontSize: 42, bold: true, color: NAVY });
  slide.shapes.add({ geometry: "rect", position: { left: 62, top: 92, width: 1156, height: 3 }, fill: NAVY, line: { style: "solid", fill: NAVY, width: 0 } });
  addTextbox(slide, String(number).padStart(2, "0"), 1168, 670, 48, 24, { fontSize: 16, color: MUTED, alignment: "right" });
}

function addNote(slide, text, left = 62, top = 640, width = 1080) {
  addTextbox(slide, text, left, top, width, 34, { fontSize: 16, color: MUTED });
}

function styleTable(table, fontSize = 18) {
  table.borders.assign({ style: "solid", fill: GRID, width: 1 });
  table.cells.block({ row: 0, column: 0, rowCount: 1, columnCount: table.columns.length }).assign({
    fill: NAVY,
    textStyle: { typeface: FONT, fontSize, bold: true, color: WHITE },
    margins: { left: 8, right: 8, top: 5, bottom: 5 },
  });
  if (table.rows.length > 1) {
    table.cells.block({ row: 1, column: 0, rowCount: table.rows.length - 1, columnCount: table.columns.length }).assign({
      textStyle: { typeface: FONT, fontSize, color: DARK },
      margins: { left: 8, right: 8, top: 4, bottom: 4 },
    });
  }
  for (let row = 0; row < table.rows.length; row++) {
    for (let column = 0; column < table.columns.length; column++) {
      table.getCell(row, column).text.style = {
        typeface: FONT,
        fontSize,
        bold: row === 0,
        color: row === 0 ? WHITE : DARK,
        autoFit: "shrinkText",
      };
    }
  }
  return table;
}

function chartFont(chart, size = 16) {
  applyPresentationChartFont(chart, { fontFamily: FONT, fontSize: size });
  return chart;
}

const comparison = await csv("deliverables/final_review/forecasting/model_comparison.csv");
const predictions = await csv("deliverables/final_review/forecasting/test_predictions.csv");
const forecasts = await csv("deliverables/final_review/forecasting/latest_forecasts.csv");
const marketCoverage = await csv("deliverables/final_review/01_dataset/market_coverage.csv");
const panel = await csv("data/processed/market_daily.csv");
const metadata = JSON.parse(await fs.readFile(path.join(workspaceDir, "deliverables/final_review/forecasting/selected_model.json"), "utf8"));
const selected = metadata.selected_model;
const selectedRow = comparison.find(row => row.model === selected);
const persistenceRow = comparison.find(row => row.model === "M0 Persistence");
const representative = forecasts.find(row => row.market === "Ahmednagar") ?? forecasts[0];

const monthlyMap = new Map();
for (const row of panel) {
  const month = row.date.slice(0, 7);
  if (!monthlyMap.has(month)) monthlyMap.set(month, []);
  monthlyMap.get(month).push(Number(row.modal_price));
}
const monthly = [...monthlyMap.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([month, values]) => {
  values.sort((a, b) => a - b);
  const mid = Math.floor(values.length / 2);
  const median = values.length % 2 ? values[mid] : (values[mid - 1] + values[mid]) / 2;
  return { month, median };
});

const selectedPredictions = predictions.filter(row => row.model === selected);
const counts = new Map();
for (const row of selectedPredictions) counts.set(row.market_id, (counts.get(row.market_id) ?? 0) + 1);
const focusMarketId = [...counts.entries()].sort((a, b) => b[1] - a[1])[0][0];
const focusPredictions = selectedPredictions.filter(row => row.market_id === focusMarketId).sort((a, b) => a.date.localeCompare(b.date));
const sampledPredictions = selectedPredictions.filter((_, index) => index % Math.max(1, Math.floor(selectedPredictions.length / 120)) === 0).slice(0, 120);
const topMarkets = [...marketCoverage].sort((a, b) => Number(b.observations) - Number(a.observations)).slice(0, 10);

const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });
presentation.theme.defaultFont = FONT;

// 1 - Title
{
  const slide = presentation.slides.add();
  slide.background.fill = WHITE;
  slide.shapes.add({ geometry: "rect", position: { left: 0, top: 0, width: 28, height: 720 }, fill: GREEN, line: { style: "solid", fill: GREEN, width: 0 } });
  addTextbox(slide, "AgriFlow: Agricultural Market Price Analysis and Forecasting", 88, 124, 1090, 126, { fontSize: 52, bold: true, color: NAVY });
  addTextbox(slide, "Spatiotemporal Market Integration and Machine Learning-Based Price Prediction", 92, 270, 1040, 54, { fontSize: 27, color: DARK });
  slide.shapes.add({ geometry: "rect", position: { left: 92, top: 346, width: 1020, height: 2 }, fill: GRID, line: { style: "solid", fill: GRID, width: 0 } });
  addTextbox(slide, "CSI3004 Data Science Programming\nVellore Institute of Technology, Vellore", 92, 382, 520, 78, { fontSize: 23, color: MUTED });
  addTextbox(slide, "Kasinath C A - 24MID0124\nKamal Nayan C S - 24MID0189", 692, 382, 430, 78, { fontSize: 23, color: DARK });
  addTextbox(slide, "Final Review | 13 October 2026", 92, 628, 420, 30, { fontSize: 18, color: MUTED });
}

// 2 - Problem
{
  const slide = presentation.slides.add(); addHeader(slide, "Problem Statement", 2);
  addBullets(slide, [
    "Wholesale Onion prices vary sharply across markets and seasons.",
    "Markets report on uneven dates, which complicates direct comparison.",
    "Analysts need both descriptive market evidence and a cautious short-horizon forecast.",
    "Intended users include market analysts, agricultural researchers and other stakeholders.",
  ], 70, 126, 570, 360, { fontSize: 25, spaceAfterPoints: 12 });
  addBox(slide, "Uneven market reports", 710, 145, 390, 76, { fill: PALE, lineColor: GREEN, bold: true, fontSize: 24 });
  addBox(slide, "Validated historical panel", 710, 267, 390, 76, { fill: WHITE, lineColor: NAVY, bold: true, fontSize: 24 });
  addBox(slide, "Analysis plus next-report forecast", 710, 389, 390, 86, { fill: PALE, lineColor: GREEN, bold: true, fontSize: 24 });
  addTextbox(slide, "1", 660, 164, 32, 32, { fontSize: 22, bold: true, color: GREEN, alignment: "center" });
  addTextbox(slide, "2", 660, 286, 32, 32, { fontSize: 22, bold: true, color: GREEN, alignment: "center" });
  addTextbox(slide, "3", 660, 416, 32, 32, { fontSize: 22, bold: true, color: GREEN, alignment: "center" });
  addNote(slide, "The predictive task estimates the next reported observation, not an exact next-day or current market price.");
}

// 3 - Objectives
{
  const slide = presentation.slides.add(); addHeader(slide, "Objectives", 3);
  const objectives = [
    ["01", "Acquire and clean historical market prices", "7,794 validated market-day records"],
    ["02", "Characterize trends and reporting coverage", "Existing exploratory dashboard"],
    ["03", "Analyze integration and price transmission", "Lead-lag, network and geography modules"],
    ["04", "Develop and compare forecasting models", "Six candidates on a common temporal cohort"],
    ["05", "Deliver a reproducible analytical dashboard", "Offline training, saved inference and evidence"],
  ];
  objectives.forEach((item, i) => {
    const top = 126 + i * 96;
    addTextbox(slide, item[0], 75, top + 8, 62, 48, { fontSize: 30, bold: true, color: GREEN, alignment: "center" });
    addTextbox(slide, item[1], 160, top, 570, 38, { fontSize: 25, bold: true, color: NAVY });
    addTextbox(slide, item[2], 160, top + 39, 900, 30, { fontSize: 20, color: MUTED });
    slide.shapes.add({ geometry: "rect", position: { left: 160, top: top + 75, width: 940, height: 1 }, fill: GRID, line: { style: "solid", fill: GRID, width: 0 } });
  });
}

// 4 - Architecture
{
  const slide = presentation.slides.add(); addHeader(slide, "Proposed Solution and Architecture", 4);
  const stages = ["Historical\nmarket data", "Validation", "Preprocessing", "Feature\nengineering", "Model\ntraining", "Temporal\nevaluation", "Model\nselection", "Forecasting\ndashboard"];
  stages.forEach((label, i) => addBox(slide, label, 58 + i * 148, 172, 126, 92, { fill: i % 2 ? WHITE : PALE, lineColor: i === 7 ? GREEN : NAVY, fontSize: 19, bold: i === 0 || i === 7 }));
  addTextbox(slide, "1", 108, 286, 28, 28, { fontSize: 18, bold: true, color: MUTED, alignment: "center" });
  stages.slice(1).forEach((_, i) => addTextbox(slide, String(i + 2), 256 + i * 148, 286, 28, 28, { fontSize: 18, bold: true, color: MUTED, alignment: "center" }));
  addBox(slide, "Existing analytical branch", 144, 390, 260, 62, { fill: WHITE, lineColor: GREEN, bold: true, fontSize: 22 });
  addBox(slide, "Trends and coverage", 452, 365, 228, 54, { fill: PALE, lineColor: GRID, fontSize: 20 });
  addBox(slide, "Lead-lag and network", 452, 433, 228, 54, { fill: PALE, lineColor: GRID, fontSize: 20 });
  addBox(slide, "Geography and integration", 724, 365, 250, 54, { fill: PALE, lineColor: GRID, fontSize: 20 });
  addBox(slide, "Quality and research status", 724, 433, 250, 54, { fill: PALE, lineColor: GRID, fontSize: 20 });
  addNote(slide, "All normal execution paths use local files. No cloud service, live market API or training inside dashboard callbacks is required.");
}

// 5 - Dataset
{
  const slide = presentation.slides.add(); addHeader(slide, "Dataset Description", 5);
  const values = [
    ["Field", "Observed scope"],
    ["Source", "CEDA Agri Market Data / AGMARKNET"],
    ["Commodity", "Onion"],
    ["Coverage", "Maharashtra; 4 districts; 25 markets"],
    ["Rows", "8,499 raw; 7,794 processed market-days"],
    ["Dates", "01 Jan 2023 to 30 Oct 2025"],
    ["Target and unit", "modal_price; INR per quintal"],
  ];
  const table = slide.tables.add({ rows: values.length, columns: 2, left: 62, top: 126, width: 570, height: 450, values, columnWidths: [170, 400] });
  styleTable(table, 18);
  const chart = slide.charts.add("bar", {
    position: { left: 675, top: 135, width: 530, height: 405 },
    categories: topMarkets.map(row => row.market),
    series: [{ name: "Market-day observations", values: topMarkets.map(row => Number(row.observations)), fill: GREEN }],
    barOptions: { direction: "bar", grouping: "clustered", gapWidth: 35 },
    hasLegend: false,
    xAxis: { title: "Processed observations", majorGridlines: { style: "solid", fill: GRID, width: 1 } },
    yAxis: { textStyle: { fontSize: 14 } },
  });
  chartFont(chart, 14);
  addNote(slide, "Experimental evidence covers Maharashtra only. The India map remains a visualization capability, not a claim of national experimental coverage.");
}

// 6 - Preprocessing
{
  const slide = presentation.slides.add(); addHeader(slide, "Data Preprocessing and Exploratory Analysis", 6);
  addBullets(slide, [
    "Parsed dates and enforced positive numeric modal prices.",
    "Removed duplicate market-date-commodity targets; none remained.",
    "Kept missing reports absent rather than filling prices with zero.",
    "Built market-specific lags and shifted rolling statistics.",
    "Excluded 322 rows lacking complete 14-report history.",
  ], 62, 128, 420, 370, { fontSize: 22, spaceAfterPoints: 9 });
  const chart = slide.charts.add("line", {
    position: { left: 500, top: 126, width: 700, height: 420 },
    categories: monthly.map(row => row.month),
    series: [{ name: "Monthly median modal price", values: monthly.map(row => row.median), line: { style: "solid", fill: GREEN, width: 3 }, marker: { symbol: "none" } }],
    hasLegend: false,
    xAxis: { title: "Month", labelOffsetPercent: 75 },
    yAxis: { title: "INR per quintal", majorGridlines: { style: "solid", fill: GRID, width: 1 } },
  });
  chartFont(chart, 14);
  addNote(slide, "Observed row flow: 8,499 raw checkpoint rows to 7,794 processed market-days to 7,378 modeling rows across 23 eligible markets.");
}

// 7 - Methodology
{
  const slide = presentation.slides.add(); addHeader(slide, "Methodology", 7);
  addTextbox(slide, "Forecast horizon", 70, 126, 240, 34, { fontSize: 22, bold: true, color: GREEN });
  addTextbox(slide, "Next reported market observation", 70, 164, 360, 34, { fontSize: 25, bold: true, color: NAVY });
  const phases = [
    ["TRAIN", "through 13 Jan 2025", "5,199 rows"],
    ["VALIDATE", "14 Jan to 07 Jun 2025", "1,106 rows"],
    ["TEST", "08 Jun to 30 Oct 2025", "1,073 rows"],
  ];
  phases.forEach((phase, i) => {
    const left = 70 + i * 388;
    addBox(slide, phase[0], left, 258, 330, 54, { fill: i === 2 ? PALE : WHITE, lineColor: i === 2 ? GREEN : NAVY, bold: true, fontSize: 23 });
    addTextbox(slide, phase[1], left, 330, 330, 30, { fontSize: 20, color: DARK, alignment: "center" });
    addTextbox(slide, phase[2], left, 368, 330, 30, { fontSize: 19, color: MUTED, alignment: "center" });
  });
  addBullets(slide, [
    "Global target-date boundaries prevent later targets from entering training.",
    "Every rolling feature uses a one-observation shift within its market.",
    "Validation MAE selects the model; validation RMSE resolves ties.",
    "The held-out test set supports the final comparison only after selection.",
  ], 78, 452, 1060, 160, { fontSize: 21, spaceAfterPoints: 6 });
}

// 8 - Models
{
  const slide = presentation.slides.add(); addHeader(slide, "Model Implementation", 8);
  const values = [
    ["Model", "Category", "Principal parameters", "Advantage", "Drawback"],
    ["M0 Persistence", "Baseline", "prediction = lag 1", "Strong local benchmark", "Cannot anticipate turning points"],
    ["M1 Lag-7", "Baseline", "prediction = lag 7", "Simple longer memory", "Ignores recent reports"],
    ["M2 Ridge", "Linear", "alpha 1.0; scaled", "Stable and interpretable", "Linear response"],
    ["M3 Decision Tree", "Tree", "depth 8; leaf 5", "Nonlinear rules", "Overfitting risk"],
    ["M4 Random Forest", "Ensemble", "200 trees; depth 12; leaf 3", "Robust nonlinear fit", "Less transparent"],
    ["M5 Hist Gradient Boosting", "Boosting", "150 iterations; rate 0.05; 15 leaves", "Efficient nonlinear model", "Sensitive to drift"],
  ];
  const table = slide.tables.add({ rows: values.length, columns: 5, left: 52, top: 126, width: 1176, height: 470, values, columnWidths: [210, 128, 310, 260, 268] });
  styleTable(table, 17);
  addNote(slide, "Python 3.12; pandas 2.3.3; NumPy 2.5.3; scikit-learn 1.9.1; deterministic seed 42.");
}

// 9 - Metrics
{
  const slide = presentation.slides.add(); addHeader(slide, "Evaluation Metrics", 9);
  const values = [
    ["Metric", "Definition", "Unit / preferred direction"],
    ["MAE", "mean absolute error", "INR/q; lower"],
    ["MSE", "mean squared error", "squared INR/q; lower"],
    ["RMSE", "square root of MSE", "INR/q; lower"],
    ["R-squared", "1 - SSE/SST", "unitless; higher"],
    ["MAPE", "mean absolute percentage error", "percent; lower"],
    ["sMAPE", "symmetric percentage error", "percent; lower"],
    ["WAPE", "weighted absolute percentage error", "percent; lower"],
    ["Median AE", "median absolute error", "INR/q; lower"],
    ["Mean bias", "mean(predicted - actual)", "INR/q; near zero"],
    ["Directional accuracy", "matching movement signs vs lag 1", "percent; higher"],
  ];
  const table = slide.tables.add({ rows: values.length, columns: 3, left: 62, top: 120, width: 720, height: 505, values, columnWidths: [190, 300, 230] });
  styleTable(table, 16);
  addBox(slide, "MAE = mean(|y - yhat|)", 830, 154, 340, 62, { fill: PALE, lineColor: GREEN, fontSize: 22 });
  addBox(slide, "RMSE = sqrt(mean((y - yhat)^2))", 830, 238, 340, 70, { fill: WHITE, lineColor: NAVY, fontSize: 21 });
  addBox(slide, "MAPE = 100 mean(|(y - yhat) / y|)", 830, 330, 340, 70, { fill: PALE, lineColor: GREEN, fontSize: 20 });
  addBox(slide, "Direction = sign(price - lag 1)", 830, 422, 340, 62, { fill: WHITE, lineColor: NAVY, fontSize: 21 });
  addTextbox(slide, "Selection rule\nLowest validation MAE; validation RMSE breaks ties", 830, 526, 340, 72, { fontSize: 21, bold: true, color: NAVY, alignment: "center" });
}

// 10 - Performance
{
  const slide = presentation.slides.add(); addHeader(slide, "Model Performance Comparison", 10);
  const ordered = [...comparison].sort((a, b) => Number(a.mae) - Number(b.mae));
  const maeChart = slide.charts.add("bar", {
    position: { left: 56, top: 124, width: 555, height: 320 },
    categories: ordered.map(row => row.model.replace("M5 Hist Gradient Boosting", "M5 Hist GB")),
    series: [{ name: "Test MAE", values: ordered.map(row => Number(row.mae)), fill: GREEN }],
    barOptions: { direction: "bar", grouping: "clustered", gapWidth: 35 }, hasLegend: false,
    xAxis: { title: "MAE (INR/q)", majorGridlines: { style: "solid", fill: GRID, width: 1 } }, yAxis: { textStyle: { fontSize: 13 } },
  });
  chartFont(maeChart, 13);
  const rmseChart = slide.charts.add("bar", {
    position: { left: 642, top: 124, width: 555, height: 320 },
    categories: ordered.map(row => row.model.replace("M5 Hist Gradient Boosting", "M5 Hist GB")),
    series: [{ name: "Test RMSE", values: ordered.map(row => Number(row.rmse)), fill: NAVY }],
    barOptions: { direction: "bar", grouping: "clustered", gapWidth: 35 }, hasLegend: false,
    xAxis: { title: "RMSE (INR/q)", majorGridlines: { style: "solid", fill: GRID, width: 1 } }, yAxis: { textStyle: { fontSize: 13 } },
  });
  chartFont(rmseChart, 13);
  const values = [
    ["Validation-selected model", selected],
    ["Validation MAE", `${Number(metadata.selected_validation_mae).toFixed(1)} INR/q`],
    ["Held-out test MAE", `${Number(selectedRow.mae).toFixed(1)} INR/q`],
    ["Held-out test RMSE", `${Number(selectedRow.rmse).toFixed(1)} INR/q`],
    ["Improvement vs persistence", `${Number(metadata.mae_improvement_vs_persistence_pct).toFixed(1)}%`],
  ];
  const table = slide.tables.add({ rows: values.length, columns: 2, left: 202, top: 452, width: 876, height: 150, values, columnWidths: [430, 446] });
  styleTable(table, 17);
  addNote(slide, "Persistence won the validation rule. No machine-learning candidate improved the selected validation MAE; the baseline therefore remains the preferred model.");
}

// 11 - Diagnostics
{
  const slide = presentation.slides.add(); addHeader(slide, "Prediction Results and Diagnostics", 11);
  const line = slide.charts.add("line", {
    position: { left: 40, top: 122, width: 580, height: 360 },
    categories: focusPredictions.map(row => row.date.slice(5)),
    series: [
      { name: "Actual", values: focusPredictions.map(row => Number(row.modal_price)), line: { style: "solid", fill: NAVY, width: 2 }, marker: { symbol: "none" } },
      { name: "Predicted", values: focusPredictions.map(row => Number(row.predicted_price)), line: { style: "solid", fill: GREEN, width: 2 }, marker: { symbol: "none" } },
    ],
    legend: { position: "bottom", overlay: false },
    xAxis: { title: "Held-out reported date", labelOffsetPercent: 65 },
    yAxis: { title: "INR per quintal", majorGridlines: { style: "solid", fill: GRID, width: 1 } },
  });
  chartFont(line, 13);
  const scatter = slide.charts.add("scatter", {
    position: { left: 650, top: 122, width: 560, height: 360 },
    series: [{
      name: "Held-out observations",
      xValues: sampledPredictions.map(row => Number(row.modal_price)),
      values: sampledPredictions.map(row => Number(row.predicted_price)),
      marker: { symbol: "circle", size: 5, fill: GREEN },
      line: { style: "solid", fill: "none", width: 0 },
    }],
    scatterOptions: { style: "marker" }, hasLegend: false,
    xAxis: { title: "Actual (INR/q)", majorGridlines: { style: "solid", fill: GRID, width: 1 } },
    yAxis: { title: "Predicted (INR/q)", majorGridlines: { style: "solid", fill: GRID, width: 1 } },
  });
  chartFont(scatter, 13);
  addTextbox(slide, `Focus market: ${focusPredictions[0].market}\nTest range: ${metadata.split.test_start} to ${metadata.split.test_end}`, 70, 510, 470, 62, { fontSize: 21, color: DARK });
  addTextbox(slide, `Mean bias: ${Number(selectedRow.mean_bias_error).toFixed(1)} INR/q\nMedian absolute error: ${Number(selectedRow.median_absolute_error).toFixed(1)} INR/q`, 690, 510, 440, 62, { fontSize: 21, color: DARK });
  addNote(slide, "Residual convention: predicted price minus actual price. Positive bias indicates overprediction.");
}

// 12 - Application
{
  const slide = presentation.slides.add(); addHeader(slide, "Application and Demonstration", 12);
  const imagePath = path.join(workspaceDir, "deliverables", "final_review", "06_dashboard_screenshots", "real_overview.png");
  const bytes = await fs.readFile(imagePath);
  slide.images.add({
    blob: bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
    contentType: "image/png", alt: "Verified AgriFlow REAL-data dashboard overview",
    fit: "contain", position: { left: 50, top: 125, width: 720, height: 455 },
  });
  addTextbox(slide, "Saved forecast output", 820, 136, 330, 38, { fontSize: 27, bold: true, color: NAVY, alignment: "center" });
  addBox(slide, `Market\n${representative.market}`, 820, 196, 330, 72, { fill: PALE, lineColor: GREEN, fontSize: 22, bold: true });
  addBox(slide, `Last observation\n${representative.last_observed_date} | INR ${Number(representative.last_observed_price).toFixed(0)}/q`, 820, 286, 330, 86, { fill: WHITE, lineColor: NAVY, fontSize: 21 });
  addBox(slide, `Next-report forecast\nINR ${Number(representative.predicted_next_report_price).toFixed(0)}/q`, 820, 390, 330, 86, { fill: PALE, lineColor: GREEN, fontSize: 23, bold: true });
  addTextbox(slide, `Model: ${selected}\nHeld-out MAE: ${Number(selectedRow.mae).toFixed(1)} INR/q`, 820, 512, 330, 64, { fontSize: 21, color: DARK, alignment: "center" });
  addNote(slide, "The dashboard also retains Overview, India Map, Market Influence, Weather and Crunch, Geography, Data Quality and Research Status views.");
}

// 13 - Challenges
{
  const slide = presentation.slides.add(); addHeader(slide, "Challenges, Solutions and Drawbacks", 13);
  const values = [
    ["Challenge", "Implemented response or remaining limitation"],
    ["Uneven reporting", "Define horizon as next reported observation; never fill missing dates as prices."],
    ["Restricted acquisition", "Train and run offline from traceable local CEDA checkpoints."],
    ["Limited geography", "State four-district Maharashtra scope; avoid national performance claims."],
    ["Temporal leakage", "Group by market, shift every rolling feature and split on global target dates."],
    ["Overfitting", "Use constrained trees, a common cohort and validation-only selection."],
    ["Historical staleness", "Display the last observation and 2025-10-30 data cutoff."],
    ["No exogenous variables", "Keep the first model price-only; arrivals units remain uncertain."],
    ["Model drawback", "Persistence cannot anticipate shocks or turning points, despite winning validation MAE."],
  ];
  const table = slide.tables.add({ rows: values.length, columns: 2, left: 58, top: 120, width: 1164, height: 510, values, columnWidths: [300, 864] });
  styleTable(table, 18);
}

// 14 - Conclusion
{
  const slide = presentation.slides.add(); addHeader(slide, "Conclusion and Future Scope", 14);
  addTextbox(slide, "What the project achieved", 70, 126, 500, 38, { fontSize: 28, bold: true, color: NAVY });
  addBullets(slide, [
    "Preserved the existing market-analysis dashboard.",
    "Evaluated six forecasting approaches with ten metrics.",
    `Selected ${selected} using validation MAE of ${Number(metadata.selected_validation_mae).toFixed(1)} INR/q.`,
    `Measured held-out MAE of ${Number(selectedRow.mae).toFixed(1)} INR/q and RMSE of ${Number(selectedRow.rmse).toFixed(1)} INR/q.`,
    "Delivered saved next-report forecasts and reproducible evidence.",
  ], 70, 180, 540, 350, { fontSize: 23, spaceAfterPoints: 8 });
  addTextbox(slide, "Future scope", 690, 126, 420, 38, { fontSize: 28, bold: true, color: NAVY });
  addBullets(slide, [
    "Broaden market and commodity coverage.",
    "Add verified weather and consistently measured arrivals.",
    "Collect a longer historical series and refresh the data.",
    "Evaluate fixed calendar horizons separately.",
    "Revisit tuning only after stronger coverage becomes available.",
  ], 690, 180, 470, 350, { fontSize: 23, spaceAfterPoints: 8 });
  addBox(slide, "Measured improvement versus persistence: 0.0%\nThe baseline won, so no unsupported ML advantage is claimed.", 270, 560, 740, 68, { fill: PALE, lineColor: GREEN, fontSize: 22, bold: true });
}

// 15 - References
{
  const slide = presentation.slides.add(); addHeader(slide, "References", 15);
  const refs = [
    "CEDA Agri Market Data documentation: https://api.ceda.ashoka.edu.in/documentation/",
    "Government of India AGMARKNET / OGD resource: https://data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi",
    "AgriFlow repository documentation: README.md; docs/04_DATA_SPECIFICATION.md; docs/05_ANALYTICS_SPECIFICATION.md",
    "scikit-learn documentation: https://scikit-learn.org/stable/",
    "pandas documentation: https://pandas.pydata.org/docs/",
    "NumPy documentation: https://numpy.org/doc/",
    "Dash documentation: https://dash.plotly.com/",
    "Plotly Python documentation: https://plotly.com/python/",
    "Hyndman and Athanasopoulos, Forecasting: Principles and Practice, https://otexts.com/fpp3/",
  ];
  addBullets(slide, refs, 78, 126, 1110, 480, { fontSize: 21, spaceAfterPoints: 8, marginLeftPoints: 18, hangingPoints: 9 });
  addNote(slide, "All experimental values in this deck originate from the saved local dataset and generated forecasting artifacts.");
}

await fs.mkdir(buildDir, { recursive: true });
await fs.mkdir(renderDir, { recursive: true });
await fs.mkdir(outputDir, { recursive: true });
for (const [index, slide] of presentation.slides.items.entries()) {
  const png = await presentation.export({ slide, format: "png", scale: 1 });
  await fs.writeFile(path.join(renderDir, `slide-${String(index + 1).padStart(2, "0")}.png`), new Uint8Array(await png.arrayBuffer()));
}
const montage = await presentation.export({ format: "webp", montage: true });
await fs.writeFile(path.join(buildDir, "montage.webp"), new Uint8Array(await montage.arrayBuffer()));

const requirements = {
  explicitTotalSlideCount: 15,
  requiredNativeTableOwnerSlides: [5, 8, 9, 10, 13],
  requiredNativeChartOwnerSlides: [5, 6, 10, 11],
  requiredEmbeddedWorkbookChartOwnerSlides: [],
  materializeLiteralChartWorkbooks: true,
  nativeChartTargetApplication: "powerpoint",
};
const fontPolicy = { basis: "user_request", families: [FONT] };
const stagingDir = path.join(workspaceDir, ".codex-finalizer");
await fs.mkdir(stagingDir, { recursive: true });
const candidatePath = path.join(stagingDir, "AgriFlow_Final_Review_candidate.pptx");
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);

const result = await finalizePresentation({
  ...requirements,
  workspaceDir,
  candidatePath,
  finalPath: FINAL_PPTX,
  pythonExecutable: RUNTIME_PYTHON,
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools", "inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools", "inspect_presentation_layout_geometry.py"),
  layoutArgs: [
    "--expected-slide-size-emu", "12192000,6858000",
    "--validate-bullet-geometry",
    "--validate-heading-fit",
    ...requirements.requiredNativeTableOwnerSlides.flatMap(number => ["--require-native-table-slide", String(number)]),
  ],
  requiredNativeTableOwnerSlides: requirements.requiredNativeTableOwnerSlides,
  fontPolicy,
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, "AgriFlow_Final_Review.validation.json"),
});

console.log(JSON.stringify({ finalPath: FINAL_PPTX, renderDir, selectedModel: selected, result }, null, 2));
