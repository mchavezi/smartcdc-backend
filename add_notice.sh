#!/bin/bash

# Define the notice text
NOTICE_TEXT="# ===================================================\n\
# NOTICE: This file is part of a private repository.\n\
# Provided for demonstration purposes only.\n\
# Not suitable for production use.\n\
# ===================================================\n"

# Directories to exclude
EXCLUDE_DIRS=( "./venv" "./.git" "./migrations" "./__pycache__" )

# Function to add notice to a file
add_notice_to_file() {
    local file="$1"

    # Check if the notice is already present
    if grep -q "NOTICE: This file is part of a private repository" "$file"; then
        echo "Skipping $file, notice already present."
        return
    fi

    # Create a temp file and prepend the notice
    temp_file=$(mktemp)
    echo -e "$NOTICE_TEXT\n$(cat "$file")" > "$temp_file"
    mv "$temp_file" "$file"

    echo "Updated $file"
}

# Process all Python files in the repository while excluding directories
process_repository() {
    find . -type d \( -path "${EXCLUDE_DIRS[0]}" -o -path "${EXCLUDE_DIRS[1]}" -o -path "${EXCLUDE_DIRS[2]}" -o -path "${EXCLUDE_DIRS[3]}" \) -prune -o \
           -type f -name "*.py" -print | while read -r file; do
        add_notice_to_file "$file"
    done
}

# Run the script
process_repository
