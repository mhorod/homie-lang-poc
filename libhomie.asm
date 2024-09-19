section .bss
    global heap
    heap: resq 1
    heap_end: resq 1

section .text
    global _start
    global _make_obj
    extern main

%define MAP_GROWSDOWN 256
%define MAP_ANONYMOUS 32
%define MAP_PRIVATE 2
%define PROT_READ 1 
%define PROT_WRITE 2 

%define SYS_MMAP 9
%define SYS_EXIT 60

_start:
    mov rax, SYS_MMAP
    mov rdi, 0
    mov rsi, 4096
    mov rdx, PROT_READ | PROT_WRITE
    mov r10, MAP_ANONYMOUS | MAP_PRIVATE | MAP_GROWSDOWN
    mov r8, -1
    mov r9, 0
    syscall

    mov [heap], rax
    mov [heap_end], rax

    mov r12, 0x00ffffffffffffff
    call main

    mov rax, SYS_EXIT
    xor rdi, rdi
    syscall

_make_obj:
    mov rax, [heap_end] ; heap end
    pop rsi ; return pointer
    pop rbx ; object type
    pop rdx ; argument count 
    cmp rdx, 0
    je read_args_end
    mov rcx, rdx ; loop counter
    read_args:
        sub rax, 8
        pop qword [rax]
        loop read_args
    mov [heap_end], rax
    read_args_end:
    
    ; make funny pointer (1 byte for object type, 7 bytes for position on heap)
    sub rax, [heap]
    neg rax
    shl rbx, 56
    or rax, rbx

    push rsi
    ret