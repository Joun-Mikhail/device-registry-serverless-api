import os
import pytest
import boto3
from moto import mock_aws


@pytest.fixture(autouse=True)
def aws_credentials():
    """Prevent any real AWS calls during tests."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "eu-central-1"


@pytest.fixture
def dynamodb_table(aws_credentials):
    """Create a mock DynamoDB table for the duration of a test."""
    with mock_aws():
        client = boto3.client("dynamodb", region_name="eu-central-1")
        client.create_table(
            TableName="device-registry-dev",
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[{"AttributeName": "deviceId", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "deviceId", "KeyType": "HASH"}],
        )
        os.environ["DEVICES_TABLE"] = "device-registry-dev"
        yield
