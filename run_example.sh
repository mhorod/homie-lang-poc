#!/bin/bash

for path in $(find examples -type f -name $1.hom); do
    python3 src/main.py ${path}
done;
