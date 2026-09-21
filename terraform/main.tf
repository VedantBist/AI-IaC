terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {}

resource "docker_image" "ai_service" {
  name = "ai-iac-service:latest"

  build {
    context    = "${path.module}/.."
    dockerfile = "${path.module}/../Dockerfile"
    builder    = "default"
  }
}

resource "docker_container" "ai_service" {
  name  = "ai-iac-terraform"
  image = docker_image.ai_service.image_id

  ports {
    internal = 8000
    external = 8001
  }
}