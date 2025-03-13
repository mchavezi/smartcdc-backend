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

# Function to stop the RDS instance
stop_rds_instance() {
  echo "Stopping RDS instance: $RDS_IDENTIFIER in region $AWS_REGION..."
  aws rds stop-db-instance --db-instance-identifier "$RDS_IDENTIFIER" --region "$AWS_REGION"
  
  if [ $? -eq 0 ]; then
    echo "Successfully initiated stopping of RDS instance: $RDS_IDENTIFIER"
  else
    echo "Failed to stop RDS instance: $RDS_IDENTIFIER"
  fi
}

# Main script execution
stop_rds_instance
