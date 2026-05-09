# AWS EKS MCP Server

Comprehensive MCP server for creating and managing AWS EKS (Elastic Kubernetes Service) clusters using Terraform.

## Features

### Terraform Generation & Execution
- **generate_eks_terraform** - Generate complete Terraform configs (VPC, EKS, node groups, IRSA)
- **eks_terraform_init** - Initialize Terraform
- **eks_terraform_plan** - Preview infrastructure changes
- **eks_terraform_apply** - Create/update EKS cluster
- **eks_terraform_destroy** - Destroy cluster and all resources

### Kubectl Configuration
- **configure_kubectl** - Automatically configure kubectl to access the cluster

### Add-on Management
- **install_addon** - Install common EKS add-ons:
  - AWS Load Balancer Controller
  - Metrics Server
  - Cluster Autoscaler
  - External DNS
  - Cert Manager

### Cluster Management
- **upgrade_eks_cluster** - Upgrade Kubernetes version
- **list_eks_clusters** - List all EKS clusters
- **describe_eks_cluster** - Get detailed cluster info
- **get_eks_node_groups** - List and describe node groups
- **scale_node_group** - Scale node groups up/down

## What Gets Created

When you generate and apply an EKS Terraform configuration, you get:

### Networking
- VPC with public and private subnets across 3 AZs
- NAT Gateways for private subnet internet access
- Internet Gateway for public subnets
- Proper subnet tagging for EKS/ALB

### EKS Cluster
- EKS control plane with specified Kubernetes version
- IRSA (IAM Roles for Service Accounts) enabled
- Managed node group with auto-scaling
- EBS CSI driver (optional)
- Security groups configured

### IAM
- EKS cluster IAM role
- Node group IAM role
- IRSA OIDC provider
- EBS CSI driver IAM role (if enabled)
- Cluster Autoscaler IAM role (if enabled)

## Prerequisites

- Python 3.10+
- Terraform >= 1.0
- AWS CLI configured
- kubectl installed
- Helm (for add-on installation)
- boto3 Python library

## Installation

```bash
cd ~/.mcp-servers/eks-mcp-server
pip install -r requirements.txt
```

## Configuration

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "eks": {
      "command": "python3",
      "args": ["/Users/youruser/.mcp-servers/eks-mcp-server/server.py"],
      "env": {
        "EKS_WORKSPACE": "/Users/youruser/eks-clusters"
      }
    }
  }
}
```

## Usage Examples

### Create a New EKS Cluster

```
User: "Generate Terraform for an EKS cluster named production-cluster in us-west-2 with Kubernetes 1.29"

User: "Use t3.large instances with 3 nodes minimum and 10 maximum"

User: "Enable EBS CSI driver and cluster autoscaler"

Claude: [generates complete Terraform configuration]

User: "Initialize and plan the Terraform"

Claude: [runs terraform init and plan]

User: "Apply the configuration"

Claude: [creates the entire EKS cluster]

User: "Configure kubectl for this cluster"

Claude: [updates kubeconfig]
```

### Manage Existing Cluster

```
User: "List all EKS clusters in us-east-1"

User: "Describe the production-cluster"

User: "Show me the node groups"

User: "Scale the node group to 5 desired nodes"

User: "Install the AWS Load Balancer Controller"

User: "Install metrics-server"
```

### Upgrade Cluster

```
User: "Upgrade production-cluster to Kubernetes 1.30"

Claude: [initiates rolling upgrade]
```

## Generated Terraform Structure

```
~/eks-clusters/
└── my-cluster/
    ├── main.tf       # VPC, EKS, node groups, IRSA
    ├── variables.tf  # Configurable parameters
    └── outputs.tf    # Cluster endpoints, IDs, kubectl command
