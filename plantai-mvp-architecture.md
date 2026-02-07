# PlantAI MVP Architecture Diagram

## MVP Architecture Overview

This diagram shows the simplified architecture for the PlantAI MVP, focusing on core functionality needed for the initial deployment with rubber plantation farmers.

```mermaid
graph TB
    subgraph "User Interface Layer - MVP"
        VI[Voice Interface<br/>Hindi/Tamil/Malayalam]
        MA[Mobile App<br/>React Native]
        WD[Web Dashboard<br/>React.js]
    end
    
    subgraph "API Gateway & Load Balancer"
        AG[API Gateway<br/>FastAPI + Kong]
        LB[Load Balancer<br/>NGINX]
    end
    
    subgraph "Core Orchestration - MVP"
        AC[Agent Coordinator<br/>Python FastAPI]
        KG[Knowledge Graph<br/>Neo4j Lite]
        DA[Data Access Layer<br/>Python + Redis Cache]
    end
    
    subgraph "Essential Agents - MVP"
        FA[Farmer Agent<br/>Voice + Context]
        AA[Agronomy Agent<br/>Crop Recommendations]
        TA[Tapping Agent<br/>Schedule Optimization]
        MA_AGENT[Market Agent<br/>Price Intelligence]
    end
    
    subgraph "MVP Data Sources"
        IMD[IMD Weather API<br/>Government Data]
        RB[Rubber Board API<br/>Market Prices]
        SOIL[Basic IoT Sensors<br/>Soil + Weather]
        CACHE[Local Cache<br/>Redis]
    end
    
    subgraph "MVP Data Storage"
        PG[PostgreSQL<br/>Farmers + Plantations]
        INFLUX[InfluxDB<br/>Sensor Data]
        MONGO[MongoDB<br/>Voice Interactions]
    end
    
    subgraph "Voice Processing - MVP"
        STT[Speech-to-Text<br/>Whisper Local]
        NLU[NLU Engine<br/>spaCy + Custom]
        TTS[Text-to-Speech<br/>Festival TTS]
    end
    
    %% User Interface Connections
    VI --> AG
    MA --> AG
    WD --> AG
    
    %% API Gateway
    AG --> LB
    LB --> AC
    
    %% Core Orchestration
    AC --> KG
    AC --> DA
    AC --> FA
    
    %% Agent Communication
    FA --> AA
    FA --> TA
    FA --> MA_AGENT
    AA <--> TA
    TA <--> MA_AGENT
    
    %% Voice Processing
    VI --> STT
    STT --> NLU
    NLU --> FA
    FA --> TTS
    TTS --> VI
    
    %% Data Access
    DA --> IMD
    DA --> RB
    DA --> SOIL
    DA --> CACHE
    
    %% Knowledge Graph
    KG --> PG
    KG --> INFLUX
    KG --> MONGO
    
    %% Styling
    classDef mvpCore fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef mvpAgent fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef mvpData fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    classDef mvpUI fill:#fff3e0,stroke:#e65100,stroke-width:2px
    
    class AC,KG,DA mvpCore
    class FA,AA,TA,MA_AGENT mvpAgent
    class PG,INFLUX,MONGO,IMD,RB,SOIL mvpData
    class VI,MA,WD mvpUI
```

## MVP Technology Stack

### Backend Services
- **Language**: Python 3.9+
- **Framework**: FastAPI with async/await
- **Agent Framework**: Custom Python classes with direct messaging
- **API Gateway**: Kong or AWS API Gateway
- **Load Balancer**: NGINX

### Voice Processing
- **Speech-to-Text**: OpenAI Whisper (local deployment)
- **NLU**: spaCy with custom agricultural models
- **Text-to-Speech**: Festival TTS with Hindi/Tamil/Malayalam support
- **Offline Support**: Local models cached on edge devices

### Data Storage
- **Primary Database**: PostgreSQL 14+ (farmers, plantations, equipment)
- **Time Series**: InfluxDB 2.0 (sensor data, weather data)
- **Document Store**: MongoDB 5.0 (voice interactions, unstructured data)
- **Graph Database**: Neo4j Community Edition (relationships)
- **Cache**: Redis 6.0+ (session data, frequent queries)

### Frontend Applications
- **Mobile App**: React Native 0.72+ (iOS/Android)
- **Web Dashboard**: React.js 18+ with TypeScript
- **Voice Interface**: WebRTC for real-time audio streaming

### External Integrations
- **Weather Data**: India Meteorological Department (IMD) API
- **Market Data**: Rubber Board of India API
- **IoT Sensors**: Basic soil moisture, temperature, humidity sensors
- **Authentication**: OAuth 2.0 with JWT tokens

