typedef unsigned long size_t;

typedef struct H1Frame {
    int visited;
    int attached;
    void * children[1];
} H1Frame;

typedef struct H3Frame {
    int visited;
    int attached;
    void * children[3];
} H3Frame;

typedef struct H7Frame {
    int visited;
    int attached;
    void * children[7];
} H7Frame;

#define SYS_MMAP 9
#define SYS_EXIT 60

#define PROT_READ 1
#define PROT_WRITE 2
#define MAP_ANONYMOUS 32
#define MAP_PRIVATE 2

#define NULL ((void *) 0)

static void * mmap(void * addr, size_t length) {
    void * result;
    register long r10 asm("r10") = MAP_ANONYMOUS | MAP_PRIVATE;
    register long r8 asm("r8") = -1;
    register long r9 asm("r9") = 0;
    asm volatile
    (
        "syscall"
        : "=a"(result)
        : "a"(SYS_MMAP), "D"(addr), "S"(length), "d"(PROT_READ | PROT_WRITE), "r"(r10), "r"(r8), "r"(r9)
        : "rcx", "r11", "memory"
    );
    return result;
}

static void exit(int error_code)
{
    asm volatile
    (
        "syscall"
        :
        : "a"(SYS_EXIT), "D"(error_code)
        : "rcx", "r11", "memory"
    );
    while(1);
}

typedef struct Heap {
    void * content;
    void ** gaps;
    size_t gap_count;
    size_t capacity;
    size_t elem_size;
} Heap;

Heap H1;
Heap H3;
Heap H7;

Heap *HEAPS[] = {&H1, &H3, &H7, NULL};

static void push_gap(Heap * heap, void * gap) {
    heap->gaps[heap->gap_count] = gap;
    heap->gap_count++;
}

static void push_gaps(Heap * heap, void * new_space, size_t elem_count) {
    for(void * i = new_space; i < new_space + elem_count * heap->elem_size; i += heap->elem_size) {
        push_gap(heap, i);
    }
}

static void grow(Heap * heap, size_t elem_count) {
    void * new_space = heap->content + heap->capacity * heap->elem_size;
    mmap(new_space, elem_count * heap->elem_size);
    mmap(heap->gaps + heap->capacity, elem_count * sizeof(void *));
    push_gaps(heap, new_space, elem_count);
    heap->capacity += elem_count;
}

static void gc() {
    // TODO: actually collect garbage
    for(Heap ** heap = &HEAPS[0]; *heap != NULL; heap++)
        if((*heap)->gap_count == 0)
            grow(*heap, (*heap)->capacity);
}

static void * alloc(Heap * heap) {
    if(heap->gap_count == 0) gc();
    heap->gap_count--;
    return heap->gaps[heap->gap_count];
}

static void init(Heap * heap, size_t elem_count, size_t elem_size, void * heap_ptr, void * gaps_ptr) {
    heap->capacity = 0;
    heap->gap_count = 0;
    heap->elem_size = elem_size;
    heap->content = heap_ptr;
    heap->gaps = (void **) gaps_ptr;
    grow(heap, elem_count);
}


typedef unsigned long funny_ptr_t;

static long funny_ptr(void * ptr, long variant) {
    return ((long) ptr) | (variant << 56);
}

long _make_obj0(long * args) {
    return funny_ptr((void *) 0, args[0]);
}

long _make_obj1(long * args) {
    H1Frame * frame = (H1Frame *) alloc(&H1);
    frame->attached = 1;
    frame->visited = 0;
    frame->children[0] = (void *) args[1];
    return funny_ptr(&frame->children, args[0]);
}

long _make_obj3(long * args) {
    H3Frame * frame = (H3Frame *) alloc(&H3);
    frame->attached = 1;
    frame->visited = 0;
    frame->children[0] = (void *) args[1];
    frame->children[1] = (void *) args[2];
    frame->children[2] = (void *) args[3];
    return funny_ptr(&frame->children, args[0]);
}

long _make_obj7(long * args) {
    H7Frame * frame = (H7Frame *) alloc(&H7);
    frame->attached = 1;
    frame->visited = 0;
    frame->children[0] = (void *) args[1];
    frame->children[1] = (void *) args[2];
    frame->children[2] = (void *) args[3];
    frame->children[3] = (void *) args[4];
    frame->children[4] = (void *) args[5];
    frame->children[5] = (void *) args[6];
    frame->children[6] = (void *) args[7];
    return funny_ptr(&frame->children, args[0]);
}

#define INITIAL_HEAP_SIZE 512

extern int main();

void _start() {
    init(&H1, INITIAL_HEAP_SIZE, sizeof(H1Frame), (void *) 0x1000000000, (void *) 0x11000000000);
    init(&H3, INITIAL_HEAP_SIZE, sizeof(H3Frame), (void *) 0x2000000000, (void *) 0x12000000000);
    init(&H7, INITIAL_HEAP_SIZE, sizeof(H7Frame), (void *) 0x3000000000, (void *) 0x13000000000);
    main();
    exit(0);
}