```

## Terraform Modules Used

- **terraform-aws-modules/vpc/aws** - Production-ready VPC
- **terraform-aws-modules/eks/aws** - EKS cluster and node groups
- **terraform-aws-modules/iam/aws** - IRSA IAM roles

## Default Configuration

- **VPC CIDR**: 10.0.0.0/16
- **Subnets**: 3 public + 3 private (one per AZ)
- **Node Instance Type**: t3.medium
- **Node Count**: 2 desired, 1-4 scaling range
- **Disk Size**: 20 GB
- **Kubernetes Version**: 1.29
- **IRSA**: Enabled
- **EBS CSI Driver**: Enabled

## Add-on Installation

The server can install these add-ons via Helm or kubectl:

### AWS Load Balancer Controller
Enables ALB and NLB ingress for your applications.

### Metrics Server
Required for Horizontal Pod Autoscaler (HPA) and `kubectl top`.

### Cluster Autoscaler
Automatically scales node groups based on pod resource requests.

### External DNS
Automatically creates Route53 DNS records for Ingresses.

### Cert Manager
Automates TLS certificate management with Let's Encrypt.

## Cluster Upgrade Process

When you upgrade a cluster:

1. Control plane is upgraded first (rolling, zero-downtime)
2. Add-ons may need updating to match new K8s version
3. Node groups should be upgraded separately (after control plane)
4. Update Terraform config and run `eks_terraform_apply` to upgrade nodes

## Cost Considerations

Typical EKS cluster costs:

- **EKS Control Plane**: $0.10/hour (~$73/month)
- **EC2 Nodes**: Varies by instance type
  - t3.medium: ~$0.0416/hour (~$30/month per node)
  - t3.large: ~$0.0832/hour (~$60/month per node)
- **NAT Gateways**: $0.045/hour per AZ (~$32/month each)
- **Data Transfer**: Varies

**Cost Optimization**:
- Use single NAT Gateway for dev environments
- Enable cluster autoscaler to scale down during off-hours
- Use Spot instances for fault-tolerant workloads
- Right-size instance types based on actual usage

## Security Best Practices

- Enable cluster logging (CloudWatch)
- Use private API endpoint for production
- Implement Pod Security Standards
- Enable secrets encryption using KMS
- Use IRSA instead of instance profiles
- Regular security updates (upgrade K8s version)
- Network policies to restrict pod communication
- Use AWS WAF with ALB

## Troubleshooting

### Terraform fails with "Error creating EKS Cluster"
- Check AWS service quotas
- Verify IAM permissions
- Ensure region supports EKS

### Node groups stuck in "CREATE_FAILED"
- Check EC2 instance limits
- Verify subnet has available IP addresses
- Review node IAM role permissions

### kubectl can't connect
- Run `configure_kubectl` tool again
- Verify AWS credentials are current
- Check cluster endpoint is accessible

### Add-on installation fails
- Ensure Helm is installed
- Verify kubectl is configured
- Check cluster has internet access (for pulling images)

## Environment Variables

- **EKS_WORKSPACE**: Directory for Terraform projects (default: ~/eks-clusters)

## Advanced Usage

### Custom Node Group Configuration

```
User: "Generate EKS cluster with mixed instance types: t3.large and t3.xlarge, 5-20 nodes"

User: "Set disk size to 50GB"
```

### Multi-Region

```
User: "Create EKS cluster in ap-southeast-1"

User: "List clusters in eu-west-1"
```

### Tags

```
User: "Generate EKS cluster with tags: Environment=Production, Team=Platform, CostCenter=Engineering"
```

## Terraform State Management

⚠️ **Important**: For production, configure remote state:

```hcl
terraform {
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "eks/production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}
```

## Next Steps After Cluster Creation

1. Install core add-ons (metrics-server, AWS LB controller)
2. Set up monitoring (Prometheus, Grafana)
3. Configure logging (Fluent Bit → CloudWatch)
4. Deploy sample application
5. Set up CI/CD pipelines
6. Implement GitOps (ArgoCD, Flux)

## Resources

- **EKS Best Practices**: https://aws.github.io/aws-eks-best-practices/
- **Terraform AWS EKS Module**: https://registry.terraform.io/modules/terraform-aws-modules/eks/aws
- **EKS Documentation**: https://docs.aws.amazon.com/eks/

---

**Production-Ready EKS Clusters** | Terraform + VPC + IRSA + Add-ons
