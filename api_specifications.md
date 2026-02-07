# PlantAI API Specifications
## RESTful API Documentation for Multi-Agent System

### Document Overview
This document provides comprehensive API specifications for the PlantAI multi-agent system, including endpoint definitions, request/response schemas, authentication mechanisms, and integration guidelines.

---

## 1. API Architecture Overview

### Base URL Structure
```
Production: https://api.plantai.gov.in/v1
Staging: https://staging-api.plantai.gov.in/v1
Development: https://dev-api.plantai.gov.in/v1
```

### Authentication
- **Type**: OAuth 2.0 with JWT tokens
- **Scopes**: farmer, cooperative, admin, system
- **Token Expiry**: 24 hours (access), 30 days (refresh)

### Rate Limiting
- **Farmer APIs**: 1000 requests/hour
- **System APIs**: 10000 requests/hour
- **Bulk Operations**: 100 requests/hour

---

## 2. Core API Endpoints

### 2.1 Authentication APIs

#### POST /auth/login
Authenticate farmer or system user

**Request:**
```json
{
  "phone_number": "+91XXXXXXXXXX",
  "otp": "123456",
  "language": "hi",
  "device_id": "unique-device-identifier"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 86400,
  "farmer_id": "farmer_12345",
  "profile": {
    "name": "राम कुमार",
    "plantation_id": "plantation_67890",
    "location": {
      "state": "Kerala",
      "district": "Kottayam",
      "village": "Rubber Valley"
    }
  }
}
```

#### POST /auth/refresh
Refresh access token

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### POST /auth/logout
Logout and invalidate tokens

---

### 2.2 Voice Interaction APIs

#### POST /voice/process
Process voice input and return agent response

**Request:**
```json
{
  "audio_data": "base64_encoded_audio",
  "format": "wav",
  "sample_rate": 16000,
  "language": "hi",
  "session_id": "session_12345",
  "context": {
    "previous_intent": "crop_recommendation",
    "plantation_id": "plantation_67890"
  }
}
```

**Response:**
```json
{
  "session_id": "session_12345",
  "intent": "weather_query",
  "confidence": 0.95,
  "agent": "climate_sustainability",
  "response": {
    "text": "आज बारिश की संभावना है। टैपिंग का काम शाम तक टाल दें।",
    "audio_url": "https://cdn.plantai.gov.in/audio/response_12345.mp3",
    "duration": 5.2
  },
  "data": {
    "weather": {
      "temperature": 28,
      "humidity": 85,
      "rainfall_probability": 80,
      "wind_speed": 12
    }
  },
  "suggestions": [
    "क्या मुझे कल का मौसम बताएं?",
    "टैपिंग के लिए सबसे अच्छा समय कब है?"
  ]
}
```

#### GET /voice/session/{session_id}
Retrieve conversation history

#### DELETE /voice/session/{session_id}
Clear conversation context

---

### 2.3 Farmer Profile APIs

#### GET /farmers/{farmer_id}
Get farmer profile and plantation details

**Response:**
```json
{
  "farmer_id": "farmer_12345",
  "personal_info": {
    "name": "राम कुमार",
    "phone": "+91XXXXXXXXXX",
    "language": "hi",
    "education": "primary",
    "experience_years": 15
  },
  "plantation_info": {
    "plantation_id": "plantation_67890",
    "area_hectares": 2.5,
    "tree_count": 625,
    "plantation_age": 12,
    "varieties": ["RRII 105", "GT 1"],
    "location": {
      "latitude": 9.5916,
      "longitude": 76.5222,
      "elevation": 45,
      "soil_type": "laterite"
    }
  },
  "cooperative_membership": {
    "cooperative_id": "coop_456",
    "membership_number": "RV2023001",
    "status": "active"
  }
}
```

#### PUT /farmers/{farmer_id}
Update farmer profile

#### POST /farmers/{farmer_id}/plantation
Add new plantation

---

### 2.4 Agronomy & Diversification APIs

#### POST /agronomy/crop-recommendation
Get crop diversification recommendations

