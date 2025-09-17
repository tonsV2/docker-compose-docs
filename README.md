# Docker Compose Docs

Generate documentation for environment variables in your Docker Compose files.

This tool is inspired by [helm-docs](https://github.com/norwoodj/helm-docs).

## Quick start

Git clone this repository and run the below command to generate documentation for the Docker Compose file in the `examples` directory:

```bash
python -m src.cli examples/ > docs.md
```

Or using Docker

```bash
docker compose run --rm app > docs.md
```

## How it works

The tool scans your Docker Compose files for environment variables with comments starting with `# --`.  
These comments are turned into documentation tables in Markdown format.

## Integrate with your project

There are many ways to run the tool and pass it your Docker Compose files. However, the most common use case is probably
to include this in your own `docker-compose.yml` and run it from there.

```yaml
compose-docs:
  image: tons/docker-compose-docs:latest          # Should be pinned to a specific version
  profiles:
    - docs                                        # Only run when explicitly requested
  volumes:
    - .:/src:ro                                   # Mount the directory with your docker compose file (as read-only)
  environment:
    DOCKER_COMPOSE_FILE_PATHS: /src;/src/overlays # Specify paths to docker-compose files to include in the documentation
```

Then run this from your Makefile, CI pipeline, or directly:

```bash
docker compose run --rm compose-docs > ./docs/environment-variables.md
```

## Sample output

Example of generated documentation:

```markdown
# Environment Variables Documentation

## File: `docker-compose.yml`

### Service: web

| Variable   | Description           | Default Value |
|------------|-----------------------|---------------|
| `APP_PORT` | Web service port      | `8080`        |
| `DEBUG`    | Enable debug logging  | `false`       |
```