## MVP Deployment Architecture

```mermaid
graph TB
    subgraph "Edge/Village Level"
        EDGE[Edge Device<br/>Raspberry Pi 4]
        VOICE_LOCAL[Local Voice Processing<br/>Whisper + TTS]
        CACHE_LOCAL[Local Cache<br/>Redis Lite]
        IOT_GATEWAY[IoT Gateway<br/>MQTT Broker]
    end
    
    subgraph "Cloud Infrastructure - MVP"
        ALB[Application Load Balancer<br/>AWS ALB / Azure LB]
        API_CLUSTER[API Services<br/>Docker + Kubernetes]
        AGENT_SERVICES[Agent Services<br/>FastAPI Containers]
        DB_CLUSTER[Database Cluster<br/>Managed Services]
    end
    
    subgraph "External Services"
        IMD_API[IMD Weather API]
        RUBBER_API[Rubber Board API]
        SMS_SERVICE[SMS Gateway<br/>Twilio/AWS SNS]
    end
    
    %% Edge to Cloud
    EDGE --> ALB
    VOICE_LOCAL --> EDGE
    CACHE_LOCAL --> EDGE
    IOT_GATEWAY --> EDGE
    
    %% Cloud Services
    ALB --> API_CLUSTER
    API_CLUSTER --> AGENT_SERVICES
    AGENT_SERVICES --> DB_CLUSTER
    
    %% External Integrations
    AGENT_SERVICES --> IMD_API
    AGENT_SERVICES --> RUBBER_API
    AGENT_SERVICES --> SMS_SERVICE
    
    %% Styling
    classDef edge fill:#ffecb3,stroke:#ff8f00,stroke-width:2px
    classDef cloud fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef external fill:#f1f8e9,stroke:#388e3c,stroke-width:2px
    
    class EDGE,VOICE_LOCAL,CACHE_LOCAL,IOT_GATEWAY edge
    class ALB,API_CLUSTER,AGENT_SERVICES,DB_CLUSTER cloud
    class IMD_API,RUBBER_API,SMS_SERVICE external
```

## MVP Data Flow

```mermaid
sequenceDiagram
    participant F as Farmer
    participant V as Voice Interface
    participant FA as Farmer Agent
    participant AA as Agronomy Agent
    participant KG as Knowledge Graph
    participant IMD as IMD Weather API
    participant DB as Database
    
    F->>V: Voice Query (Hindi)<br/>"मेरी फसल के लिए सबसे अच्छा समय क्या है?"
    V->>FA: Processed Intent<br/>"crop_timing_query"
    FA->>KG: Get Farmer Context<br/>farmer_id, plantation_data
    KG->>DB: Query Farmer Profile
    DB-->>KG: Farmer + Plantation Data
    KG-->>FA: Complete Context
    FA->>AA: Crop Timing Request<br/>+ Context
    AA->>IMD: Get Weather Data<br/>location, date_range
    IMD-->>AA: Weather Forecast
    AA->>KG: Store Analysis
    AA-->>FA: Crop Timing Recommendation
    FA->>V: Generate Response<br/>"अगले सप्ताह बुवाई के लिए अच्छा समय है"
    V->>F: Voice Response (Hindi)
```

## MVP Simplifications

### Reduced Scope for MVP
1. **Languages**: Start with 3 languages (Hindi, Tamil, Malayalam) instead of 6
2. **Agents**: Implement 4 core agents instead of 6 (skip Community and Climate for MVP)
3. **Data Sources**: Focus on essential APIs (IMD, Rubber Board) and basic IoT sensors
4. **Deployment**: Single-region deployment instead of multi-region
5. **Features**: Core voice interaction and basic recommendations only

### MVP Success Criteria
- **Performance**: <5 seconds voice response (relaxed from <3 seconds)
- **Accuracy**: >85% speech recognition (relaxed from >95%)
- **Users**: 100+ farmers in pilot (reduced from 1000+)
- **Uptime**: 95% availability (relaxed from 99.5%)
- **Languages**: 3 Indian languages with basic dialect support

### Post-MVP Expansion Path
1. **Phase 2**: Add Community and Climate agents
2. **Phase 3**: Expand to 6 languages with full dialect support
3. **Phase 4**: Add satellite imagery and advanced IoT integration
4. **Phase 5**: Multi-region deployment and scaling to 1000+ farmers

This MVP architecture provides a solid foundation while being achievable for initial deployment and testing with rubber plantation farmers.