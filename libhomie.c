typedef unsigned long size_t;

typedef struct Frame {
    short visited;
    short exists;
    int attached;
    long children[];
} Frame;

typedef struct H1Frame {
    short visited;
    short exists;
    int attached;
    long children[1];
} H1Frame;

typedef struct H3Frame {
    short visited;
    short exists;
    int attached;
    long children[3];
} H3Frame;

typedef struct H7Frame {
    short visited;
    short exists;
    int attached;
    long children[7];
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
    Frame ** gaps;
    size_t gap_count;
    size_t capacity;
    size_t elem_size;
} Heap;

Heap H1;
Heap H3;
Heap H7;

void * H1_ADDR = (void *) 0x1000000000;
void * H3_ADDR = (void *) 0x2000000000;
void * H7_ADDR = (void *) 0x3000000000;

Heap *HEAPS[] = {&H1, &H3, &H7, NULL};

static void * ptr_from_funny(long funny) {
    if(funny >> 56 == 0) return NULL;
    return (void *) ((funny << 8) >> 8);
}

static size_t get_child_count(void * obj) {
    if(obj < H1_ADDR) return 0;
    if(obj < H3_ADDR) return 1;
    if(obj < H7_ADDR) return 3;
    return 7;
}

static void push_gap(Heap * heap, void * gap) {
    heap->gaps[heap->gap_count] = gap;
    heap->gap_count++;
}

static void push_gaps(Heap * heap, void * new_space, size_t elem_count) {
    for(void * i = new_space; i < new_space + elem_count * heap->elem_size; i += heap->elem_size)
        push_gap(heap, i);
}

static void init_frames(void * space, size_t elem_count, size_t elem_size) {
    for(size_t i = 0; i < elem_count; i++) {
        Frame * frame = (Frame *) (space + i * elem_size);
        frame->exists = 0;
        frame->attached = 0;
        for(int child = 0; child < elem_size / 8 - 1; child++)
            frame->children[child] = 0;
    }
}

static void grow(Heap * heap, size_t elem_count) {
    void * new_space = heap->content + heap->capacity * heap->elem_size;
    mmap(new_space, elem_count * heap->elem_size);
    init_frames(new_space, elem_count, heap->elem_size);
    mmap(heap->gaps + heap->capacity, elem_count * sizeof(void *));
    push_gaps(heap, new_space, elem_count);
    heap->capacity += elem_count;
}

static void clear_visited(Heap * heap) {
    for(size_t i = 0; i < heap->capacity; i++) {
        Frame * frame = (Frame *) (heap->content + i * heap->elem_size);
        frame->visited = 0;
    }
}

static void visit(void * obj) {
    size_t child_count = get_child_count(obj);
    if(child_count == 0) return;
    Frame * frame = (Frame *) (obj - 8);
    if(frame->visited) return;
    frame->visited = 1;
    for(size_t i = 0; i < child_count; i++)
        visit(ptr_from_funny(frame->children[i]));
}

static void visit_all(Heap * heap) {
    for(size_t i = 0; i < heap->capacity; i++) {
        Frame * frame = (Frame *) (heap->content + i * heap->elem_size);
        if(!frame->exists || frame->visited || !frame->attached) continue;
        visit(((void *) frame) + 8);
    }
}

static void recreate_stack(Heap * heap) {
    heap->gap_count = 0;
    for(size_t i = 0; i < heap->capacity; i++) {
        Frame * frame = (Frame *) (heap->content + i * heap->elem_size);
        if(!frame->visited) {
            frame->attached = 0;
            frame->exists = 0;
            push_gap(heap, (void *) frame);
        }
    }
}

static void gc() {
    for(Heap ** heap = &HEAPS[0]; *heap != NULL; heap++)
        clear_visited(*heap);
    for(Heap ** heap = &HEAPS[0]; *heap != NULL; heap++)
        visit_all(*heap);
    for(Heap ** heap = &HEAPS[0]; *heap != NULL; heap++)
        recreate_stack(*heap);
    for(Heap ** heap = &HEAPS[0]; *heap != NULL; heap++)
        if((*heap)->gap_count < (*heap)->capacity / 2)
            grow(*heap, (*heap)->capacity);
}

static Frame * alloc(Heap * heap) {
    if(heap->gap_count == 0) gc();
    heap->gap_count--;
    Frame * frame = heap->gaps[heap->gap_count];
    frame->exists = 1;
    return frame;
}

static void init(Heap * heap, size_t elem_count, size_t elem_size, void * heap_ptr, void * gaps_ptr) {
    heap->capacity = 0;
    heap->gap_count = 0;
    heap->elem_size = elem_size;
    heap->content = heap_ptr;
    heap->gaps = (Frame **) gaps_ptr;
    grow(heap, elem_count);
}

static long funny_ptr(void * ptr, long variant) {
    return ((long) ptr) | (variant << 56);
}

long _make_obj0(long * args) {
    return funny_ptr((void *) 0, args[0]);
}

long _make_obj1(long * args) {
    H1Frame * frame = (H1Frame *) alloc(&H1);
    frame->attached = 0;
    frame->visited = 0;
    frame->children[0] = args[1];
    return funny_ptr(&frame->children, args[0]);
}

long _make_obj3(long * args) {
    H3Frame * frame = (H3Frame *) alloc(&H3);
    frame->attached = 0;
    frame->visited = 0;
    frame->children[0] = args[1];
    frame->children[1] = args[2];
    frame->children[2] = args[3];
    return funny_ptr(&frame->children, args[0]);
}

long _make_obj7(long * args) {
    H3Frame * frame = (H3Frame *) alloc(&H7);
    frame->attached = 0;
    frame->visited = 0;
    frame->children[0] = args[1];
    frame->children[1] = args[2];
    frame->children[2] = args[3];
    frame->children[3] = args[4];
    frame->children[4] = args[5];
    frame->children[5] = args[6];
    frame->children[6] = args[7];
    return funny_ptr(&frame->children, args[0]);
}

void _detach_obj(long * args) {
    void * obj = ptr_from_funny(args[0]);
    if(obj == NULL) return;
    Frame * frame = (Frame *) (obj - 8);
    frame->attached--;
}


void _attach_obj(long * args) {
    void * obj = ptr_from_funny(args[0]);
    if(obj == NULL) return;
    Frame * frame = (Frame *) (obj - 8);
    frame->attached++;
}

#define INITIAL_HEAP_SIZE 512

extern void main();

void _start() {
    init(&H1, INITIAL_HEAP_SIZE, sizeof(H1Frame), H1_ADDR, (void *) 0x11000000000);
    init(&H3, INITIAL_HEAP_SIZE, sizeof(H3Frame), H3_ADDR, (void *) 0x12000000000);
    init(&H7, INITIAL_HEAP_SIZE, sizeof(H7Frame), H7_ADDR, (void *) 0x13000000000);
    main();
    exit(0);
}
