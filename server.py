#!/usr/bin/env python3
"""
AWS EKS MCP Server
Comprehensive server for creating and managing AWS EKS clusters with Terraform.
Includes cluster creation, add-on management, upgrades, and kubectl configuration.
"""

import asyncio
import json
import subprocess
import os
import base64
from pathlib import Path
from typing import Any, Dict, Optional

from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio

server = Server("eks-mcp-server")

EKS_WORKSPACE = os.environ.get("EKS_WORKSPACE", str(Path.home() / "eks-clusters"))
Path(EKS_WORKSPACE).mkdir(parents=True, exist_ok=True)


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available EKS tools."""
    return [
        Tool(
            name="generate_eks_terraform",
            description="Generate complete Terraform configuration for an EKS cluster with VPC, node groups, and IRSA",
            inputSchema={
                "type": "object",
                "properties": {
                    "cluster_name": {"type": "string", "description": "EKS cluster name"},
                    "region": {"type": "string", "description": "AWS region", "default": "us-east-1"},
                    "kubernetes_version": {"type": "string", "description": "Kubernetes version", "default": "1.29"},
                    "vpc_cidr": {"type": "string", "description": "VPC CIDR block", "default": "10.0.0.0/16"},
                    "node_group_config": {
                        "type": "object",
                        "description": "Node group configuration",
                        "properties": {
                            "instance_types": {"type": "array", "items": {"type": "string"}, "default": ["t3.medium"]},
                            "desired_size": {"type": "integer", "default": 2},
                            "min_size": {"type": "integer", "default": 1},
                            "max_size": {"type": "integer", "default": 4},
                            "disk_size": {"type": "integer", "default": 20}
                        }
                    },
                    "enable_irsa": {"type": "boolean", "description": "Enable IRSA (IAM Roles for Service Accounts)", "default": True},
                    "enable_cluster_autoscaler": {"type": "boolean", "description": "Include cluster autoscaler IAM role", "default": False},
                    "enable_ebs_csi": {"type": "boolean", "description": "Enable EBS CSI driver", "default": True},
                    "tags": {"type": "object", "description": "Tags for all resources"}
                },
                "required": ["cluster_name", "region"]
            }
        ),
        Tool(
            name="eks_terraform_init",
            description="Initialize Terraform for an EKS cluster project",
            inputSchema={
                "type": "object",
                "properties": {
                    "cluster_name": {"type": "string", "description": "EKS cluster name"}
                },
                "required": ["cluster_name"]
            }
        ),
        Tool(
            name="eks_terraform_plan",
            description="Run Terraform plan for EKS cluster",
            inputSchema={
                "type": "object",
                "properties": {
                    "cluster_name": {"type": "string", "description": "EKS cluster name"}
                },
                "required": ["cluster_name"]
            }
        ),
        Tool(
            name="eks_terraform_apply",
            description="Apply Terraform to create/update EKS cluster",
            inputSchema={
                "type": "object",
                "properties": {
                    "cluster_name": {"type": "string", "description": "EKS cluster name"},
                    "auto_approve": {"type": "boolean", "description": "Auto-approve changes", "default": False}
                },
                "required": ["cluster_name"]
            }
        ),
        Tool(
            name="eks_terraform_destroy",
            description="Destroy EKS cluster and all resources",
            inputSchema={
                "type": "object",
                "properties": {
                    "cluster_name": {"type": "string", "description": "EKS cluster name"},
                    "auto_approve": {"type": "boolean", "description": "Auto-approve destruction", "default": False}
                },
                "required": ["cluster_name"]
            }
        ),
        Tool(
            name="configure_kubectl",
            description="Configure kubectl to access the EKS cluster",
            inputSchema={
                "type": "object",
                "properties": {
                    "cluster_name": {"type": "string", "description": "EKS cluster name"},
                    "region": {"type": "string", "description": "AWS region"}
                },
                "required": ["cluster_name", "region"]
            }
        ),
        Tool(
            name="install_addon",
            description="Install an EKS add-on using Helm or kubectl",
            inputSchema={
                "type": "object",
                "properties": {
                    "cluster_name": {"type": "string", "description": "EKS cluster name"},
                    "addon_name": {
                        "type": "string",
                        "description": "Add-on to install",
                        "enum": ["aws-load-balancer-controller", "metrics-server", "cluster-autoscaler", "external-dns", "cert-manager"]
                    },
                    "region": {"type": "string", "description": "AWS region"},
                    "values": {"type": "object", "description": "Custom values for the add-on"}
                },
                "required": ["cluster_name", "addon_name", "region"]
            }
        ),
        Tool(
            name="upgrade_eks_cluster",
            description="Upgrade EKS cluster to a new Kubernetes version",
            inputSchema={
                "type": "object",
                "properties": {
                    "cluster_name": {"type": "string", "description": "EKS cluster name"},
                    "region": {"type": "string", "description": "AWS region"},
                    "target_version": {"type": "string", "description": "Target Kubernetes version (e.g., 1.29)"}
                },
                "required": ["cluster_name", "region", "target_version"]
            }
        ),
        Tool(
            name="list_eks_clusters",
            description="List all EKS clusters in a region",
            inputSchema={
                "type": "object",
                "properties": {
                    "region": {"type": "string", "description": "AWS region", "default": "us-east-1"}
                },
                "required": []
            }
        ),
        Tool(
            name="describe_eks_cluster",
            description="Get detailed information about an EKS cluster",
            inputSchema={
                "type": "object",
                "properties": {
                    "cluster_name": {"type": "string", "description": "EKS cluster name"},
                    "region": {"type": "string", "description": "AWS region"}
                },
                "required": ["cluster_name", "region"]
            }
        ),
        Tool(
            name="get_eks_node_groups",
            description="List node groups for an EKS cluster",
            inputSchema={
                "type": "object",
                "properties": {
                    "cluster_name": {"type": "string", "description": "EKS cluster name"},
                    "region": {"type": "string", "description": "AWS region"}
                },
                "required": ["cluster_name", "region"]
            }
        ),
        Tool(
            name="scale_node_group",
            description="Scale an EKS node group",
            inputSchema={
                "type": "object",
                "properties": {
                    "cluster_name": {"type": "string", "description": "EKS cluster name"},
                    "node_group_name": {"type": "string", "description": "Node group name"},
                    "region": {"type": "string", "description": "AWS region"},
                    "desired_size": {"type": "integer", "description": "Desired number of nodes"},
                    "min_size": {"type": "integer", "description": "Minimum nodes (optional)"},
                    "max_size": {"type": "integer", "description": "Maximum nodes (optional)"}
                },
                "required": ["cluster_name", "node_group_name", "region", "desired_size"]
            }
        )
    ]


def generate_eks_terraform_files(cluster_name: str, config: Dict) -> Path:
    """Generate complete Terraform files for EKS cluster."""
    cluster_path = Path(EKS_WORKSPACE) / cluster_name
    cluster_path.mkdir(parents=True, exist_ok=True)

    region = config.get("region", "us-east-1")
    k8s_version = config.get("kubernetes_version", "1.29")
    vpc_cidr = config.get("vpc_cidr", "10.0.0.0/16")
    node_config = config.get("node_group_config", {})
    tags = config.get("tags", {})

    # Main Terraform configuration
    main_tf = f"""terraform {{
  required_version = ">= 1.0"

  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }}
  }}
}}

