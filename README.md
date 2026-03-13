# 🌾 AgroShield — Geopolitical Agricultural Trade Intelligence System

> Monitor global geopolitical events in real-time and predict their cascading impact on India's agricultural trade. Generate actionable advisories for farmers, policymakers, consumers, and traders using Amazon Bedrock.

---

## Architecture 

```
GDELT API (free, real-time)
    ↓
Agent 1 — Event Collector      (fetches 65,000+ news sources every 90s)
    ↓
Agent 2 — Event Processor      (extracts country, event_type, severity, commodities)
    ↓
Agent 3 — Risk Predictor       (XGBoost ML model from S3 → LOW/MEDIUM/HIGH/CRITICAL)
    ↓
Agent 4 — Impact Reasoner      (derives states, farmers at risk, revenue, cascading effects)
    ↓
Agent 5 — Advisory Generator   (Amazon Bedrock Claude Sonnet → 4-stakeholder advisories)
    ↓
DynamoDB + In-memory store → FastAPI → React Frontend
```

## AWS Services Used

| Service | Purpose |
|---------|---------|
| **Amazon S3** | Trade dataset CSV + XGBoost model artifacts |
| **Amazon Bedrock** | Claude Sonnet / Nova Lite for advisory generation |
| **Amazon DynamoDB** | Persistent storage for events and advisories |
| **Amazon EC2 t3.medium** | FastAPI backend + Nginx frontend serving |
| **Amazon CloudWatch** | Backend logs via systemd journal |

---

## Quick Start

### 1. Prerequisites
- Python 3.11+, Node.js 18+
- AWS account with Bedrock access (ap-south-1 or us-east-1)
- IAM role with: `S3:GetObject`, `S3:PutObject`, `bedrock:InvokeModel`, `dynamodb:PutItem`, `dynamodb:GetItem`

### 2. Upload your data to S3
```bash
cd backend
cp .env.example .env
# Edit .env with your AWS credentials

# Create S3 bucket and upload data + model
python setup_s3.py
```

### 3. Create DynamoDB tables
```bash
python setup_dynamo.py
```

### 4. Run locally
```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

### 5. Deploy to EC2
```bash
chmod +x deploy.sh
./deploy.sh
```

---

## Training Your Own Model

If you have the trade dataset CSV (139,626 rows with the columns listed below):

```bash
cd backend
python train_model.py --csv data/trade_dataset.csv --out data/
python setup_s3.py  # upload to S3
```

The trainer will auto-derive risk labels from `Effective_Shock` + `Trade_Share` if no `risk_label` column exists.

### Required CSV Columns
```
Year, Month, Country, Trade_Type, HS4, HS2, Commodity,
Value_USD, NetWeight_KG, Unit_Price_USD_per_KG, Signed_Trade_Value_USD,
MoM_Change_Value, Rolling_3M_Volatility, Total_Event_Count,
Avg_Goldstein, Avg_Tone, Total_Mentions, Total_Sources,
Shock_Intensity, Conflict_Event_Count, Protest_Event_Count,
Trade_Shock_Count, Sanction_Threat_Count, Incoming_Shock_Count,
Outgoing_Shock_Count, Net_Hostility, Conflict_Density,
Protest_Density, Trade_Shock_Density, Total_Country_Trade_USD,
Trade_Share, Effective_Shock, Conflict_Exposure, Protest_Exposure,
Trade_Shock_Exposure, Incoming_Shock_Exposure, Outgoing_Shock_Exposure,
Net_Hostility_Exposure, Log_Value_USD, Shock_Intensity_Lag1,
Shock_Intensity_Lag2, Trade_Share_Lag1, Trade_Share_Lag2,
Lagged_Effective_Shock_1, Lagged_Effective_Shock_2
```

---

## Example: How It Works

**Input headline**: `"USA imposes 50% tariff on Indian agricultural exports"`

1. **Agent 1** fetches from GDELT ✅
2. **Agent 2** extracts: `country=USA, type=TARIFF, severity=50%`
3. **Agent 3** reads real `Trade_Share=18.4%` from S3 CSV → XGBoost → `CRITICAL (94/100)`
4. **Agent 4** derives: `$840M at risk, 8.3M farmers, Punjab/Gujarat/Andhra affected`
5. **Agent 5** calls Bedrock Claude → dynamic 4-stakeholder advisory
6. Frontend shows CRITICAL alert with real data

**Input headline**: `"Iran fires missiles near Strait of Hormuz"`

1. Iran not in CSV → proxy = Saudi Arabia/UAE stats
2. GDELT Goldstein = -8.5 injected
3. XGBoost → CRITICAL (96/100)
4. Impact: oil route disruption, diesel spike, rice export lane blocked
5. Bedrock: advisory mentions Hormuz, Punjab basmati exports, diesel costs

---

## Environment Variables

```env
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET=agroshield-trade-data
BEDROCK_MODEL=anthropic.claude-3-sonnet-20240229-v1:0
BEDROCK_FALLBACK_MODEL=amazon.nova-lite-v1:0
USE_DYNAMO=true
PIPELINE_INTERVAL_SECONDS=90
```

---

## Frontend Pages

| Page | Description |
|------|-------------|
| Dashboard | KPIs, threat map, system risk gauge |
| Event Tracker | Filterable GDELT event table |
| Live Feed | Real-time stream + custom headline analyzer |
| Risk Analyzer | ML predictions + commodity risk matrix |
| Trade Flows | Partner exposure + shipping route risk |
| Price Alerts | Commodity price impact predictions |
| Advisories | Full stakeholder advisories from Bedrock |
| Policy Support | Action timeline + buffer stock status |
| Farmer Portal | Crop calendar + state-wise risk + opportunities |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI + Python 3.11 on EC2 t3.medium |
| ML Model | XGBoost (trained on 139K rows) |
| LLM | Amazon Bedrock Claude Sonnet / Nova Lite |
| Data | AWS S3 (CSV + model artifacts) |
| Database | AWS DynamoDB |
| Event Source | GDELT API (free, real-time, no key needed) |
| Frontend | React 18 + Vite + Tailwind CSS |
| Deployment | EC2 + Nginx + systemd |

---

Built for **AI 4 Bharat Hackathon** — AWS Track
