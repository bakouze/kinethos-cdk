from __future__ import annotations
from aws_cdk import (
    aws_dynamodb as ddb,
    RemovalPolicy,
)
from constructs import Construct

class UpdatesTable(Construct):
    """
    Creates a DynamoDB table for operational queries:
      - PK: pk (e.g., CHAT#{chat_id})
      - SK: sk (e.g., TS#{epoch_ms})
      - TTL: expire_at (epoch seconds)
      - GSI1 for idempotency lookup by update_id if you want (optional)
    """
    def __init__(self, scope: Construct, cid: str, *, with_gsi: bool = True) -> None:
        super().__init__(scope, cid)

        self.table = ddb.Table(
            self, "BotUpdates",
            partition_key=ddb.Attribute(name="pk", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="sk", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="expire_at",
            removal_policy=RemovalPolicy.DESTROY,  # for dev; change to RETAIN in prod
        )

        if with_gsi:
            self.table.add_global_secondary_index(
                index_name="gsi1",
                partition_key=ddb.Attribute(name="gsi1pk", type=ddb.AttributeType.STRING),
                sort_key=ddb.Attribute(name="gsi1sk", type=ddb.AttributeType.STRING),
                projection_type=ddb.ProjectionType.ALL,
            )