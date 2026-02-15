"""
PlantAI MVP Architecture Diagram Generator
Generates AWS architecture diagram for the PlantAI multi-agent system
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import EC2, ECS, Lambda
from diagrams.aws.database import RDS, Dynamodb, ElastiCache
from diagrams.aws.network import ELB, APIGateway, CloudFront
from diagrams.aws.storage import S3
from diagrams.aws.integration import SQS, SNS
from diagrams.aws.analytics import Kinesis
from diagrams.aws.ml import Sagemaker
from diagrams.aws.iot import IotCore
from diagrams.onprem.client import Users, Client
from diagrams.onprem.database import MongoDB, PostgreSQL, Influxdb
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.network import Nginx
from diagrams.programming.language import Python, NodeJS
from diagrams.custom import Custom

# Configure diagram
graph_attr = {
    "fontsize": "14",
    "bgcolor": "white",
    "pad": "0.5",
    "splines": "ortho"
}

node_attr = {
    "fontsize": "12",
    "height": "1.2",
    "width": "1.2"
}

edge_attr = {
    "fontsize": "10"
}

with Diagram(
    "PlantAI MVP Architecture - AWS Deployment",
    filename="plantai_mvp_architecture",
    show=False,
    direction="TB",
    graph_attr=graph_attr,
    node_attr=node_attr,
    edge_attr=edge_attr
):
    
    # User Layer
    with Cluster("Users"):
        farmers = Users("Farmers\n(Voice + Mobile)")
        cooperatives = Client("Cooperative\nManagers")
    
    # Edge Computing Layer
    with Cluster("Edge Computing (Village Level)"):
        edge_device = EC2("Edge Device\nRaspberry Pi")
        voice_local = Lambda("Voice Processing\nWhisper STT/TTS")
        iot_gateway = IotCore("IoT Gateway\nMQTT Broker")
        local_cache = Redis("Local Cache\nRedis")
    
    # API Gateway & Load Balancing
    cdn = CloudFront("CloudFront CDN")
    api_gateway = APIGateway("API Gateway\nREST + WebSocket")
    load_balancer = ELB("Application\nLoad Balancer")
    
    # Core Application Services
    with Cluster("Core Services (ECS Fargate)"):
        with Cluster("Orchestration Layer"):
            coordinator = ECS("Agent Coordinator\nFastAPI")
            knowledge_graph = ECS("Knowledge Graph\nNeo4j Driver")
            data_access = ECS("Data Access Layer\nPython")
        
        with Cluster("Essential Agents"):
            farmer_agent = ECS("Farmer Agent\nVoice + Context")
            agronomy_agent = ECS("Agronomy Agent\nCrop Recommendations")
            tapping_agent = ECS("Tapping Agent\nSchedule Optimization")
            market_agent = ECS("Market Agent\nPrice Intelligence")
        
        with Cluster("Voice Processing Pipeline"):
            stt_service = ECS("Speech-to-Text\nWhisper")
            nlu_service = ECS("NLU Engine\nspaCy")
            tts_service = ECS("Text-to-Speech\nFestival")
    
    # Data Storage Layer
    with Cluster("Data Storage"):
        postgres = RDS("PostgreSQL\nFarmers + Plantations")
        influxdb = Influxdb("InfluxDB\nSensor Time Series")
        mongodb = MongoDB("MongoDB\nVoice Interactions")
        neo4j = EC2("Neo4j\nKnowledge Graph")
        redis_cache = ElastiCache("Redis Cache\nSession + Queries")
    
    # ML & Analytics
    with Cluster("ML & Analytics"):
        ml_models = Sagemaker("ML Models\nCrop Predictions")
        s3_storage = S3("S3 Storage\nModels + Data Lake")
    
    # Message Queue & Streaming
    with Cluster("Event Processing"):
        message_queue = SQS("SQS Queue\nAgent Messages")
        event_stream = Kinesis("Kinesis Stream\nIoT Data")
        notifications = SNS("SNS\nAlerts + Notifications")
    
    # External Integrations
    with Cluster("External APIs"):
        imd_api = EC2("IMD Weather API\nGovernment Data")
        rubber_board = EC2("Rubber Board API\nMarket Prices")
        sms_gateway = SNS("SMS Gateway\nTwilio/AWS SNS")
    
    # User to Edge connections
    farmers >> Edge(label="Voice\nCommands") >> edge_device
    farmers >> Edge(label="Mobile\nApp") >> cdn
    cooperatives >> Edge(label="Web\nDashboard") >> cdn
    
    # Edge to Cloud
    edge_device >> voice_local
    edge_device >> iot_gateway
    edge_device >> local_cache
    voice_local >> Edge(label="Processed\nAudio") >> api_gateway
    iot_gateway >> Edge(label="Sensor\nData") >> event_stream
    
    # API Gateway flow
    cdn >> api_gateway
    api_gateway >> load_balancer
    load_balancer >> coordinator
    
    # Orchestration connections
    coordinator >> knowledge_graph
    coordinator >> data_access
    coordinator >> farmer_agent
    
    # Agent interactions
    farmer_agent >> Edge(label="Crop\nQuery") >> agronomy_agent
    farmer_agent >> Edge(label="Tapping\nQuery") >> tapping_agent
    farmer_agent >> Edge(label="Market\nQuery") >> market_agent
    agronomy_agent >> Edge(label="Weather\nData") >> tapping_agent
    tapping_agent >> Edge(label="Price\nData") >> market_agent
    
    # Voice processing flow
    farmer_agent >> stt_service
    stt_service >> nlu_service
    nlu_service >> farmer_agent
    farmer_agent >> tts_service
    
    # Knowledge graph to databases
    knowledge_graph >> postgres
    knowledge_graph >> influxdb
    knowledge_graph >> mongodb
    knowledge_graph >> neo4j
    knowledge_graph >> redis_cache
    
    # Data access to external APIs
    data_access >> imd_api
    data_access >> rubber_board
    data_access >> redis_cache
    
    # ML integration
    agronomy_agent >> ml_models
    ml_models >> s3_storage
    
    # Event processing
    coordinator >> message_queue
    event_stream >> data_access
    coordinator >> notifications
    notifications >> sms_gateway
    
    # Agent to message queue
    farmer_agent >> message_queue
    agronomy_agent >> message_queue
    tapping_agent >> message_queue
    market_agent >> message_queue

print("✅ PlantAI MVP Architecture diagram generated successfully!")
print("📁 Output file: plantai_mvp_architecture.png")
print("\nTo view the diagram, open: plantai_mvp_architecture.png")
