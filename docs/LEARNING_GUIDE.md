# AWS Learning Booklet: Magnetic Capsule Tracking in the Cloud

*A review guide for what you built, what each piece means, what went wrong and how you fixed it, and what is left to do.*

Repository: `github.com/Homeew/capsule-tracker-aws`
Research code it builds on: `github.com/Homeew/capsule-tracker`

---

## 1. The big picture

You took your own research (magnetic localization of a capsule endoscope) and built a small cloud system around it. This is the kind of project that shows AWS skills on a CV, because it solves a problem from your own work rather than following a tutorial.

```
 sim_node (C++)            SQS queue              worker (Python)
 simulated magnetometer -> holds the messages -> reads messages one by one
 readings (JSON lines)     until processed            |
                                                      v
                                              tracker_node (C++)
                                              your Levenberg-Marquardt solver
                                              estimates position + moment
                                                      |
                                                      v
                                              DynamoDB table
                                              one row per time step
```

**What is proven to work**

| Piece | Proven where |
|---|---|
| Simulator sends 200 messages to SQS | Your terminal, real AWS |
| Worker reads SQS, runs your C++ tracker, writes DynamoDB | Your terminal, real AWS (200 samples, 0 skipped) |
| Same worker inside a Docker container | Your computer (Docker Desktop) |
| Docker image stored in ECR | Real AWS |
| ECS cluster, IAM roles, log group, service created by Terraform | Real AWS (8 resources) |

**What is not yet proven**

The container has **not yet run on ECS Fargate**. AWS reported: *"unable to place a task because your account is currently blocked."* That is an account-level block on a new account, not a bug in your code. See section 8.

**Accuracy result (simulated data):** on a 20-second simulated trajectory with 0.05 µT sensor noise, all 200 frames converged. Median position error was about 0.8 mm and the maximum about 2 mm. These numbers come from simulation, not from real hardware.

---

## 2. Vocabulary: what each thing is

**AWS basics**

- **Region:** a geographic location of AWS data centers (for example `us-east-2`, Ohio). Resources live in one region. Your account only allows certain regions.
- **IAM (Identity and Access Management):** who is allowed to do what. Users, roles, and policies live here.
- **IAM role:** a set of permissions that something (a person, a container) can temporarily assume. No permanent password.
- **Least privilege:** give only the permissions that are needed. Your worker's role can only read and delete from one queue and write to one table.
- **Service Control Policy (SCP):** a guardrail set by an AWS Organization above your account. It can deny actions even when your own permissions allow them. You hit three of these (section 5).
- **MFA:** a second login factor, such as a code from a phone app.

**Services you used**

- **S3:** object (file) storage. You made a private bucket with public access blocked.
- **SQS:** a message queue. The sender drops messages in and a worker takes them out later. This decouples the two sides, so the sender never waits for the worker.
- **DynamoDB:** a NoSQL database. Your table's key is `capsule_id` plus time `t`. On-demand billing means no idle cost.
- **ECR:** a private registry that stores your Docker images.
- **ECS Fargate:** runs containers without managing servers. You describe the container (a *task definition*) and ECS runs it (a *service* keeps N copies running).
- **CloudWatch Logs:** where container output goes.

**Tools**

- **Terraform:** infrastructure as code. You describe resources in `.tf` files and Terraform makes AWS match. *Plan* shows changes without making them. *Apply* makes them. The *state file* is Terraform's memory of what it created (never commit it).
- **Docker:** packages a program and everything it needs into an *image*. A running copy is a *container*.
- **CMake / FetchContent:** C++ build tool; FetchContent downloads your `capsule-tracker` repo and Eigen automatically during the build.

---

## 3. What is in the repository