provider "aws" {{
  region = var.aws_region
}}

# VPC Module
module "vpc" {{
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${{var.cluster_name}}-vpc"
  cidr = var.vpc_cidr

  azs             = ["${{var.aws_region}}a", "${{var.aws_region}}b", "${{var.aws_region}}c"]
  private_subnets = [for k, v in module.vpc.azs : cidrsubnet(var.vpc_cidr, 4, k)]
  public_subnets  = [for k, v in module.vpc.azs : cidrsubnet(var.vpc_cidr, 8, k + 48)]

  enable_nat_gateway   = true
  single_nat_gateway   = false
  enable_dns_hostnames = true
  enable_dns_support   = true

  public_subnet_tags = {{
    "kubernetes.io/role/elb" = "1"
  }}

  private_subnet_tags = {{
    "kubernetes.io/role/internal-elb" = "1"
  }}

  tags = merge(var.tags, {{
    "kubernetes.io/cluster/${{var.cluster_name}}" = "shared"
  }})
}}

# EKS Cluster
module "eks" {{
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = var.cluster_name
  cluster_version = var.kubernetes_version

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  cluster_endpoint_public_access = true

  {"enable_irsa = true" if config.get("enable_irsa", True) else ""}

  eks_managed_node_groups = {{
    default = {{
      name            = "${{var.cluster_name}}-node-group"
      instance_types  = var.node_instance_types
      desired_size    = var.node_desired_size
      min_size        = var.node_min_size
      max_size        = var.node_max_size
      disk_size       = var.node_disk_size

      labels = {{
        role = "general"
      }}

      tags = var.tags
    }}
  }}

