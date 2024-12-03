import boto3
from botocore.exceptions import ClientError
import datetime
from config import settings


def get_utc_now():
    """
    Simply returns datetime.datetime.utcnow(). This function makes testing easier, since datetime is a built-in type
    that can't be easily mocked.
    :return: datetime object with current UTC time
    """
    return datetime.datetime.utcnow()


def get_secret(secret_name, region_name="us-east-1"):
    # Create a Secrets Manager client
    boto_session = boto3.session.Session(profile_name=settings.AWS_PROFILE)
    client = boto_session.client(service_name="secretsmanager", region_name=region_name)

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    # Decrypts secret using the associated KMS key.
    secret = get_secret_value_response["SecretString"]

    return secret
