#!/usr/bin/env python3
"""SQS worker: feed sensor samples to the C++ tracker and store the estimates.

queue (SQS) -> tracker_node (C++ LM solver, one long-lived process) -> DynamoDB

Settings come from command-line flags or from environment variables, so the
same script runs on a laptop and inside a container on ECS.
"""
import argparse
import json
import os
import subprocess
import sys
from decimal import Decimal

import boto3

N_SENSORS = 8  # must match mag::twoLayerRing() in the C++ code


def is_valid(body, sample):
    """True if the message has the structure tracker_node expects."""
    try:
        float(sample["t"])
        rows = sample["readings_ut"]
        return (
            "\n" not in body.strip()
            and len(rows) == N_SENSORS
            and all(len(r) == 3 and all(float(v) == float(v) for v in r) for r in rows)
        )
    except (KeyError, TypeError, ValueError):
        return False


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--queue-url", default=os.environ.get("QUEUE_URL"))
    p.add_argument("--table", default=os.environ.get("TABLE_NAME"))
    p.add_argument("--region", default=os.environ.get("AWS_REGION", "us-east-2"))
    p.add_argument("--capsule-id", default=os.environ.get("CAPSULE_ID", "sim-1"))
    p.add_argument("--tracker", default=os.environ.get("TRACKER_BIN", "tracker_node"))
    p.add_argument("--exit-when-empty", action="store_true",
                   help="stop when the queue is empty (default: run forever)")
    args = p.parse_args(argv)
    if not args.queue_url or not args.table:
        p.error("--queue-url and --table are required (or set QUEUE_URL / TABLE_NAME)")
    return args


def main(argv=None):
    args = parse_args(argv)
    sqs = boto3.client("sqs", region_name=args.region)
    table = boto3.resource("dynamodb", region_name=args.region).Table(args.table)
    tracker = subprocess.Popen([args.tracker], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, text=True, bufsize=1)
    processed = skipped = 0
    try:
        while True:
            resp = sqs.receive_message(QueueUrl=args.queue_url,
                                       MaxNumberOfMessages=10, WaitTimeSeconds=5)
            messages = resp.get("Messages", [])
            if not messages:
                if args.exit_when_empty:
                    break
                continue

            good = []
            for m in messages:
                try:
                    sample = json.loads(m["Body"], parse_float=Decimal)
                except json.JSONDecodeError:
                    sample = None
                if sample is not None and is_valid(m["Body"], sample):
                    good.append((m, sample))
                else:
                    skipped += 1
                    print(f"skipping malformed message {m['MessageId']}", file=sys.stderr)

            # Standard SQS queues do not guarantee order; the tracker warm-starts
            # from the previous frame, so process each batch in time order.
            good.sort(key=lambda ms: ms[1]["t"])

            for m, sample in good:
                tracker.stdin.write(m["Body"].strip() + "\n")
                tracker.stdin.flush()
                out = tracker.stdout.readline()
                if not out:
                    raise RuntimeError("tracker_node exited unexpectedly")
                est = json.loads(out, parse_float=Decimal)
                item = {
                    "capsule_id": args.capsule_id,
                    "t": est["t"],
                    "true_position_m": sample.get("true_position_m"),
                    "est_position_m": est["est_position_m"],
                    "est_moment_am2": est["est_moment_am2"],
                    "cost": est["cost"],
                    "converged": est["converged"],
                }
                if "error_mm" in est:
                    item["error_mm"] = est["error_mm"]
                table.put_item(Item={k: v for k, v in item.items() if v is not None})
                processed += 1

            # Delete only after everything in the batch was stored. A crash
            # means redelivery, and the (capsule_id, t) key makes that harmless.
            sqs.delete_message_batch(
                QueueUrl=args.queue_url,
                Entries=[{"Id": str(i), "ReceiptHandle": m["ReceiptHandle"]}
                         for i, m in enumerate(messages)])
    finally:
        tracker.stdin.close()
        tracker.wait(timeout=10)

    print(f"processed {processed} samples, skipped {skipped}")
    return processed


if __name__ == "__main__":
    main()
