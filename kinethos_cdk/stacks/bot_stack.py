from __future__ import annotations

from aws_cdk import (
    Stack,
    CfnOutput,
    aws_iam as iam,
)
from constructs import Construct

from kinethos_cdk.constructs.telegram_webhook import TelegramWebhook
from kinethos_cdk.constructs.updates_storage import UpdatesStorage
from kinethos_cdk.constructs.updates_table import UpdatesTable


class BotStack(Stack):
    """
    Hosts the Telegram webhook:
      - Lambda (Python 3.11) at services/telegram_bot/lambda_function.py
      - HTTP API (API Gateway v2) with POST /bot → Lambda
      - Emits WebhookUrl output for setWebhook

    Args passed from app.py:
      - telegram_token: str
      - webhook_secret: str
      - lambda_code_path: str (default: services/telegram_bot)
      - webhook_path: str (default: /bot)
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        telegram_token: str,
        webhook_secret: str,
        lambda_code_path: str = "kinethos_cdk/services/telegram_bot",
        webhook_path: str = "/bot",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Basic validation to avoid deploying a broken stack
        if not telegram_token:
            raise ValueError(
                "telegram_token is empty. Pass -c telegramToken=... or set TELEGRAM_TOKEN."
            )
        if not webhook_secret:
            raise ValueError(
                "webhook_secret is empty. Pass -c webhookSecret=... or set WEBHOOK_SECRET_TOKEN."
            )

        # 1) Webhook Lambda + API
        webhook = TelegramWebhook(
            self,
            "TelegramWebhook",
            lambda_code_path=lambda_code_path,
            env_vars={
                "TELEGRAM_TOKEN": telegram_token,
                "WEBHOOK_SECRET_TOKEN": webhook_secret,
            },
            webhook_path=webhook_path,
        )

        # Tidy up logs (optional): set default retention on the function's log group
        # If you prefer to configure this in the construct, you can move it there.
        # if webhook.function.log_group is not None:
            # webhook.function.log_group.apply_removal_policy(self.removal_policy)  # inherit
            # webhook.function.log_group.set_retention(logs.RetentionDays.TWO_WEEKS)
            
        # 2) Storage: S3 + Firehose
        storage = UpdatesStorage(self, "UpdatesStorage", bucket_prefix="raw/")
        # Allow the Lambda to put records into Firehose
        webhook.function.add_to_role_policy(iam.PolicyStatement(
            actions=["firehose:PutRecord", "firehose:PutRecordBatch"],
            resources=[f"arn:aws:firehose:{self.region}:{self.account}:deliverystream/{storage.delivery_stream_name}"],
        ))

        # 3) DynamoDB for operational queries
        ddb = UpdatesTable(self, "UpdatesTable")
        ddb.table.grant_write_data(webhook.function)  # PutItem

        # 4) Pass names to the Lambda as env vars
        webhook.function.add_environment("FIREHOSE_STREAM_NAME", storage.delivery_stream_name)
        webhook.function.add_environment("DDB_TABLE_NAME", ddb.table.table_name)


        # Handy attribute for app.py to export
        self.webhook_url = webhook.webhook_url

        # Also output it directly from this stack
        CfnOutput(self, "WebhookUrl", value=self.webhook_url, description="Telegram webhook URL")
        CfnOutput(self, "S3BucketName", value=storage.bucket.bucket_name)
        CfnOutput(self, "FirehoseStreamName", value=storage.delivery_stream_name)
        CfnOutput(self, "DynamoTableName", value=ddb.table.table_name)