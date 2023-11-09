// Configurações Principais do Terraform
terraform {
  required_providers {
    // Seleção do Provider (Cloud)
    aws = {
      source  = "hashicorp/aws"
      version = "3.70.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "3.1.0"
    }
  }
  backend "azurerm" {
    storage_account_name = "blockbittfstate"
    container_name       = "blockbit-tfstate"
    key                  = "blockbit-pr-analyzer/blockbit-tfstate"
    access_key           = "Gyth73Wh3C521r47ahfUSbX9NLU5baySv4cgZmu7OV7M3Gqr1JiFROXo2ARwjSFGuQVwTxLB6iZ/+ASto9lKJQ=="
  }
}


// Provider sera usado por padrao o Norte da Virgnia
provider "aws" {
  region = "us-east-1"
}

provider "azurerm" {
  features {}
  subscription_id = "1f68070e-4bb7-404f-8a43-a767171c871c"
}

// Perfil padrao na maquina
data "aws_caller_identity" "current" {
}