```
capsule-tracker-aws/
├── terraform/            infrastructure as code
│   ├── versions.tf       provider + region
│   ├── variables.tf      region (us-east-2), project name
│   ├── main.tf           S3 telemetry bucket (private)
│   ├── queue.tf          SQS ingest queue
│   ├── dynamodb.tf       table for estimates
│   ├── ecr.tf            image registry
│   ├── ecs.tf            cluster, roles, task definition, service
│   └── outputs.tf        queue URL, table name, ECR URL
├── cpp/                  C++ programs reusing your research code
│   ├── sim_node.cpp      simulated sensor stream (JSON lines)
│   └── tracker_node.cpp  reads JSON, runs LM solver, prints estimates
├── simulator/
│   ├── simulate.py       first Python simulator (3x3 grid, superseded)
│   └── send_to_sqs.py    stdin -> SQS
├── consumer/
│   └── consume_to_dynamodb.py   first, simple SQS -> DynamoDB step
├── worker/worker.py      SQS -> C++ tracker -> DynamoDB
├── Dockerfile            two-stage build of the worker image
└── PROGRESS.md
```

---

## 4. The journey, step by step

1. **Repo and tools.** Created the GitHub repo. Installed git, GitHub CLI, AWS CLI v2, Terraform, Docker (Docker Desktop connected to Ubuntu in WSL 2).
2. **AWS account.** Created an account on the free plan ($100 credits, about 6 months).
3. **CLI login.** `aws login` (browser sign-in), region set with `aws configure set region us-east-2`.
4. **First Terraform resource.** S3 bucket. Plan, then apply.
5. **Simulator.** Python, magnetic dipole field, JSON lines.
6. **Streaming attempt (Kinesis).** Blocked by a guardrail. Redesigned around SQS and DynamoDB.
7. **Queue and table.** Created with Terraform. Sent 100 messages. Consumer wrote 100 rows.
8. **C++ nodes.** `sim_node` and `tracker_node` reuse your own classes (`twoLayerRing`, `GiTrajectory`, `measure`, `LmBaseline`).
9. **Worker.** Sorts each batch by time (standard SQS does not guarantee order), feeds your tracker, stores estimates, deletes messages only after storing.
10. **Docker.** Two-stage Dockerfile. Ran the container locally against real AWS.
11. **ECR.** Created the registry and pushed image `v1`.
12. **ECS.** Created cluster, two IAM roles, task definition, and service. Blocked at task placement.

---

## 5. Problems you hit and how you solved them

These are the most valuable part for learning. Real cloud work is mostly this.

| Problem | What it meant | Fix |
|---|---|---|
| `explicit deny in a service control policy` on S3 create | A guardrail allows only some regions | Tested regions one by one with a throwaway bucket. `us-east-2` worked, so the project moved there |
| Kinesis `AddTagsToStream` / `ListStreams` denied | The whole Kinesis service is blocked | Probed which services are allowed and redesigned with SQS + DynamoDB |
| `No configuration files` from Terraform | Ran it from the repo root | Run Terraform inside `terraform/` |
| `Unable to locate credentials` / `ExpiredToken` | Login session expired, or old exported keys overrode it | `unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN`, then `aws login` |
| `botocore[crt]` missing | `aws login` sessions need an extra Python package | `pip install "botocore[crt]"` |
| `git push` rejected (fetch first) | GitHub had a commit you lacked (a LICENSE edit) | `git pull --rebase`, then `git push` |
| Docker `The stub received bad data` | Docker Desktop credential helper problem in WSL | Used a plain `DOCKER_CONFIG` folder for the ECR login |
| `docker: command not found` in Ubuntu | Docker Desktop was not integrated with that Ubuntu | Turned on WSL integration for the right distro |
| ECS `account is currently blocked` | AWS blocks new accounts from launching compute until a check clears | Open an AWS Support case (section 8) |

**Lessons to remember**

- Read the *action name* in a permission error. It tells you exactly what is blocked.
- Test assumptions with small throwaway experiments before building on them.
- When you cannot use one service, redesign around the services you can use.
- Do not trust "it ran" until you see the result (the DynamoDB row count).

---

## 6. Safety and cost habits

- Never put passwords, access keys, or one-time codes into chats, screenshots, or Git.
- Blur your account ID and personal details in public screenshots.
- Do not commit `.terraform/`, `*.tfstate`, `.venv/`, or `cpp/build/`. They are already in `.gitignore`.
- Keep the ECS worker at **0 tasks** when not testing (`terraform apply` with the default). Always-on Fargate costs roughly $9 a month for this size.
- SQS and DynamoDB on-demand cost nothing when idle. A Kinesis stream would have billed hourly, which is another reason the redesign suits you.
- On the free plan, services stop when the credits run out or the plan ends (about May 2027).