**Request:**
```json
{
  "farmer_id": "farmer_12345",
  "plantation_id": "plantation_67890",
  "analysis_type": "diversification",
  "parameters": {
    "available_area": 0.5,
    "investment_capacity": 50000,
    "risk_tolerance": "medium",
    "market_preference": "local"
  }
}
```

**Response:**
```json
{
  "recommendations": [
    {
      "crop": "black_pepper",
      "suitability_score": 0.92,
      "expected_roi": 1.8,
      "investment_required": 35000,
      "time_to_harvest": "3 years",
      "intercropping_compatibility": "excellent",
      "market_demand": "high",
      "reasons": [
        "Ideal climate conditions",
        "Good market prices",
        "Compatible with rubber trees"
      ]
    },
    {
      "crop": "pineapple",
      "suitability_score": 0.87,
      "expected_roi": 1.5,
      "investment_required": 25000,
      "time_to_harvest": "18 months",
      "intercropping_compatibility": "good",
      "market_demand": "medium"
    }
  ],
  "soil_analysis": {
    "ph": 6.2,
    "organic_matter": 3.1,
    "nitrogen": "medium",
    "phosphorus": "low",
    "potassium": "high"
  },
  "climate_suitability": {
    "temperature_range": "optimal",
    "rainfall_pattern": "suitable",
    "humidity": "ideal"
  }
}
```

#### GET /agronomy/yield-forecast/{plantation_id}
Get yield predictions for current season

#### POST /agronomy/soil-analysis
Submit soil test results and get recommendations

---

### 2.5 Mechanized Tapping APIs

#### GET /tapping/schedule/{plantation_id}
Get optimized tapping schedule

**Response:**
```json
{
  "plantation_id": "plantation_67890",
  "current_week": {
    "week_number": 23,
    "recommended_days": ["Monday", "Wednesday", "Friday"],
    "optimal_times": {
      "start": "06:00",
      "end": "10:00"
    },
    "weather_considerations": {
      "monday": "Clear - Proceed",
      "tuesday": "Rain expected - Skip",
      "wednesday": "Cloudy - Proceed with caution"
    }
  },
  "monthly_forecast": {
    "expected_yield": 125,
    "tapping_days": 18,
    "rest_days": 12,
    "maintenance_days": 1
  },
  "tree_health": {
    "healthy_trees": 580,
    "stressed_trees": 35,
    "resting_trees": 10,
    "recommendations": "Reduce tapping frequency for stressed trees"
  }
}
```

#### POST /tapping/service-providers
Find and book mechanized tapping services

**Request:**
```json
{
  "plantation_id": "plantation_67890",
  "service_type": "mechanized_tapping",
  "preferred_dates": ["2024-06-15", "2024-06-17"],
  "area_hectares": 2.5,
  "tree_count": 625,
  "budget_range": {
    "min": 5000,
    "max": 8000
  }
}
```

**Response:**
```json
{
  "available_providers": [
    {
      "provider_id": "provider_123",
      "company_name": "Kerala Rubber Mechanization Pvt Ltd",
      "rating": 4.7,
      "price_per_hectare": 2800,
      "total_cost": 7000,
      "availability": {
        "2024-06-15": "available",
        "2024-06-17": "available"
      },
      "equipment": ["Modern tapping machines", "Collection systems"],
      "experience_years": 8,
      "contact": {
        "phone": "+91XXXXXXXXXX",
        "manager": "സുരേഷ് കുമാർ"
      }
    }
  ],
  "booking_options": {
    "advance_booking_days": 7,
    "cancellation_policy": "24 hours notice",
    "payment_terms": "50% advance, 50% on completion"
  }
}
```

#### POST /tapping/book-service
Book mechanized tapping service

#### GET /tapping/equipment-maintenance
Get equipment maintenance schedules and alerts

---

### 2.6 Market & Supply Chain APIs

#### GET /market/prices/current
Get current rubber prices

