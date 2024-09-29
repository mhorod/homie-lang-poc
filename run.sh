#!/bin/bash
(mkdir -p build &&
gcc -o build/libhomie.o -c -nostdlib -fno-stack-protector libhomie.c &&
python3 src/main.py $1 > build/main.asm &&
nasm -f elf64 -o build/main.o build/main.asm &&
ld build/main.o build/libhomie.o -o build/program.out) || exit 1
./build/program.out || true
