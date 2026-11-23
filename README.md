# capsule-tracker-aws

Cloud pipeline for **magnetic capsule endoscopy localization**. A simulated magnetometer stream goes through an AWS queue to a containerized C++17 tracker, and the position estimates are stored in a database. All infrastructure is defined with Terraform.

It builds on my research code: [capsule-tracker](https://github.com/Homeew/capsule-tracker) (dipole model, two-layer sensor array, Levenberg-Marquardt solver).

## Architecture

```
 sim_node (C++)  ->  SQS queue  ->  worker (Python)  ->  tracker_node (C++)  ->  DynamoDB
 simulated           buffers        reads messages,      Levenberg-Marquardt     one row per
 magnetometer        messages       runs the tracker     position + moment       time step
 readings
```

## Status

| Piece | State |
|---|---|
| Simulator and tracker nodes (C++17, reuse `capsule-tracker`) | Done |
| SQS queue, DynamoDB table, S3 bucket, ECR registry (Terraform) | Done, deployed |
| Worker: SQS -> tracker -> DynamoDB | Done, tested on AWS |
| Docker image (two-stage build), pushed to ECR | Done |
| ECS Fargate service, IAM roles, log group (Terraform) | Deployed; running tasks is blocked by an AWS account-level restriction (support case pending) |
| CI/CD with GitHub Actions | Planned |
| EKF / UKF in the cloud | Planned (see `capsule-tracker`) |

## Result (simulated data)

On a 20-second simulated trajectory (8 sensors, 0.05 µT noise), all 200 frames converged. Median position error was about 0.8 mm and the maximum about 2 mm. This is simulation only, not real hardware.

## Try the tracker locally (no AWS needed)

```bash
cmake -S cpp -B cpp/build
cmake --build cpp/build --target sim_node tracker_node -j4
./cpp/build/sim_node --duration 20 | ./cpp/build/tracker_node | tail -3
```

## Repository layout

- `cpp/` – `sim_node` and `tracker_node`
- `worker/` – SQS worker that drives the tracker
- `simulator/`, `consumer/` – early Python pieces and the SQS sender
- `terraform/` – all AWS resources as code
- `Dockerfile` – worker image
- `docs/LEARNING_GUIDE.md` – what I built, problems hit (including organization guardrails that blocked Kinesis and some regions), and next steps

## Lessons learned

The AWS account sits under organization-level guardrails (service control policies). They blocked Kinesis and most regions, so the design was changed to SQS + DynamoDB in `us-east-2`. Details are in the learning guide.# capsule-tracker-aws
Real-time magnetic capsule endoscopy tracking on AWS — C++17 UKF tracker on ECS Fargate, IoT Core/Kinesis streaming, Timestream storage and Grafana dashboards, deployed with Terraform and GitHub Actions.