**Response:**
```json
{
  "timestamp": "2024-06-15T10:30:00Z",
  "prices": {
    "rubber_sheet": {
      "grade": "RSS1",
      "price_per_kg": 185.50,
      "change_percent": 2.3,
      "trend": "increasing",
      "market": "Kottayam"
    },
    "latex": {
      "drc_60": {
        "price_per_kg": 165.00,
        "change_percent": 1.8,
        "trend": "stable"
      }
    }
  },
  "market_analysis": {
    "demand": "high",
    "supply": "moderate",
    "forecast": "Prices expected to remain stable for next 2 weeks",
    "factors": [
      "Increased export demand",
      "Seasonal production peak",
      "Favorable weather conditions"
    ]
  },
  "nearby_markets": [
    {
      "market_name": "Kottayam Rubber Market",
      "distance_km": 15,
      "price_difference": 0,
      "contact": "+91XXXXXXXXXX"
    }
  ]
}
```

#### POST /market/sell-request
Create a sell request for rubber

**Request:**
```json
{
  "farmer_id": "farmer_12345",
  "product_type": "rubber_sheet",
  "grade": "RSS1",
  "quantity_kg": 500,
  "quality_certificate": "cert_789",
  "expected_price": 185.00,
  "delivery_location": {
    "latitude": 9.5916,
    "longitude": 76.5222,
    "address": "Rubber Valley, Kottayam"
  },
  "availability_date": "2024-06-20"
}
```

#### GET /market/buyers
Find potential buyers

#### GET /market/logistics
Get logistics and transportation options

---

### 2.7 Community & Cooperative APIs

#### GET /community/dashboard/{cooperative_id}
Get community dashboard data

**Response:**
```json
{
  "cooperative_id": "coop_456",
  "overview": {
    "total_members": 125,
    "active_plantations": 98,
    "total_area_hectares": 245.5,
    "monthly_production_kg": 12500
  },
  "recent_activities": [
    {
      "type": "training_session",
      "title": "Mechanized Tapping Workshop",
      "date": "2024-06-10",
      "participants": 35,
      "status": "completed"
    },
    {
      "type": "bulk_purchase",
      "title": "Fertilizer Group Purchase",
      "date": "2024-06-08",
      "savings_percent": 15,
      "status": "delivered"
    }
  ],
  "upcoming_events": [
    {
      "type": "market_visit",
      "title": "Kottayam Market Price Discussion",
      "date": "2024-06-18",
      "time": "14:00",
      "location": "Community Center"
    }
  ],
  "collective_metrics": {
    "average_yield_per_hectare": 1250,
    "price_improvement_percent": 8.5,
    "cost_savings_annual": 125000,
    "training_completion_rate": 78
  }
}
```

#### POST /community/training/enroll
Enroll in training programs

#### GET /community/resources
Get shared resources and equipment

#### POST /community/decisions/vote
Participate in community voting

---

### 2.8 Climate & Sustainability APIs

#### GET /climate/weather/{location}
Get weather forecast and alerts

**Response:**
```json
{
  "location": {
    "latitude": 9.5916,
    "longitude": 76.5222,
    "name": "Rubber Valley, Kottayam"
  },
  "current_weather": {
    "temperature": 28.5,
    "humidity": 82,
    "rainfall_mm": 0,
    "wind_speed_kmh": 8,
    "uv_index": 6,
    "conditions": "Partly Cloudy"
  },
  "forecast_7_days": [
    {
      "date": "2024-06-15",
      "temperature_max": 32,
      "temperature_min": 24,
      "rainfall_probability": 60,
      "rainfall_mm": 15,
      "conditions": "Light Rain",
      "tapping_suitability": "not_recommended"
    }
  ],
  "alerts": [
    {
      "type": "heavy_rain",
      "severity": "moderate",
      "start_time": "2024-06-16T14:00:00Z",
      "end_time": "2024-06-16T20:00:00Z",
      "message": "Heavy rain expected. Avoid tapping activities.",
      "recommendations": [
        "Postpone tapping until weather clears",
        "Ensure proper drainage in plantation",
        "Check for waterlogging in low-lying areas"
      ]
    }
  ],
  "climate_insights": {
    "seasonal_pattern": "Pre-monsoon showers typical for this period",
    "long_term_trend": "Rainfall patterns shifting earlier by 2 weeks",
    "adaptation_suggestions": [
      "Consider drought-resistant intercropping",
      "Improve water harvesting systems"
    ]
  }
}
```