---

## 7. Command cheat sheet

```bash
# Log in again (any time you see ExpiredToken)
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
aws login
aws sts get-caller-identity

# Terraform (always inside terraform/)
cd ~/capsule-tracker-aws/terraform
terraform fmt && terraform validate
terraform plan
terraform apply

# Build the C++ nodes
cmake -S cpp -B cpp/build
cmake --build cpp/build --target sim_node tracker_node -j4

# Try the tracker locally (no AWS needed)
./cpp/build/sim_node --duration 20 | ./cpp/build/tracker_node | tail -3

# Send simulated data to the queue
./cpp/build/sim_node --duration 20 | python3 simulator/send_to_sqs.py \
  --queue-url "$(terraform -chdir=terraform output -raw queue_url)"

# Run the worker locally (drains the queue, then exits)
python3 worker/worker.py \
  --queue-url "$(terraform -chdir=terraform output -raw queue_url)" \
  --table "$(terraform -chdir=terraform output -raw poses_table)" \
  --tracker ./cpp/build/tracker_node --exit-when-empty

# Count rows for one capsule ID
aws dynamodb query --table-name "$(terraform -chdir=terraform output -raw poses_table)" \
  --key-condition-expression "capsule_id = :c" \
  --expression-attribute-values '{":c": {"S": "sim-1"}}' --select COUNT

# Docker
docker build -t capsule-tracker-aws:dev .

# Git
git status
git add -A && git commit -m "message" && git push
```

---

## 8. Open items (your to-do list)

**Important, do these soon**

1. **Account security:** turn on MFA for the root user and confirm the account recovery email is correct.
2. **Contact AWS Support about the ECS block.** In the AWS Settings sidebar, open **Support** and create a case. Say that your ECS service in `us-east-2` reports "unable to place a task because your account is currently blocked", that you are on the free plan, and ask what is needed to lift it. Also check your sign-up email (and spam) for any verification request from AWS.
3. **Make sure the ECS service is at 0 tasks** (`terraform apply` with the default).

**Next learning steps**

4. **GitHub Actions:** build the Docker image and push it to ECR on every commit (CI/CD).
5. **README polish:** architecture diagram, results table, "lessons learned" section.
6. **Add resource tags** once you know which services allow them (tagging was blocked on Kinesis).
7. **Pin the tracker version** in `cpp/CMakeLists.txt` (use a commit hash instead of `main`) so builds are reproducible.
8. **Move raw data to S3** and query it with **Athena**.
9. **Use a FIFO queue** if strict ordering matters once your EKF/UKF is added, because those filters are sensitive to message order.
10. **Plug in your EKF and UKF** (still unchecked in your `capsule-tracker` README) and compare them with the LM baseline in the cloud.
11. **Certification path:** AWS Cloud Practitioner, then Solutions Architect Associate or Machine Learning Engineer Associate.

---

## 9. How to describe this on your CV and GitHub

Only claim what is true today. Suggested wording:

> **Cloud pipeline for magnetic capsule localization (AWS, Terraform, Docker, C++17, Python)**
> Designed an event-driven pipeline: simulated magnetometer stream, SQS ingest queue, containerized worker running a C++17 Levenberg-Marquardt tracker, and DynamoDB storage. Defined all infrastructure as code with Terraform, including least-privilege IAM roles, an ECR registry, and an ECS Fargate service. Achieved a median 0.8 mm position error on simulated trajectories. Diagnosed and worked around organization-level service control policies by redesigning the architecture.

After the ECS block is lifted and you see the container running in the cloud, you can change the wording to say it was *deployed and run on ECS Fargate*.

**GitHub checklist:** README with the architecture diagram and results, Topics added, repo pinned on your profile, no secrets in history, license present.

---

## 10. Where to resume

When you come back:
1. Run the login steps (section 7).
2. Check your email and the support case about the ECS block.
3. Tell your assistant: *"Continue from section 8, item 4 (GitHub Actions)"* or *"The ECS block is lifted, let's run the worker on Fargate."*

Good work. You went from "I want to learn AWS" to a working, version-controlled cloud pipeline built around your own research.
