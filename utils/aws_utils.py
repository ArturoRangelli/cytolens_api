import boto3
from boto3 import resource
from boto3.s3.transfer import TransferConfig
from botocore.client import Config
from botocore.exceptions import ClientError

# Use signature v4 for KMS-encrypted buckets
s3_client = boto3.client('s3', config=Config(signature_version='s3v4'))


def copy_file(bucket: str, key_src: str, key_dst: str) -> None:
    """
    Copy an object within the same S3 bucket, supporting large files via multipart copy.
    """
    s3 = resource("s3")

    config = TransferConfig(
        multipart_threshold=5 * 1024**3,  # Files above 5 GB use multipart
        multipart_chunksize=64 * 1024**2,  # Each part = 64 MB
        max_concurrency=10,  # Number of threads
    )

    copy_source = {"Bucket": bucket, "Key": key_src}
    s3.meta.client.copy(copy_source, bucket, key_dst, Config=config)


def delete_file(bucket: str, key: str) -> None:
    """
    Delete a file from S3 given its bucket and object key.
    Raises an exception if the delete fails.
    """
    s3_client.delete_object(Bucket=bucket, Key=key)


def file_exists(bucket: str, key: str) -> bool:
    """
    Check if a file (object) exists in an S3 bucket.
    """
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        else:
            # Raise other errors (e.g., permission denied, wrong bucket)
            raise


def download_file(bucket: str, key: str, local_path: str) -> None:
    """
    Download a file from S3 to a local path.
    """
    config = TransferConfig(
        multipart_threshold=5 * 1024**3,  # Files above 5 GB use multipart
        multipart_chunksize=64 * 1024**2,  # Each part = 64 MB
        max_concurrency=10,  # Number of threads
    )
    
    s3_client.download_file(
        Bucket=bucket,
        Key=key,
        Filename=local_path,
        Config=config
    )


def create_multipart_upload(bucket: str, key: str) -> str:
    """
    Initialize a multipart upload and return the upload ID.
    """
    response = s3_client.create_multipart_upload(
        Bucket=bucket,
        Key=key
    )
    return response['UploadId']


def generate_multipart_presigned_url(
    bucket: str, key: str, upload_id: str, part_number: int, expiry: int = 7200
) -> str:
    """
    Generate a presigned URL for uploading a part in multipart upload.
    """
    return s3_client.generate_presigned_url(
        ClientMethod='upload_part',
        Params={
            'Bucket': bucket,
            'Key': key,
            'UploadId': upload_id,
            'PartNumber': part_number
        },
        ExpiresIn=expiry
    )


def complete_multipart_upload(bucket: str, key: str, upload_id: str, parts: list) -> None:
    """
    Complete a multipart upload with the provided parts.
    """
    s3_client.complete_multipart_upload(
        Bucket=bucket,
        Key=key,
        UploadId=upload_id,
        MultipartUpload={'Parts': parts}
    )


def abort_multipart_upload(bucket: str, key: str, upload_id: str) -> None:
    """
    Abort a multipart upload.
    """
    try:
        s3_client.abort_multipart_upload(
            Bucket=bucket,
            Key=key,
            UploadId=upload_id
        )
    except ClientError:
        pass  # Already aborted or doesn't exist