#### GET /climate/satellite/{plantation_id}
Get satellite-based plantation health analysis

#### POST /climate/sustainability-report
Generate sustainability assessment

---

## 3. WebSocket APIs for Real-time Communication

### 3.1 Voice Streaming
```
wss://api.plantai.gov.in/v1/voice/stream
```

**Connection Parameters:**
```json
{
  "farmer_id": "farmer_12345",
  "session_id": "session_67890",
  "language": "hi",
  "audio_format": "wav"
}
```

**Message Types:**
- `audio_chunk`: Streaming audio data
- `transcription`: Real-time speech-to-text
- `agent_response`: AI agent responses
- `session_end`: End conversation

### 3.2 IoT Data Streaming
```
wss://api.plantai.gov.in/v1/iot/stream
```

**Sensor Data Format:**
```json
{
  "sensor_id": "soil_sensor_123",
  "plantation_id": "plantation_67890",
  "timestamp": "2024-06-15T10:30:00Z",
  "data": {
    "soil_moisture": 65.2,
    "soil_temperature": 26.8,
    "ph": 6.1,
    "conductivity": 1.2
  }
}
```

---

## 4. Error Handling

### Standard Error Response Format
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "The request parameters are invalid",
    "details": {
      "field": "phone_number",
      "issue": "Invalid format. Expected +91XXXXXXXXXX"
    },
    "request_id": "req_12345",
    "timestamp": "2024-06-15T10:30:00Z"
  }
}
```

### Error Codes
- `AUTHENTICATION_FAILED`: Invalid credentials
- `AUTHORIZATION_DENIED`: Insufficient permissions
- `INVALID_REQUEST`: Malformed request
- `RESOURCE_NOT_FOUND`: Requested resource doesn't exist
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `SERVICE_UNAVAILABLE`: Temporary service outage
- `VALIDATION_ERROR`: Data validation failed
- `AGENT_TIMEOUT`: AI agent response timeout

---

## 5. Data Models

### 5.1 Farmer Model
```json
{
  "farmer_id": "string",
  "personal_info": {
    "name": "string",
    "phone": "string",
    "language": "string",
    "education": "string",
    "experience_years": "integer"
  },
  "plantation_info": {
    "plantation_id": "string",
    "area_hectares": "number",
    "tree_count": "integer",
    "plantation_age": "integer",
    "varieties": ["string"],
    "location": {
      "latitude": "number",
      "longitude": "number",
      "elevation": "number",
      "soil_type": "string"
    }
  },
  "preferences": {
    "notification_methods": ["voice", "sms", "whatsapp"],
    "preferred_language": "string",
    "privacy_settings": {
      "data_sharing": "boolean",
      "marketing_communications": "boolean"
    }
  }
}
```

### 5.2 Plantation Model
```json
{
  "plantation_id": "string",
  "owner_id": "string",
  "basic_info": {
    "area_hectares": "number",
    "tree_count": "integer",
    "plantation_age": "integer",
    "varieties": ["string"],
    "planting_density": "integer"
  },
  "location": {
    "latitude": "number",
    "longitude": "number",
    "elevation": "number",
    "state": "string",
    "district": "string",
    "village": "string"
  },
  "soil_data": {
    "type": "string",
    "ph": "number",
    "organic_matter": "number",
    "nutrients": {
      "nitrogen": "string",
      "phosphorus": "string",
      "potassium": "string"
    }
  },
  "production_data": {
    "annual_yield_kg": "number",
    "yield_per_hectare": "number",
    "tapping_frequency": "integer",
    "quality_grade": "string"
  }
}
```

### 5.3 Voice Session Model
```json
{
  "session_id": "string",
  "farmer_id": "string",
  "start_time": "datetime",
  "end_time": "datetime",
  "language": "string",
  "conversation": [
    {
      "timestamp": "datetime",
      "type": "farmer_input",
      "content": {
        "text": "string",
        "audio_url": "string",
        "confidence": "number"
      }
    },
    {
      "timestamp": "datetime",
      "type": "agent_response",
      "agent": "string",
      "content": {
        "text": "string",
        "audio_url": "string",
        "data": "object"
      }
    }
  ],
  "summary": {
    "intents": ["string"],
    "actions_taken": ["string"],
    "satisfaction_score": "number"
  }
}
```

---

## 6. API Integration Examples

### 6.1 Python SDK Example
```python
import plantai