  tags = var.tags
}}

{"" if not config.get("enable_ebs_csi", True) else '''
# EBS CSI Driver IAM Role
module "ebs_csi_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.0"

  role_name = "${var.cluster_name}-ebs-csi-driver"

  attach_ebs_csi_policy = true

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:ebs-csi-controller-sa"]
    }
  }

  tags = var.tags
}

# Install EBS CSI Driver
resource "aws_eks_addon" "ebs_csi" {
  cluster_name             = module.eks.cluster_name
  addon_name               = "aws-ebs-csi-driver"
  service_account_role_arn = module.ebs_csi_irsa.iam_role_arn

  depends_on = [module.eks]
}
'''}

{"" if not config.get("enable_cluster_autoscaler", False) else '''
# Cluster Autoscaler IAM Role
module "cluster_autoscaler_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.0"

  role_name = "${var.cluster_name}-cluster-autoscaler"

  attach_cluster_autoscaler_policy = true
  cluster_autoscaler_cluster_names = [module.eks.cluster_name]

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:cluster-autoscaler"]
    }
  }

  tags = var.tags
}
'''}
"""

    variables_tf = f"""variable "aws_region" {{
  description = "AWS region"
  type        = string
  default     = "{region}"
}}

variable "cluster_name" {{
  description = "EKS cluster name"
  type        = string
  default     = "{cluster_name}"
}}

variable "kubernetes_version" {{
  description = "Kubernetes version"
  type        = string
  default     = "{k8s_version}"
}}

variable "vpc_cidr" {{
  description = "VPC CIDR block"
  type        = string
  default     = "{vpc_cidr}"
}}

variable "node_instance_types" {{
  description = "Node instance types"
  type        = list(string)
  default     = {json.dumps(node_config.get("instance_types", ["t3.medium"]))}
}}

variable "node_desired_size" {{
  description = "Desired number of nodes"
  type        = number
  default     = {node_config.get("desired_size", 2)}
}}

variable "node_min_size" {{
  description = "Minimum number of nodes"
  type        = number
  default     = {node_config.get("min_size", 1)}
}}

variable "node_max_size" {{
  description = "Maximum number of nodes"
  type        = number
  default     = {node_config.get("max_size", 4)}
}}

variable "node_disk_size" {{
  description = "Node disk size in GB"
  type        = number
  default     = {node_config.get("disk_size", 20)}
}}

variable "tags" {{
  description = "Tags for all resources"
  type        = map(string)
  default     = {json.dumps(tags)}
}}
"""

    outputs_tf = """output "cluster_id" {
  description = "EKS cluster ID"
  value       = module.eks.cluster_id
}

output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "cluster_security_group_id" {
  description = "Security group ID attached to the EKS cluster"
  value       = module.eks.cluster_security_group_id
}

output "cluster_iam_role_arn" {
  description = "IAM role ARN of the EKS cluster"
  value       = module.eks.cluster_iam_role_arn
}

output "cluster_certificate_authority_data" {
  description = "Base64 encoded certificate data"
  value       = module.eks.cluster_certificate_authority_data
  sensitive   = true
}

