
# 🏥 ReadmitIQ — Hospital Readmission Prediction Platform

> **ML-powered system to predict 30-day hospital readmissions before discharge**  
> Real-time risk scoring · Explainable AI · Clinical decision support

---

## 🎯 Problem

### The Healthcare Crisis

Hospital readmissions within 30 days cost the US healthcare system **$26 billion annually**. The Centers for Medicare & Medicaid Services (CMS) penalizes hospitals for excess readmissions under the Hospital Readmission Reduction Program (HRRP).

### Why Current Solutions Fail

- **Reactive, not proactive**: Hospitals typically identify readmission risk only after it happens
- **Siloed data**: Patient records are fragmented across multiple systems (EHR, lab, imaging)
- **No explainability**: Clinicians get a risk score but no understanding of *why*
- **One-size-fits-all**: Generic interventions that don't account for individual patient factors
- **No real-time alerts**: High-risk patients may go unnoticed until it's too late

---

## 💡 Solution

**ReadmitIQ** predicts readmission risk **before discharge** and provides:

- 📊 Risk score (0–1) with confidence interval  
- 🧠 Explainable AI (SHAP) for transparency  
- ⚡ Real-time alerts via WebSockets  
- 🏥 Actionable clinical recommendations  
- 🔮 What-If Simulations — Model the impact of interventions
- 💰 Financial ROI Tracking — Measure cost savings
- 🤖 AI Copilot — Conversational interface for clinical decision support
- 📝 Clinical Notes NLP — Extract risk signals from unstructured notes  

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         ReadmitIQ Platform                       │
│                                                                   │
│  ┌──────────────┐    HTTP/WS    ┌──────────────────────────────┐ │
│  │   React UI   │◄─────────────►│     FastAPI Backend          │ │
│  │  (Port 81)   │               │     (Port 8001)               │ │
│  │              │               │                              │ │
│  │ • Dashboard  │               │  ┌─────────────────────────┐ │ │
│  │ • Patients   │               │  │    ML Inference Engine  │ │ │
│  │ • SHAP viz   │               │  │  XGBoost + LightGBM +   │ │ │
│  │ • Alerts     │               │  │  LogReg + Calibration    │ │ │
│  │ • Retrain    │               │  │  SHAP + Explainability   │ │ │
│  │ • Copilot    │               │  └─────────────────────────┘ │ │
│  │ • Simulation │               │                              │ │
│  │ • Financials │               │  ┌──────┐  ┌─────────────┐  │ │
│  └──────────────┘               │  │ PG   │  │   Redis     │  │ │
│                                 │  │ DB   │  │   Cache     │  │ │
│                                 │  └──────┘  └─────────────┘  │ │
│                                 │                              │ │
│                                 │  ┌─────────────────────────┐ │ │
│                                 │  │  Celery Workers          │ │ │
│                                 │  │  (Async Model Training)  │ │ │
│                                 │  └─────────────────────────┘ │ │
│                                 └──────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📸 Output Screenshots

![Dashboard](./readmitiq/outputimages/Screenshot%202026-03-24%20201735.png)  
![Patients](./readmitiq/outputimages/Screenshot%202026-03-24%20201756.png)  
![Prediction](./readmitiq/outputimages/Screenshot%202026-03-24%20201806.png)  
![Risk Trajectory](./readmitiq/outputimages/Screenshot%202026-03-24%20201816.png)  
![Financials](./readmitiq/outputimages/Screenshot%202026-03-24%20201836.png)  
![Simulation](./readmitiq/outputimages/Screenshot%202026-03-24%20201846.png)  
![Model](./readmitiq/outputimages/Screenshot%202026-03-24%20201855.png)

---

## 🔄 Workflow

1. Patient Data Input (EHR, vitals, labs)  
2. Data Preprocessing & Feature Engineering  
3. Time-Series Modeling  
4. Risk Prediction using ML Models  
5. Explainability (SHAP/LIME insights)  
6. Dashboard Visualization & Alerts  

<img width="1446" height="366" alt="readmicare" src="https://github.com/user-attachments/assets/4cc504f8-1108-4738-b2b7-3a9134625cca" />

---


## 🛠 Technology Stack

| Layer | Technology | Why We Used It |
|-------|-----------|----------------|
| **Frontend** | React 18 + Vite | Modern, fast SPA with excellent developer experience |
| **Charts** | Recharts | Composable, React-native charting library |
| **Animations** | Framer Motion | Smooth animations for clinical dashboard |
| **State** | Zustand | Minimalist state management without boilerplate |
| **Backend** | FastAPI | Modern Python async web framework; automatic OpenAPI docs |
| **Database** | PostgreSQL 16 | Reliable relational database with excellent JSON support |
| **Cache/Queue** | Redis 7 | In-memory data store for caching and Celery message broker |
| **Task Queue** | Celery | Distributed task queue for async ML model retraining |
| **ML** | XGBoost | Gradient boosting — top performer for tabular healthcare data |
| **ML** | LightGBM | Fast gradient boosting; complements XGBoost in ensemble |
| **ML** | Scikit-learn | Classical ML algorithms and utilities |
| **Explainability** | SHAP | State-of-the-art model explainability (Shapley values) |
| **Deployment** | Docker Compose | Container orchestration for easy deployment |

---

## 🔐 Security

* JWT Authentication
* Role-based access control
* Audit logging
* Synthetic data support (no PHI exposure)

---

## 📂 Project Structure

```
backend/      → API + ML pipeline
frontend/     → React dashboard
infra/        → DB setup
docker-compose.yml
```

---

## 🔌 Extensibility

* Add new ML models easily
* Plug in real hospital datasets
* Extend APIs for new analytics

---

## ✨ Highlights

* Real-time clinical AI system
* Explainable predictions (not black-box)
* Production-ready architecture
* Strong ML + full-stack integration

---

## 📜 License

MIT License

```

