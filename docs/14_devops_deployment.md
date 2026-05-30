# Document 14: DevOps & Deployment Documentation

---

## 1. CI/CD Pipeline Workflow

The project uses GitHub Actions for continuous integration and deployment. The pipeline validates tests, builds container images, and deploys cloud microservices to AWS.

```yaml
# GitHub Actions CI/CD Workflow: .github/workflows/deploy.yml
name: Build and Deploy Hawk-AI Cloud

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test_and_lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: 18
          cache: 'npm'
      - name: Install dependencies
        run: npm ci
      - name: Run Linter
        run: npm run lint
      - name: Run Unit Tests
        run: npm run test

  build_and_push_docker:
    needs: test_and_lint
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      - name: Log in to AWS ECR
        uses: aws-actions/amazon-ecr-login@v1
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_REGION: ap-south-1
      - name: Build and Push API Image
        uses: docker/build-push-action@v4
        with:
          context: .
          file: ./docker/Dockerfile.api
          push: true
          tags: ${{ secrets.ECR_REPOSITORY_URL }}/api:latest

  deploy_aws:
    needs: build_and_push_docker
    runs-on: ubuntu-latest
    steps:
      - name: Deploy Amazon ECS Task
        uses: aws-actions/amazon-ecs-deploy-task-definition@v1
        with:
          task-definition: ./docker/ecs-task-def.json
          service: hawk-ai-api-service
          cluster: hawk-ai-production-cluster
          wait-for-service-stability: true
```

---

## 2. Containerized Environments (Docker Compose)

For local development, the full cloud stack (Node.js API, PostgreSQL database, Redis instance) is containerized and initialized using Docker Compose.

```yaml
# docker-compose.yml
version: '3.8'

services:
  database:
    image: postgis/postgis:15-3.3
    container_name: hawk_ai_db
    environment:
      POSTGRES_DB: hawk-ai
      POSTGRES_USER: hawk_ai_admin
      POSTGRES_PASSWORD: SecretPassword123
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    container_name: hawk_ai_queue
    ports:
      - "6379:6379"

  api:
    build:
      context: .
      dockerfile: ./docker/Dockerfile.api
    container_name: hawk_ai_api
    environment:
      - PORT=3000
      - DB_HOST=database
      - DB_USER=hawk_ai_admin
      - DB_PASSWORD=SecretPassword123
      - DB_NAME=hawk-ai
      - REDIS_URL=redis://redis:6379
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    ports:
      - "3000:3000"
    depends_on:
      - database
      - redis

volumes:
  postgres_data:
```

---

## 3. Monitoring & Metrics Configuration

The system implements **Prometheus** for metrics collection and **Grafana** for visualizations:
* **Metrics Tracked**:
  * Ingestion Endpoint Requests Per Second (RPS).
  * VLM Worker Job processing time.
  * Active connections, queue depth (BullMQ).
  * Memory/CPU usage metrics on Edge RPi units.
* **Target Dashboards**:
  * *Systems Health*: API uptime, error rates, queue lag.
  * *Operations Room*: GPS coordinates of active captures, heatmap of current traffic violations.

---

## 4. Centralized Logging Architecture

1. **Edge Client**: Log entries on the Raspberry Pi write to `/var/log/hawk-ai/client.log`. Rotated daily using standard `logrotate` to prevent storage depletion.
2. **Cloud Stack**: Logs are formatted in structured JSON via Winston logger and pushed to **Winston/CloudWatch**.
3. **Log Format Example**:
   ```json
   {
     "level": "info",
     "timestamp": "2026-05-31T04:00:53.120Z",
     "message": "VLM verification completed successfully",
     "violation_id": "d8a50b3e-5948-4987-d9f6-1155ae853945",
     "confidence": 0.985,
     "execution_time_ms": 2340
   }
   ```

---

## 5. Backup & Rollback Protocols

### 5.1 Backup Strategy
* **Database**: Automated nightly snapshots of AWS RDS PostgreSQL with 30-day retention. Points of Recovery (PITR) configured to allow restoring database states within 5 minutes of data loss.
* **Storage**: Amazon S3 versioning enabled. Deletes are restricted to MFA Delete permissions to prevent malicious data wipes.

### 5.2 Rollback Strategy
* **Cloud Rollbacks**: If a production build fails stability tests after deploy, the ECS scheduler auto-reverts traffic route to the previous task definition image tag within 2 minutes.
* **Edge Firmware Rollbacks**: Managed via **Mender.io**. Mender uses dual rootfs partitions (A/B system partitions). When updating the YOLOv8 binary or firmware:
  1. Image flashes to inactive partition B.
  2. RPi reboots to partition B.
  3. Edge script runs a post-boot health check script confirming camera connections and API handshakes.
  4. If validation fails within 5 minutes, the bootloader automatically rolls back to the stable partition A.
  ```text
  Bootloader -> Try Active Partition B -> Health Check OK -> Commit Partition B
                                       -> Health Check FAIL -> Reboot to Stable Partition A
  ```