output "oidc_provider_arn" {
  description = "ARN of the OIDC Provider for IRSA"
  value       = module.eks.oidc_provider_arn
}

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "private_subnets" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnets
}

output "public_subnets" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnets
}

output "configure_kubectl" {
  description = "Command to configure kubectl"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${var.cluster_name}"
}
"""

    # Write files
    (cluster_path / "main.tf").write_text(main_tf)
    (cluster_path / "variables.tf").write_text(variables_tf)
    (cluster_path / "outputs.tf").write_text(outputs_tf)

    return cluster_path


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls for EKS operations."""

    try:
        if name == "generate_eks_terraform":
            cluster_name = arguments["cluster_name"]
            cluster_path = generate_eks_terraform_files(cluster_name, arguments)

            return [TextContent(
                type="text",
                text=f"✓ EKS Terraform configuration generated\n\nLocation: {cluster_path}\n\nFiles created:\n- main.tf\n- variables.tf\n- outputs.tf\n\nNext steps:\n1. Review the configuration\n2. Run: eks_terraform_init\n3. Run: eks_terraform_plan\n4. Run: eks_terraform_apply"
            )]

        elif name == "eks_terraform_init":
            cluster_path = Path(EKS_WORKSPACE) / arguments["cluster_name"]
            if not cluster_path.exists():
                return [TextContent(type="text", text=f"Error: Cluster directory not found. Generate Terraform first.")]

            result = subprocess.run(
                ["terraform", "init"],
                cwd=cluster_path,
                capture_output=True,
                text=True
            )
            return [TextContent(type="text", text=f"Exit code: {result.returncode}\n\n{result.stdout}\n{result.stderr}")]

        elif name == "eks_terraform_plan":
            cluster_path = Path(EKS_WORKSPACE) / arguments["cluster_name"]
            result = subprocess.run(
                ["terraform", "plan"],
                cwd=cluster_path,
                capture_output=True,
                text=True
            )
            return [TextContent(type="text", text=f"Exit code: {result.returncode}\n\n{result.stdout}\n{result.stderr}")]

        elif name == "eks_terraform_apply":
            cluster_path = Path(EKS_WORKSPACE) / arguments["cluster_name"]
            cmd = ["terraform", "apply"]
            if arguments.get("auto_approve", False):
                cmd.append("-auto-approve")

            result = subprocess.run(cmd, cwd=cluster_path, capture_output=True, text=True)
            return [TextContent(type="text", text=f"Exit code: {result.returncode}\n\n{result.stdout}\n{result.stderr}")]

        elif name == "eks_terraform_destroy":
            cluster_path = Path(EKS_WORKSPACE) / arguments["cluster_name"]
            cmd = ["terraform", "destroy"]
            if arguments.get("auto_approve", False):
                cmd.append("-auto-approve")

            result = subprocess.run(cmd, cwd=cluster_path, capture_output=True, text=True)
            return [TextContent(type="text", text=f"Exit code: {result.returncode}\n\n{result.stdout}\n{result.stderr}")]

        elif name == "configure_kubectl":
            cmd = [
                "aws", "eks", "update-kubeconfig",
                "--region", arguments["region"],
                "--name", arguments["cluster_name"]
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return [TextContent(type="text", text=f"✓ kubectl configured\n\n{result.stdout}\n\nTest with: kubectl get nodes")]

        elif name == "install_addon":
            addon = arguments["addon_name"]
            cluster_name = arguments["cluster_name"]
            region = arguments["region"]

            # Ensure kubectl is configured
            subprocess.run([
                "aws", "eks", "update-kubeconfig",
                "--region", region, "--name", cluster_name
            ], capture_output=True)

            if addon == "aws-load-balancer-controller":
                # Install using Helm
                commands = [
                    ["helm", "repo", "add", "eks", "https://aws.github.io/eks-charts"],
                    ["helm", "repo", "update"],
                    ["helm", "install", "aws-load-balancer-controller", "eks/aws-load-balancer-controller",
                     "-n", "kube-system", "--set", f"clusterName={cluster_name}"]
                ]
            elif addon == "metrics-server":
                commands = [
                    ["kubectl", "apply", "-f", "https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml"]
                ]
            elif addon == "cluster-autoscaler":
                commands = [
                    ["helm", "repo", "add", "autoscaler", "https://kubernetes.github.io/autoscaler"],
                    ["helm", "install", "cluster-autoscaler", "autoscaler/cluster-autoscaler",
                     "--set", f"autoDiscovery.clusterName={cluster_name}"]
                ]
            else:
                return [TextContent(type="text", text=f"Add-on {addon} installation not implemented yet")]

            outputs = []
            for cmd in commands:
                result = subprocess.run(cmd, capture_output=True, text=True)
                outputs.append(f"Command: {' '.join(cmd)}\n{result.stdout}\n{result.stderr}")

            return [TextContent(type="text", text="\n\n".join(outputs))]

        elif name == "upgrade_eks_cluster":
            import boto3
            eks = boto3.client("eks", region_name=arguments["region"])

            response = eks.update_cluster_version(
                name=arguments["cluster_name"],
                version=arguments["target_version"]
            )

            return [TextContent(
                type="text",
                text=f"✓ Cluster upgrade initiated\n\nUpdate ID: {response['update']['id']}\nStatus: {response['update']['status']}\n\nMonitor with: aws eks describe-update --region {arguments['region']} --name {arguments['cluster_name']} --update-id {response['update']['id']}"
            )]

        elif name == "list_eks_clusters":
            import boto3
            eks = boto3.client("eks", region_name=arguments.get("region", "us-east-1"))
            response = eks.list_clusters()
            clusters = response.get("clusters", [])
            return [TextContent(type="text", text=f"EKS Clusters:\n" + "\n".join(f"- {c}" for c in clusters) if clusters else "No clusters found")]

        elif name == "describe_eks_cluster":
            import boto3
            eks = boto3.client("eks", region_name=arguments["region"])
            response = eks.describe_cluster(name=arguments["cluster_name"])
            cluster = response["cluster"]

            info = f"""Cluster: {cluster['name']}
Status: {cluster['status']}
Version: {cluster['version']}
Endpoint: {cluster['endpoint']}
Created: {cluster['createdAt']}
ARN: {cluster['arn']}
VPC: {cluster['resourcesVpcConfig']['vpcId']}
Subnets: {', '.join(cluster['resourcesVpcConfig']['subnetIds'])}
"""
            return [TextContent(type="text", text=info)]

        elif name == "get_eks_node_groups":
            import boto3
            eks = boto3.client("eks", region_name=arguments["region"])
            response = eks.list_nodegroups(clusterName=arguments["cluster_name"])
            node_groups = response.get("nodegroups", [])

            if not node_groups:
                return [TextContent(type="text", text="No node groups found")]

            details = []
            for ng in node_groups:
                ng_detail = eks.describe_nodegroup(
                    clusterName=arguments["cluster_name"],
                    nodegroupName=ng
                )["nodegroup"]
                details.append(f"""
Node Group: {ng_detail['nodegroupName']}
Status: {ng_detail['status']}
Instance Types: {', '.join(ng_detail['instanceTypes'])}
Scaling: {ng_detail['scalingConfig']['desiredSize']} (min: {ng_detail['scalingConfig']['minSize']}, max: {ng_detail['scalingConfig']['maxSize']})
""")

            return [TextContent(type="text", text="\n".join(details))]

        elif name == "scale_node_group":
            import boto3
            eks = boto3.client("eks", region_name=arguments["region"])

            scaling_config = {"desiredSize": arguments["desired_size"]}
            if "min_size" in arguments:
                scaling_config["minSize"] = arguments["min_size"]
            if "max_size" in arguments:
                scaling_config["maxSize"] = arguments["max_size"]

            eks.update_nodegroup_config(
                clusterName=arguments["cluster_name"],
                nodegroupName=arguments["node_group_name"],
                scalingConfig=scaling_config
            )

            return [TextContent(type="text", text=f"✓ Node group scaling updated\nDesired: {arguments['desired_size']}")]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Main entry point for the MCP server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
