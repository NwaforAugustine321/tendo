from app.insight_recommender.agents.risk import agent as risk_agent
from app.insight_recommender.agents.recommendation import agent as recommendation_agent
from app.insight_recommender.agents.trend import agent as trend_agent
from app.insight_recommender.agents.business_health import agent as business_health_agent
from app.insight_recommender.agents.customer import agent as customer_agent
from app.insight_recommender.agents.inventory import agent as inventory_agent
from app.insight_recommender.agents.operations import agent as operations_agent

ALL_INSIGHT_AGENTS = [
    risk_agent,
    recommendation_agent,
    trend_agent,
    business_health_agent,
    customer_agent,
    inventory_agent,
    operations_agent,
]
