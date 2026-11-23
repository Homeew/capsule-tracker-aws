#!/usr/bin/env python3
"""Read JSON lines from stdin and send them to an AWS SQS queue.

Example:
    python3 simulator/simulate.py --realtime --duration 30 | \
        python3 simulator/send_to_sqs.py --queue-url "$(terraform -chdir=terraform output -raw queue_url)"
"""
import argparse
import sys

import boto3

BATCH_SIZE = 10  # SQS allows up to 10 messages per send_message_batch call


def flush(client, queue_url, batch):
    if not batch:
        return 0
    resp = client.send_message_batch(QueueUrl=queue_url, Entries=batch)
    failed = resp.get("Failed", [])
    if failed:
        print(f"warning: {len(failed)} of {len(batch)} messages failed: {failed[0]}", file=sys.stderr)
    return len(batch) - len(failed)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--queue-url", required=True, help="SQS queue URL")
    p.add_argument("--region", default="us-east-2")
    args = p.parse_args()

    client = boto3.client("sqs", region_name=args.region)
    batch, sent = [], 0
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        batch.append({"Id": str(len(batch)), "MessageBody": line})
        if len(batch) >= BATCH_SIZE:
            sent += flush(client, args.queue_url, batch)
            batch = []
    sent += flush(client, args.queue_url, batch)
    print(f"sent {sent} messages", file=sys.stderr)


if __name__ == "__main__":
    main()
