#!/bin/bash
for file in "$@"; do
    echo "Processing $file"
    awk '
    NR < 10 {print; next}
    /^---$/ {print "##"; next}
    {print}
    ' "$file" > "${file}.tmp" && mv "${file}.tmp" "$file"
done
