from __future__ import annotations
from aws_cdk import (
    Duration,
    aws_iam as iam,
    aws_s3 as s3,
    aws_logs as logs,
    aws_kinesisfirehose as firehose,  # L1 CfnDeliveryStream
)
from constructs import Construct

class UpdatesStorage(Construct):
    """
    Creates:
      - S3 bucket for raw Telegram updates
      - Kinesis Data Firehose delivery stream -> S3 (GZIP, 1min/5MB buffering)
      - CloudWatch Logs for Firehose

    Exposes:
      - bucket (s3.Bucket)
      - delivery_stream (firehose.CfnDeliveryStream)
      - delivery_stream_name (str)
    """
    def __init__(self, scope: Construct, cid: str, *, bucket_prefix: str = "raw/") -> None:
        super().__init__(scope, cid)

        self.bucket = s3.Bucket(
            self, "UpdatesBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    expiration=Duration.days(365),  # keep 1 year (tweak as you like)
                )
            ],
        )

        # Logs for Firehose
        lg = logs.LogGroup(self, "FirehoseLogGroup", retention=logs.RetentionDays.ONE_MONTH)
        ls = logs.LogStream(self, "FirehoseLogStream", log_group=lg)

        # Role Firehose assumes to write to S3 + logs
        fh_role = iam.Role(
            self, "FirehoseRole",
            assumed_by=iam.ServicePrincipal("firehose.amazonaws.com"),
        )
        # Allow Firehose to write to this bucket
        self.bucket.grant_read_write(fh_role)
        # Minimal extra S3 perms Firehose needs
        fh_role.add_to_policy(iam.PolicyStatement(
            actions=[
                "s3:ListBucket", "s3:GetBucketLocation",
                "s3:ListBucketMultipartUploads", "s3:ListMultipartUploadParts",
                "s3:AbortMultipartUpload",
            ],
            resources=[self.bucket.bucket_arn],
        ))
        # Allow logging
        fh_role.add_to_policy(iam.PolicyStatement(
            actions=["logs:PutLogEvents", "logs:CreateLogStream", "logs:DescribeLogStreams"],
            resources=[lg.log_group_arn, f"{lg.log_group_arn}:*"],
        ))

        # Firehose -> S3 destination (L1 for maximum compatibility)
        self.delivery_stream = firehose.CfnDeliveryStream(
            self, "UpdatesFirehose",
            delivery_stream_type="DirectPut",
            extended_s3_destination_configuration=firehose.CfnDeliveryStream.ExtendedS3DestinationConfigurationProperty(
                bucket_arn=self.bucket.bucket_arn,
                role_arn=fh_role.role_arn,
                buffering_hints=firehose.CfnDeliveryStream.BufferingHintsProperty(
                    interval_in_seconds=60, size_in_m_bs=5
                ),
                compression_format="GZIP",
                prefix=bucket_prefix,                  # e.g. "raw/"
                error_output_prefix="bad/",           # failed deliveries
                cloud_watch_logging_options=firehose.CfnDeliveryStream.CloudWatchLoggingOptionsProperty(
                    enabled=True,
                    log_group_name=lg.log_group_name,
                    log_stream_name=ls.log_stream_name,
                ),
            ),
        )

        self.delivery_stream_name = self.delivery_stream.ref