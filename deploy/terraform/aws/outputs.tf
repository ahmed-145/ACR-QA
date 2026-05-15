output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.acrqa.dns_name
}

output "rds_endpoint" {
  description = "RDS endpoint (host:port)"
  value       = aws_db_instance.postgres.endpoint
  sensitive   = true
}

output "redis_primary_endpoint" {
  description = "ElastiCache primary endpoint"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
  sensitive   = true
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.acrqa.name
}

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}
