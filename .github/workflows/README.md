# GitHub Workflows

This folder contains the CI/CD automation for the project.

## Overview

- `python-tests.yml`: runs Python tests for API and worker services.
- `dockerhub-manual-push.yml`: builds and pushes multi-arch Docker images to Docker Hub.

## `python-tests.yml` (Python Tests)

### Purpose

Validate Python code changes in:

- `srcs/app`
- `srcs/worker`

### Triggers

- `push` when changes affect:
	- `srcs/app/**`
	- `srcs/worker/**`
	- `.github/workflows/python-tests.yml`
- `pull_request` with the same path filters.

### What it does

Runs a matrix with 2 targets:

- `app` (`srcs/app`)
- `worker` (`srcs/worker`)

For each target, it:

1. Checks out the repository.
2. Sets up Python `3.12`.
3. Installs Poetry `1.8.3`.
4. Installs dependencies with dev extras: `poetry install --with dev`.
5. Runs tests: `poetry run pytest -q`.

### Notes

- `fail-fast: false` is enabled, so one failing matrix job does not cancel the other.

## `dockerhub-manual-push.yml` (Docker Hub Push)

### Purpose

Build and publish Docker images for:

- API
- Frontend
- Worker

### Triggers

- `workflow_dispatch` (manual run) with input:
	- `tag` (required, default: `latest`)
- `push` to `main` when changes affect:
	- `srcs/app/**`
	- `srcs/frontend/**`
	- `srcs/worker/**`
	- `.github/workflows/dockerhub-manual-push.yml`

### What it does

Runs a matrix for 3 images:

- `distributed-audio-api`
- `distributed-audio-frontend`
- `distributed-audio-worker`

For each image, it:

1. Checks out the repository.
2. Sets up QEMU for cross-platform builds (`arm64`, `amd64`).
3. Sets up Docker Buildx.
4. Logs into Docker Hub using GitHub secrets.
5. Builds and pushes images for `linux/amd64` and `linux/arm64`.

### Tags produced

Each image gets two tags:

- `${DOCKERHUB_USERNAME}/<image>:<tag-or-latest>`
	- manual run: uses `inputs.tag`
	- push run: uses `latest`
- `${DOCKERHUB_USERNAME}/<image>:sha-${GITHUB_SHA}`

### Required repository secrets

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

## Manual release flow

1. Open GitHub repository actions.
2. Select **Docker Hub Push**.
3. Click **Run workflow**.
4. Provide a tag (for example `v1.2.0`).
5. Run the workflow.

The workflow will push all three images with the selected tag and a commit SHA tag.
