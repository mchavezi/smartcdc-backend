#!/bin/bash

# Load environment variables from .env file if it exists
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
else
  echo ".env file not found. Please create one with the required variables."
  exit 1
fi

# Ensure required environment variables are set
: "${AWS_REGION:?Environment variable AWS_REGION is required}"
: "${RDS_IDENTIFIER:?Environment variable RDS_IDENTIFIER is required}"

# Function to start the RDS instance
start_rds_instance() {
  echo "Starting RDS instance: $RDS_IDENTIFIER in region $AWS_REGION..."
  aws rds start-db-instance --db-instance-identifier "$RDS_IDENTIFIER" --region "$AWS_REGION"
  
  if [ $? -eq 0 ]; then
    echo "Successfully initiated starting of RDS instance: $RDS_IDENTIFIER"
  else
    echo "Failed to start RDS instance: $RDS_IDENTIFIER"
  fi
}

# Main script execution
start_rds_instance
