import boto3
from brownie import *
from rich.console import Console

from config.env_config import env_config

console = Console()


def upload(fileName):
    upload_bucket = "badger-json"
    upload_file_key = "rewards/" + fileName

    print("Uploading file to s3/" + upload_file_key)

    s3 = boto3.client(
        "s3",
        aws_access_key_id=env_config.aws_access_key_id,
        aws_secret_access_key=env_config.aws_secret_access_key,
    )
    s3.upload_file(fileName, upload_bucket, upload_file_key)
