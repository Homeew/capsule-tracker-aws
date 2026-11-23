#!/usr/bin/env python3
"""Drain the SQS telemetry queue and store each sample in DynamoDB.

Writes are keyed by (capsule_id, t), so re-processing the same sample just
overwrites the same row (idempotent). Messages are deleted from the queue only
after they were written successfully.
"""
import argparse
import json
from decimal import Decimal

import boto3


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--queue-url", required=True)
    p.add_argument("--table", required=True)
    p.add_argument("--region", default="us-east-2")
    p.add_argument("--capsule-id", default="capsule-1")
    args = p.parse_args()

    sqs = boto3.client("sqs", region_name=args.region)
    table = boto3.resource("dynamodb", region_name=args.region).Table(args.table)

    processed = 0
    while True:
        resp = sqs.receive_message(
            QueueUrl=args.queue_url, MaxNumberOfMessages=10, WaitTimeSeconds=5
        )
        messages = resp.get("Messages", [])
        if not messages:
            break  # queue is empty

        for m in messages:
            # DynamoDB needs Decimal instead of float
            sample = json.loads(m["Body"], parse_float=Decimal)
            table.put_item(Item={
                "capsule_id": args.capsule_id,
                "t": sample["t"],
                "true_position_m": sample["true_position_m"],
                "readings_ut": sample["readings_ut"],
            })

        sqs.delete_message_batch(
            QueueUrl=args.queue_url,
            Entries=[{"Id": str(i), "ReceiptHandle": m["ReceiptHandle"]}
                     for i, m in enumerate(messages)],
        )
        processed += len(messages)

    print(f"processed {processed} messages")


if __name__ == "__main__":
    main()
