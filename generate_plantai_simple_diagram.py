"""
PlantAI MVP Architecture Diagram Generator (Simplified)
Generates a clean, focused AWS architecture diagram for the MVP
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import ECS, Lambda
from diagrams.aws.database import RDS, ElastiCache
from diagrams.aws.network import ELB, APIGateway
from diagrams.aws.storage import S3
from diagrams.aws.iot import IotCore
from diagrams.onprem.client import Users
from diagrams.onprem.database import MongoDB, Influxdb
from diagrams.onprem.inmemory import Redis

# Configure diagram for clarity
graph_attr = {
    "fontsize": "16",
    "bgcolor": "white",
    "pad": "1.0",
    "splines": "spline",
    "nodesep": "1.0",
    "ranksep": "1.5"
}

node_attr = {
    "fontsize": "13",
    "height": "1.5",
    "width": "1.5"
}

with Diagram(
    "PlantAI MVP - Core Architecture",
    filename="plantai_mvp_simple",
    show=False,
    direction="LR",
    graph_attr=graph_attr,
    node_attr=node_attr
):
    
    # Users
    farmers = Users("Farmers\n(Voice Interface)")
    
    # Edge Layer
    with Cluster("Edge Computing"):
        edge = Lambda("Voice Processing\n+ Local Cache")
        iot = IotCore("IoT Sensors")
    
    # API Layer
    api = APIGateway("API Gateway")
    lb = ELB("Load Balancer")
    
    # Core Services
    with Cluster("Agent Services (ECS)"):
        coordinator = ECS("Agent\nCoordinator")
        
        with Cluster("Essential Agents"):
            farmer_agent = ECS("Farmer\nAgent")
            agronomy = ECS("Agronomy\nAgent")
            tapping = ECS("Tapping\nAgent")
            market = ECS("Market\nAgent")
    
    # Data Layer
    with Cluster("Data Storage"):
        postgres = RDS("PostgreSQL\nCore Data")
        influx = Influxdb("InfluxDB\nSensor Data")
        mongo = MongoDB("MongoDB\nInteractions")
        cache = ElastiCache("Redis\nCache")
    
    # External APIs
    with Cluster("External Data"):
        weather = S3("Weather API\n(IMD)")
        prices = S3("Market Prices\n(Rubber Board)")
    
    # Main flow
    farmers >> Edge(color="blue", style="bold") >> edge
    edge >> Edge(color="blue") >> api
    iot >> Edge(color="green") >> api
    
    api >> lb >> coordinator
    
    # Agent coordination
    coordinator >> farmer_agent
    farmer_agent >> agronomy
    farmer_agent >> tapping
    farmer_agent >> market
    
    # Data connections
    coordinator >> cache
    coordinator >> postgres
    agronomy >> influx
    market >> mongo
    
    # External data
    agronomy >> weather
    market >> prices

print("✅ Simplified PlantAI MVP diagram generated!")
print("📁 Output file: plantai_mvp_simple.png")
