from kafka import KafkaConsumer
from botocore.client import Config
import requests
import boto3
from pathlib import Path
import tempfile
import os
import logging
import json
from urllib.parse import unquote_plus, quote


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger("tendo-kafka-consumer")


KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "tendo-kafka:9092",
)

KAFKA_TOPIC = os.getenv(
    "KAFKA_TOPIC",
    "minio-events",
)

CONSUMER_GROUP = os.getenv(
    "CONSUMER_GROUP",
    "nvingest-consumer-group",
)

MINIO_ENDPOINT = os.getenv(
    "MINIO_ENDPOINT",
    "tendo-minio:9000",
)

MINIO_PUBLIC_ENDPOINT = os.getenv(
    "MINIO_PUBLIC_ENDPOINT",
    "http://localhost:9000",
)

MINIO_ACCESS_KEY = os.getenv(
    "MINIO_ACCESS_KEY",
    "minioadmin",
)

MINIO_SECRET_KEY = os.getenv(
    "MINIO_SECRET_KEY",
    "minioadmin",
)

MINIO_SECURE = os.getenv(
    "MINIO_SECURE",
    "false",
).lower() == "true"

APPLICATION_BASE_URL = os.getenv(
    "APPLICATION_BASE_URL",
    "http://me:8000",
)

INGESTION_WEBHOOK_PATH = os.getenv(
    "INGESTION_WEBHOOK_PATH",
    "/api/pipeline/webhook/ingestion",
)


def create_minio_client():
    protocol = "https" if MINIO_SECURE else "http"

    return boto3.client(
        "s3",
        endpoint_url=f"{protocol}://{MINIO_ENDPOINT}",
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
    )


def get_collection_name(
    bucket: str,
    object_key: str,
) -> str:
    parts = Path(object_key).parts

    if len(parts) > 1:
        namespace = parts[0]
    else:
        namespace = bucket

    namespace = namespace.strip().lower()

    allowed = []

    for char in namespace:
        if char.isalnum() or char in ("_", "-"):
            allowed.append(char)
        else:
            allowed.append("_")

    namespace = "".join(allowed)

    return namespace[:255] or bucket


def get_document_identifiers(
    bucket: str,
    object_key: str,
):
    parts = Path(object_key).parts

    if len(parts) >= 3:
        business_id = parts[0]
        document_id = parts[1]
    elif len(parts) == 2:
        business_id = parts[0]
        document_id = Path(parts[1]).stem
    else:
        business_id = bucket
        document_id = Path(object_key).stem

    return business_id, document_id


def upload_to_application(
    file_path: str,
    bucket: str,
    object_key: str,
    collection_name: str,
    content_type: str,
):
    business_id, document_id = get_document_identifiers(
        bucket,
        object_key,
    )

    url = (
        f"{APPLICATION_BASE_URL.rstrip('/')}"
        f"{INGESTION_WEBHOOK_PATH}"
    )

    logger.info(
        "Sending document to application: "
        "business_id=%s document_id=%s collection=%s",
        business_id,
        document_id,
        collection_name,
    )

    try:
        with open(file_path, "rb") as file:
            response = requests.post(
                url,
                files={
                    "file": (
                        Path(object_key).name,
                        file,
                        content_type or "application/octet-stream",
                    )
                },
                data={
                    "business_id": business_id,
                    "document_id": document_id,
                    "collection_name": collection_name,
                    "bucket": bucket,
                    "object_key": object_key,
                },
                timeout=3600,
            )

    except requests.exceptions.ConnectionError as exc:
        logger.error(
            "Application is unreachable at %s. "
            "Event will be marked as failed and Kafka offset "
            "will still be committed.",
            url,
        )

        return {
            "status": "failed",
            "error": "application_unreachable",
            "message": str(exc),
        }

    except requests.exceptions.Timeout as exc:
        logger.error(
            "Application ingestion request timed out at %s. "
            "Event will be marked as failed and Kafka offset "
            "will still be committed.",
            url,
        )

        return {
            "status": "failed",
            "error": "application_timeout",
            "message": str(exc),
        }

    except requests.exceptions.RequestException as exc:
        logger.error(
            "Application ingestion request failed: %s. "
            "Event will be marked as failed and Kafka offset "
            "will still be committed.",
            exc,
        )

        return {
            "status": "failed",
            "error": "application_request_failed",
            "message": str(exc),
        }

    if not response.ok:
        logger.error(
            "Application ingestion failed: HTTP %s: %s",
            response.status_code,
            response.text,
        )

        return {
            "status": "failed",
            "error": "application_ingestion_failed",
            "http_status": response.status_code,
            "message": response.text,
        }

    logger.info(
        "Application ingestion succeeded: HTTP %s",
        response.status_code,
    )

    return {
        "status": "uploaded",
        "http_status": response.status_code,
        "response": response.text,
    }


