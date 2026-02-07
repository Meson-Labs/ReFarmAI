# PlantAI Project Structure & Organization

## Repository Structure
```
plantai/
├── docs/                           # Project documentation
│   ├── api_specifications.md       # API documentation
│   ├── system_architecture.md      # Technical architecture
│   ├── requirements.md            # System requirements
│   └── implementation_timeline.md  # Project roadmap
├── src/
│   ├── agents/                    # Multi-agent system
│   │   ├── farmer_interaction/    # Voice-first farmer agent
│   │   ├── agronomy/             # Crop recommendation agent
│   │   ├── mechanized_tapping/   # Tapping optimization agent
│   │   ├── market_supply/        # Market intelligence agent
│   │   ├── community/            # Community management agent
│   │   └── climate/              # Climate & sustainability agent
│   ├── orchestration/            # Agent coordination layer
│   │   ├── coordinator.py        # Multi-agent coordinator
│   │   ├── knowledge_graph.py    # Knowledge graph engine
│   │   └── data_access.py        # Unified data access layer
│   ├── voice/                    # Voice processing pipeline
│   │   ├── stt/                  # Speech-to-text
│   │   ├── nlu/                  # Natural language understanding
│   │   └── tts/                  # Text-to-speech
│   ├── data/                     # Data integration layer
│   │   ├── government/           # Government API integrations
│   │   ├── iot/                  # IoT sensor data
│   │   ├── satellite/            # Satellite imagery
│   │   └── market/               # Market data feeds
│   └── api/                      # REST API endpoints
├── mobile/                       # Mobile applications
│   ├── farmer_app/              # React Native farmer app
│   └── cooperative_dashboard/    # Web dashboard
├── infrastructure/               # Infrastructure as code
│   ├── docker/                  # Docker configurations
│   ├── kubernetes/              # K8s manifests
│   └── terraform/               # Cloud infrastructure
├── tests/                       # Test suites
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   └── e2e/                     # End-to-end tests
└── scripts/                     # Utility scripts
    ├── deployment/              # Deployment scripts
    └── data_migration/          # Data migration tools
```

## Key Directories

### `/src/agents/`
Each agent is a self-contained module with:
- `agent.py` - Main agent logic
- `models/` - ML models and data schemas
- `services/` - External service integrations
- `tests/` - Agent-specific tests

### `/src/orchestration/`
Central coordination system managing:
- Agent communication protocols
- Knowledge graph for data relationships
- Unified data access across all agents
- Security and authentication

### `/src/voice/`
Voice processing pipeline with:
- Multilingual speech recognition
- Agricultural domain NLU
- Context-aware conversation management
- Offline processing capabilities

### `/src/data/`
Data integration layer connecting:
- Government APIs (IMD, ICAR, Rubber Board)
- IoT sensor networks
- Satellite imagery providers
- Market data feeds

## File Naming Conventions
- **Python**: `snake_case.py`
- **JavaScript**: `camelCase.js`
- **Components**: `PascalCase.jsx`
- **Constants**: `UPPER_SNAKE_CASE`
- **APIs**: `/kebab-case` endpoints
- **Databases**: `snake_case` tables and fields

## Configuration Management
- Environment-specific configs in `/config/`
- Secrets managed through environment variables
- Feature flags for gradual rollouts
- Multi-region deployment configurations

## Documentation Standards
- API documentation using OpenAPI/Swagger
- Architecture diagrams in Mermaid format
- Code documentation with docstrings
- README files for each major component