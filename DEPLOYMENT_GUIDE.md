# AWS EC2 Deployment Guide

Follow these steps to deploy DocuMind AI to an AWS EC2 instance.

## 1. Launch an EC2 Instance
- **AMI:** Ubuntu 22.04 LTS or 24.04 LTS.
- **Instance Type:** t3.medium or larger (at least 4GB RAM recommended for Qdrant and LLM workloads).
- **Storage:** 20GB+ SSD.
- **Security Group:**
    - Allow SSH (Port 22) from your IP.
    - Allow HTTP (Port 80) from Anywhere.
    - Allow HTTPS (Port 443) from Anywhere.

## 2. Install Docker on EC2
Once connected via SSH, run:
```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER
newgrp docker
```

## 3. Clone and Prepare the Code
```bash
git clone https://github.com/your-repo/DocuMind-AI.git
cd DocuMind-AI
cp .env.sample .env
# Edit .env with your production API keys
nano .env
```

## 4. Launch the Production Stack
```bash
docker compose -f docker-compose.prod.yml up --build -d
```

## 5. SSL / HTTPS (Optional but Recommended)
Install Certbot and configure Nginx:
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

## 6. Access Your App
Visit `http://your-ec2-public-ip` or `https://yourdomain.com`.