def generate_document_url(
    bucket: str,
    object_key: str,
) -> str:
    encoded_key = quote(
        object_key,
        safe="/",
    )

    return (
        f"{MINIO_PUBLIC_ENDPOINT.rstrip('/')}/"
        f"{bucket}/"
        f"{encoded_key}"
    )


def process_event(
    event: dict,
    minio_client,
):
    records = event.get("Records", [])

    if not records:
        logger.warning("Event contains no Records")
        return []

    results = []

    for record in records:
        event_name = record.get("eventName", "")

        if not event_name.startswith("s3:ObjectCreated:"):
            logger.info(
                "Ignoring event type: %s",
                event_name,
            )
            continue

        s3 = record["s3"]

        bucket = s3["bucket"]["name"]

        raw_object_key = s3["object"]["key"]
        object_key = unquote_plus(raw_object_key)

        content_type = (
            s3["object"].get("contentType")
            or "application/octet-stream"
        )

        logger.info(
            "Processing MinIO object: bucket=%s key=%s",
            bucket,
            object_key,
        )

        collection_name = get_collection_name(
            bucket,
            object_key,
        )

        business_id, document_id = get_document_identifiers(
            bucket,
            object_key,
        )

        suffix = Path(object_key).suffix

        with tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False,
        ) as temp_file:
            temp_path = temp_file.name

        try:
            logger.info(
                "Downloading s3://%s/%s",
                bucket,
                object_key,
            )

            minio_client.download_file(
                bucket,
                object_key,
                temp_path,
            )

            ingestion_result = upload_to_application(
                file_path=temp_path,
                bucket=bucket,
                object_key=object_key,
                collection_name=collection_name,
                content_type=content_type,
            )

            document_url = generate_document_url(
                bucket,
                object_key,
            )

            status = ingestion_result.get(
                "status",
                "failed",
            )

            result = {
                "business_id": business_id,
                "document_id": document_id,
                "bucket": bucket,
                "object_key": object_key,
                "collection_name": collection_name,
                "document_url": document_url,
                "status": status,
                "ingestion": ingestion_result,
            }

            results.append(result)

            if status == "uploaded":
                logger.info(
                    "RAG ingestion completed successfully: %s",
                    json.dumps(result),
                )
            else:
                logger.error(
                    "RAG ingestion failed: %s",
                    json.dumps(result),
                )

        finally:
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass

    return results


def main():
    logger.info("Starting Tendo Kafka consumer")

    minio_client = create_minio_client()

    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(","),
        group_id=CONSUMER_GROUP,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda value: json.loads(
            value.decode("utf-8")
        ),
    )

    logger.info(
        "Listening to Kafka topic '%s'",
        KAFKA_TOPIC,
    )

    for message in consumer:
        logger.info(
            "Received event: topic=%s partition=%s offset=%s",
            message.topic,
            message.partition,
            message.offset,
        )

        try:
            results = process_event(
                message.value,
                minio_client,
            )

            if results:
                logger.info(
                    "Processing results: %s",
                    json.dumps(results),
                )

        except Exception:
            logger.exception(
                "Failed processing Kafka event. "
                "The event will NOT be retried."
            )

        finally:
            try:
                consumer.commit()

                logger.info(
                    "Kafka offset committed: "
                    "topic=%s partition=%s offset=%s",
                    message.topic,
                    message.partition,
                    message.offset,
                )

            except Exception:
                logger.exception(
                    "Failed to commit Kafka offset: "
                    "topic=%s partition=%s offset=%s",
                    message.topic,
                    message.partition,
                    message.offset,
                )


if __name__ == "__main__":
    main()