# Initialize client
client = plantai.Client(
    api_key="your_api_key",
    base_url="https://api.plantai.gov.in/v1"
)

# Authenticate farmer
auth_response = client.auth.login(
    phone_number="+91XXXXXXXXXX",
    otp="123456",
    language="hi"
)

# Get crop recommendations
recommendations = client.agronomy.get_crop_recommendations(
    farmer_id="farmer_12345",
    plantation_id="plantation_67890",
    analysis_type="diversification"
)

# Process voice input
voice_response = client.voice.process_audio(
    audio_file="farmer_query.wav",
    language="hi",
    session_id="session_12345"
)
```

### 6.2 JavaScript SDK Example
```javascript
import PlantAI from '@plantai/sdk';

const client = new PlantAI({
  apiKey: 'your_api_key',
  baseURL: 'https://api.plantai.gov.in/v1'
});

// Voice streaming example
const voiceStream = client.voice.createStream({
  farmerId: 'farmer_12345',
  language: 'hi'
});

voiceStream.on('transcription', (text) => {
  console.log('Farmer said:', text);
});

voiceStream.on('response', (response) => {
  console.log('Agent response:', response.text);
  // Play audio response
  playAudio(response.audio_url);
});
```

---

## 7. Rate Limiting and Quotas

### Rate Limits by Endpoint Category
- **Authentication**: 10 requests/minute
- **Voice Processing**: 100 requests/hour
- **Data Queries**: 1000 requests/hour
- **Bulk Operations**: 10 requests/hour
- **WebSocket Connections**: 5 concurrent connections

### Quota Management
```json
{
  "farmer_id": "farmer_12345",
  "quotas": {
    "voice_minutes_monthly": 300,
    "voice_minutes_used": 45,
    "api_calls_daily": 500,
    "api_calls_used": 127,
    "storage_mb": 100,
    "storage_used": 23
  },
  "reset_dates": {
    "daily": "2024-06-16T00:00:00Z",
    "monthly": "2024-07-01T00:00:00Z"
  }
}
```

---

## 8. Webhook APIs

### 8.1 Webhook Registration
```
POST /webhooks/register
```

**Request:**
```json
{
  "url": "https://your-app.com/webhooks/plantai",
  "events": ["tapping_scheduled", "weather_alert", "price_update"],
  "secret": "webhook_secret_key",
  "active": true
}
```

### 8.2 Webhook Events
- `tapping_scheduled`: New tapping schedule created
- `weather_alert`: Severe weather warning
- `price_update`: Significant price change
- `training_reminder`: Upcoming training session
- `equipment_maintenance`: Maintenance due alert

### 8.3 Webhook Payload Example
```json
{
  "event": "weather_alert",
  "timestamp": "2024-06-15T10:30:00Z",
  "data": {
    "alert_type": "heavy_rain",
    "severity": "high",
    "affected_areas": ["Kottayam", "Idukki"],
    "start_time": "2024-06-16T14:00:00Z",
    "recommendations": [
      "Postpone tapping activities",
      "Ensure proper drainage"
    ]
  },
  "signature": "sha256=..."
}
```

---

This API specification provides comprehensive documentation for integrating with the PlantAI multi-agent system, enabling developers to build applications that leverage AI-powered plantation management capabilities.