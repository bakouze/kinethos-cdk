# kinethos_cdk/kinethos_cdk/constructs/telegram_webhook.py
from __future__ import annotations
from typing import Dict, Optional
from aws_cdk import Duration
from constructs import Construct

from aws_cdk.aws_apigatewayv2_alpha import (
    HttpApi, HttpMethod, CorsPreflightOptions, CorsHttpMethod
)
from aws_cdk.aws_apigatewayv2_integrations_alpha import HttpLambdaIntegration

# NEW import:
from aws_cdk.aws_lambda_python_alpha import PythonFunction
from aws_cdk import aws_lambda as _lambda

class TelegramWebhook(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        lambda_code_path: str,
        env_vars: Optional[Dict[str, str]] = None,
        memory_size: int = 256,
        timeout_seconds: int = 10,
        webhook_path: str = "/bot",
        enable_cors: bool = True,
    ) -> None:
        super().__init__(scope, construct_id)

        # Bundles your code + deps from services/telegram_bot/requirements.txt inside a Docker build
        fn = PythonFunction(
            self,
            "Handler",
            entry=lambda_code_path,                 # directory with lambda_function.py + requirements.txt
            index="lambda_function.py",            # filename
            handler="lambda_handler",              # function name
            runtime=_lambda.Runtime.PYTHON_3_11,
            memory_size=memory_size,
            timeout=Duration.seconds(timeout_seconds),
            environment=env_vars or {},
        )

        integration = HttpLambdaIntegration("TelegramIntegration", fn)
        cors_opts = CorsPreflightOptions(allow_origins=["*"], allow_methods=[CorsHttpMethod.ANY]) if enable_cors else None
        http_api = HttpApi(self, "TelegramHttpApi", cors_preflight=cors_opts)
        http_api.add_routes(path=webhook_path, methods=[HttpMethod.POST], integration=integration)

        self.function = fn
        self.http_api = http_api
        self.webhook_url = f"{http_api.api_endpoint}{webhook_path}"