#!/bin/bash

# Ensure required environment variables are set
: "${DB_HOST:?Environment variable DB_HOST is required}"
: "${DB_PORT:?Environment variable DB_PORT is required}"
: "${DB_NAME:?Environment variable DB_NAME is required}"
: "${DB_USER:?Environment variable DB_USER is required}"
: "${DB_PASSWORD:?Environment variable DB_PASSWORD is required}"
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

# Function to clear database storage by removing logs, vacuuming, and clearing old data
clear_storage() {
  echo "Connecting to PostgreSQL database to clear storage..."

  PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "VACUUM FULL;"

  if [ $? -eq 0 ]; then
    echo "Successfully ran VACUUM FULL to reclaim space."
  else
    echo "Failed to run VACUUM FULL."
  fi

  # Optionally, delete old logs (adjust as necessary)
  echo "Deleting old logs..."
  PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "DELETE FROM pg_stat_activity WHERE state = 'idle' AND state_change < NOW() - INTERVAL '7 days';"

  if [ $? -eq 0 ]; then
    echo "Successfully cleared old logs."
  else
    echo "Failed to clear old logs."
  fi

  # Optional: Check autovacuum settings
  echo "Checking autovacuum settings..."
  PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SHOW autovacuum;"
}

# Main script execution
start_rds_instance
clear_storage
