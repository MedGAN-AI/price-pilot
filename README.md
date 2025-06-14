[![Docker Image CI (ghcr)](https://github.com/MedGAN-AI/price-pilot/actions/workflows/ghcr.yml/badge.svg)](https://github.com/MedGAN-AI/price-pilot/actions/workflows/ghcr.yml)
[![Docker Image CI (dh)](https://github.com/MedGAN-AI/price-pilot/actions/workflows/main.yml/badge.svg)](https://github.com/MedGAN-AI/price-pilot/actions/workflows/main.yml)

# Price Pilot

An intelligent multi-agent system for e-commerce operations, featuring AI-powered chat, inventory management, order processing, logistics tracking, demand forecasting, and product recommendations.

##  Architecture

Price Pilot consists of specialized AI agents that work together to handle different aspects of e-commerce operations:

- **ChatAgent**: Natural language interface and task delegation
- **InventoryAgent**: Stock level monitoring and management
- **OrderAgent**: Order processing and ERP integration
- **LogisticsAgent**: Shipment tracking with Aramex and Naqel carriers
- **ForecastAgent**: Demand prediction using ARIMA models
- **RecommendAgent**: AI-powered product recommendations

##  Quick Start

### Prerequisites
- Python 3.12+
- Node.js 16+
- Docker & Docker Compose

### Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configurations
```

### Using Docker (Recommended)

#### Option 1: Pre-built Images
```bash
# Pull from Docker Hub
docker pull mozaloom/price-pilot-backend
docker pull mozaloom/price-pilot-frontend

# Or pull from GitHub Container Registry
docker pull ghcr.io/medgan-ai/price-pilot-backend:latest
docker pull ghcr.io/medgan-ai/price-pilot-frontend:latest

# Start all services
docker-compose up -d
```

#### Option 2: Build from Source
```bash
# Start all services (builds images locally)
docker-compose up -d --build

# Access the application
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
```

### Manual Setup

#### Backend
```bash
cd backend
pip install -r requirements.txt
python main.py
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

##  Project Structure

```
price-pilot/
├── backend/           # Python FastAPI backend
│   ├── src/agents/   # AI agent implementations
│   ├── src/core/     # Base classes and utilities
│   ├── src/graphs/   # Agent orchestration logic
│   └── models/       # ML models and data
├── frontend/         # React frontend application
├── infra/            # Infrastructure and deployment
├── docs/             # Documentation
└── sql/              # Database schemas
```

##  Key Features

- **Multi-Agent AI System**: Specialized agents for different business functions
- **Real-time Chat Interface**: Natural language interaction with the system
- **Inventory Management**: Automated stock monitoring and alerts
- **Order Processing**: Seamless ERP integration and order fulfillment
- **Logistics Tracking**: Real-time shipment monitoring across multiple carriers
- **Demand Forecasting**: ML-powered sales prediction using ARIMA models
- **Smart Recommendations**: AI-driven product suggestion engine
- **Vector Search**: Embedding-based product discovery

##  Technology Stack

**Backend:**
- Python 3.12 with FastAPI
- LangChain for AI agent orchestration
- Supabase for database and real-time features
- MLflow for model management
- SQLite for local caching

**Frontend:**
- React with modern JavaScript
- Real-time UI updates
- Responsive design

**Infrastructure:**
- Docker containerization
- Docker Compose for local development
- Modular deployment architecture

##  Monitoring & Logging

- Application logs in `backend/app.log`
- Shipment monitoring database
- LangChain caching for performance optimization

##  Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `make test`
5. Submit a pull request

##  License

This project is licensed under the terms specified in the LICENSE file.

---

**Getting Started?** Check out the `/docs` directory for detailed documentation and API references.
