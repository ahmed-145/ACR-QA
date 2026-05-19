resource "aws_s3_bucket" "public" {
  bucket = "evil-bucket"
  acl    = "public-read"
}

resource "aws_security_group" "open" {
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "noenc" {
  instance_class      = "db.t3.micro"
  storage_encrypted   = false
}

resource "aws_ebs_volume" "noenc" {
  availability_zone = "us-east-1a"
  size              = 40
  encrypted         = false
}

resource "aws_lb_listener" "http" {
  protocol = "HTTP"
  port     = 80
}

resource "aws_cloudtrail" "off" {
  name           = "trail"
  is_logging     = false
}

resource "aws_iam_policy" "admin" {
  policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect":"Allow","Action":"*","Resource":"*"}
  ]
}
POLICY
}

# Hardcoded AWS access key
provider "aws" {
  access_key = "AKIAIOSFODNN7EXAMPLE"
  secret_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
}
