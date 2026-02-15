"""
PlantAI MVP Deployment Architecture
Shows the deployment topology with edge, cloud, and external services
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import EC2, ECS
from diagrams.aws.database import RDS, ElastiCache
from diagrams.aws.network import ELB, APIGateway, VPC, PrivateSubnet, PublicSubnet
from diagrams.aws.storage import S3
from diagrams.aws.security import IAM, SecretsManager
from diagrams.onprem.client import Users
from diagrams.onprem.compute import Server
from diagrams.onprem.network import Internet

graph_attr = {
    "fontsize": "15",
    "bgcolor": "white",
    "pad": "1.0",
    "splines": "ortho"
}

with Diagram(
    "PlantAI MVP - Deployment Architecture",
    filename="plantai_deployment",
    show=False,
    direction="TB",
    graph_attr=graph_attr
):
    
    # Users and Edge
    farmers = Users("Farmers\n(Rural Areas)")
    internet = Internet("Internet")
    
    with Cluster("Village Edge Computing"):
        edge_device = Server("Edge Device\nRaspberry Pi 4")
        edge_services = EC2("Voice Processing\nOffline Cache")
    
    # AWS Cloud
    with Cluster("AWS Cloud (Mumbai Region)"):
        
        # Public subnet
        with Cluster("Public Subnet"):
            api_gateway = APIGateway("API Gateway")
            alb = ELB("Application\nLoad Balancer")
        
        # Private subnet - Application
        with Cluster("Private Subnet - Application"):
            with Cluster("ECS Fargate Cluster"):
                coordinator = ECS("Coordinator\nService")
                agents = [
                    ECS("Farmer\nAgent"),
                    ECS("Agronomy\nAgent"),
                    ECS("Tapping\nAgent"),
                    ECS("Market\nAgent")
                ]
        
        # Private subnet - Data
        with Cluster("Private Subnet - Data"):
            postgres = RDS("RDS PostgreSQL\nMulti-AZ")
            redis = ElastiCache("ElastiCache\nRedis Cluster")
            s3 = S3("S3 Bucket\nData Lake")
        
        # Security
        with Cluster("Security & Secrets"):
            iam = IAM("IAM Roles")
            secrets = SecretsManager("Secrets\nManager")
    
    # External Services
    with Cluster("External APIs"):
        imd = Server("IMD Weather\nAPI")
        rubber = Server("Rubber Board\nAPI")
    
    # Connections
    farmers >> Edge(label="Voice/Mobile") >> edge_device
    edge_device >> edge_services
    edge_services >> internet
    internet >> api_gateway
    
    api_gateway >> alb
    alb >> coordinator
    
    coordinator >> agents[0]
    coordinator >> agents[1]
    coordinator >> agents[2]
    coordinator >> agents[3]
    
    for agent in agents:
        agent >> postgres
        agent >> redis
        agent >> s3
    
    coordinator >> iam
    coordinator >> secrets
    
    agents[1] >> Edge(label="Weather Data") >> imd
    agents[3] >> Edge(label="Market Prices") >> rubber

print("✅ PlantAI Deployment Architecture diagram generated!")
print("📁 Output file: plantai_deployment.png")
