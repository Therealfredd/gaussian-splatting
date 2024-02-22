#!/bin/bash

read -p "Enter the directory: " directory
for s in "$directory"/*; do
    if [ -d "$s" ]; then
        echo "Training model: $s"
        python train.py -s "$s"
        echo "$s Trained."
    fi
done
echo "Training complete."
