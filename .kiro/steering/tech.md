#ReFarmAI Technical Stack & Development Guidelines

## Architecture
- **Multi-Agent Framework**: Python (FastAPI), Node.js with standardized message passing
- **Hybrid Deployment**: Cloud services for complex analytics, edge computing for real-time responses
- **Voice Processing**: WebRTC, Speech Recognition APIs, Whisper, Festival TTS
- **API-First Design**: RESTful APIs with OpenAPI specifications, WebSocket for real-time communication

## Technology Stack

### Backend & AI/ML
- **Languages**: Python, Node.js, JavaScript
- **Frameworks**: FastAPI, Express.js
- **AI/ML**: TensorFlow, PyTorch, spaCy, Transformers
- **Message Queue**: Apache Kafka, RabbitMQ
- **API Gateway**: Kong, AWS API Gateway

### Data & Storage
- **Time Series**: InfluxDB, TimescaleDB
- **Graph Database**: Neo4j, Amazon Neptune  
- **Document Store**: MongoDB, Elasticsearch
- **Relational**: PostgreSQL, MySQL
- **Cache**: Redis, Memcached
- **Data Lake**: For raw data ingestion and batch processing

### Frontend & Mobile
- **Web**: React.js, Vue.js
- **Mobile**: React Native, Flutter
- **Voice Interface**: WebRTC, Speech Recognition APIs
- **Offline Support**: Service Workers, IndexedDB

### Infrastructure & DevOps
- **Containers**: Docker, Kubernetes
- **Cloud**: AWS, Azure, Google Cloud
- **Edge Computing**: AWS IoT Greengrass
- **Monitoring**: Prometheus, Grafana, ELK Stack
- **CI/CD**: Automated pipelines with blue-green deployment

## Common Commands

### Development Setup
```bash
# Clone and setup
git clone <repository>
cd plantai
npm install
pip install -r requirements.txt

# Start development environment
docker-compose up -d
npm run dev
python manage.py runserver
```

### Testing
```bash
# Run all tests
npm test
pytest
npm run test:e2e

# Code quality
npm run lint
flake8 .
sonar-scanner
```

### Deployment
```bash
# Build and deploy
docker build -t plantai:latest .
kubectl apply -f k8s/
helm upgrade plantai ./charts/plantai
```

## Development Standards
- **Code Coverage**: >80% automated test coverage required
- **API Documentation**: OpenAPI specs for all endpoints
- **Security**: OAuth 2.0 with JWT tokens, end-to-end encryption
- **Performance**: <3 second voice response time, 99.5% uptime target
- **Multilingual**: Support for 6+ Indian languages with dialect recognition
- **Offline-First**: Core functionality must work without internet connectivity