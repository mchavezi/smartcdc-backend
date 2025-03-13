#!/bin/bash

# Define the output file
output_file="issue.md"

# Clear the output file if it already exists
> "$output_file"

# List of directories to search, including some_dir with all nested files
directories=( 
  # "resources/postgres_database"
  # "resources/postgres_replication_slot"
  # "."
  # "services/wal_listener"
  # "resources/user"
  "resources/postgres_database"
  "resources/postgres_replication_slot"
  "services/wal_listener"
  # "resources/wal_events"
  # "services/wal_listener/wal_listener_service.py"
  # "services/wal_listener/postgres_decoder.py"
  # "alembic.ini"
  # "env.py"
  # "alembic/versions"
  # "services/wal_listener"
  # "backend/resources/postgres_database"
)

# Loop through each directory in the list
for dir in "${directories[@]}"; do
  # Find all .py files in the specified directory and its subdirectories
  find $dir -type f -name "*.py" 2>/dev/null | while read -r file; do
    echo "**$file**" >> "$output_file"
    echo '```python' >> "$output_file"
    cat "$file" >> "$output_file"
    echo '```' >> "$output_file"
    
    # Add a newline to separate the sections
    echo >> "$output_file"
  done
done

echo "Done! Check $output_file for the results."
