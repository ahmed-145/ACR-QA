variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "prod"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Must be dev, staging, or prod."
  }
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "AZs to use"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "private_subnet_cidrs" {
  type    = list(string)
  default = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "public_subnet_cidrs" {
  type    = list(string)
  default = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
}

variable "rds_instance_class" {
  description = "RDS instance type"
  type        = string
  default     = "db.t3.medium"
}

variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "api_cpu" {
  description = "Fargate task CPU units"
  type        = number
  default     = 512
}

variable "api_memory" {
  description = "Fargate task memory (MiB)"
  type        = number
  default     = 1024
}

variable "api_desired_count" {
  description = "Desired API task count"
  type        = number
  default     = 2
}

variable "api_image" {
  description = "Docker image for the API (without tag)"
  type        = string
  default     = "ghcr.io/ahmeed-145/acrqa"
}

variable "api_image_tag" {
  description = "Docker image tag"
  type        = string
  default     = "4.0.0"
}

variable "acm_certificate_arn" {
  description = "ARN of the ACM certificate for HTTPS"
  type        = string
}

variable "sentry_dsn" {
  description = "Sentry DSN (optional)"
  type        = string
  default     = ""
}

# Secrets — never commit real values; pass via TF_VAR_* env vars or a tfvars file
variable "db_password" {
  description = "RDS master password"
  type        = string
  sensitive   = true
}

variable "redis_auth_token" {
  description = "ElastiCache auth token (min 16 chars)"
  type        = string
  sensitive   = true
}

variable "groq_api_key" {
  description = "Groq API key"
  type        = string
  sensitive   = true
}

variable "app_secret_key" {
  description = "FastAPI JWT secret key"
  type        = string
  sensitive   = true
}
