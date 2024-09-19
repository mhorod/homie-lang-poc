#!/bin/bash
mkdir -p build
nasm -f elf64 -o build/libhomie.o libhomie.asm && python3 main.py > build/main.asm && nasm -f elf64 -o build/main.o build/main.asm &&
 ld build/main.o build/libhomie.o -o build/program.out && ./build/program.out