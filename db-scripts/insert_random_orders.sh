#!/bin/bash

# Load environment variables from .env file if it exists
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
else
  echo ".env file not found. Please create one with the required variables."
  exit 1
fi

# Ensure required environment variables are set
: "${DB_HOST:?Environment variable DB_HOST is required}"
: "${DB_PORT:?Environment variable DB_PORT is required}"
: "${DB_NAME:?Environment variable DB_NAME is required}"
: "${DB_USER:?Environment variable DB_USER is required}"
: "${DB_PASSWORD:?Environment variable DB_PASSWORD is required}"
: "${TABLE_NAME:?Environment variable TABLE_NAME is required}"
: "${NUMBER_OF_ORDERS:?Environment variable NUMBER_OF_ORDERS is required}"

# Random data generation arrays
CUSTOMER_NAMES=("John Doe" "Jane Smith" "Alice Johnson" "Bob Brown" "Mary Davis" "Steve Williams" "Linda Martinez" "Michael Garcia" "Emily Taylor" "Paul White")
ADDRESSES=("123 Maple Street, Springfield, USA" "456 Oak Avenue, Springfield, USA" "789 Pine Road, Springfield, USA" "321 Cedar Street, Springfield, USA" "654 Elm Avenue, Springfield, USA")
STATUSES=("Pending" "Processing" "Completed" "Cancelled")

# Export password for psql
export PGPASSWORD="$DB_PASSWORD"

# Check if the table exists and create it if not
echo "Checking if table '$TABLE_NAME' exists..."
SQL_CHECK_TABLE=$(cat <<EOF
DO \$\$
BEGIN
  IF NOT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = '$TABLE_NAME'
  ) THEN
    EXECUTE 'CREATE TABLE $TABLE_NAME (
      id SERIAL PRIMARY KEY,
      customer_name VARCHAR(255),
      total_amount NUMERIC(10, 2),
      shipping_address TEXT,
      status VARCHAR(50),
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );';
  END IF;
END
\$\$;
EOF
)

psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$SQL_CHECK_TABLE"
if [ $? -ne 0 ]; then
  echo "Error creating or verifying the table."
  exit 1
fi

# Generate and insert random orders
echo "Inserting random orders into '$TABLE_NAME'..."
for ((i=1; i<=NUMBER_OF_ORDERS; i++)); do
  CUSTOMER_NAME=${CUSTOMER_NAMES[$RANDOM % ${#CUSTOMER_NAMES[@]}]}
  ADDRESS=${ADDRESSES[$RANDOM % ${#ADDRESSES[@]}]}
  STATUS=${STATUSES[$RANDOM % ${#STATUSES[@]}]}
  TOTAL_AMOUNT=$(printf "%.2f" "$(echo "$RANDOM % 500 + 50 + $RANDOM / 32768" | bc -l)")

  SQL_INSERT="INSERT INTO $TABLE_NAME (customer_name, total_amount, shipping_address, status)
               VALUES ('$CUSTOMER_NAME', $TOTAL_AMOUNT, '$ADDRESS', '$STATUS');"

  echo "Executing: $SQL_INSERT"
  psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$SQL_INSERT"
  if [ $? -ne 0 ]; then
    echo "Error inserting order: $CUSTOMER_NAME"
  fi
done

echo "Inserted $NUMBER_OF_ORDERS random orders into the $TABLE_NAME table."

# Unset password
unset PGPASSWORD
