# epicki język na konkilatory

## Homie

`homie compile main.hom`

C tylko że lepszy, taki bez makr :)
- ADT
- strong static typing
- mattern patching

```



dis Joint(a: i32) {}
Foo a <-> Foo::_ a

Foo a <-> Call(Path(EnumType, EnumType), Variable)
Foo[Int]::A a
a.b.c a

enum IO[Self](_self: Self, read_line: Self -> String)

fun main(io: IO[?]) {
    io.read_line io._self;
}

fun foo(a: Int32, b: Int32) -> Bool {
    let s: Pat I32 = ?1 | ?2; // |(?1, ?2)
    let x = match a {
        (_, 1) => ...
        Foo 1 _
        _ => !
    };
}

bun OI {
    ext print_line;
}

dis Comparison {
    LT, EQ, GT
}

dis Cmp[T, Self](_self: Self, cmp: Self -> T -> T -> Comparison);

fun sort[T](xs: List[T], cmp: Cmp[T]) -> List[T] {
    ...
}

{
    cmp : CmplImpl -> Int -> Int -> Comparison [8b]
    _self : CmpImpl [8b]
}

fun max(cmp: Cmp[Int, ?], a: Int, b: Int) {
    return match cmp.cmp(a, b) {
        LT => b,
        EQ => b,
        GT => a
    };
}

{
max:
    // rax = wskaźnik na cmp
    // rbx = wskaźnik na a
    // rcx = wskaźnik na b    

    mov rdx [rsp-16]

    push rbp
    mov rbp rsp
    call rdx // cmp.cmp

    mov rax 8
    syscall malloc


}}


fun main() {
    let xs = [5, 4, 3, 2, 1];
    giv Cmp[Int] = builtin;
    xs = sort xs;
}

enum Lambda {
    Var(idx: Int),
    Abs(Lambda),
    App(Lambda, Lambda)
}

enum List[T] {
    Nil,
    Cons(T, List[T])
}

fun exec(l: Lambda, ctx: List[Lambda]) -> Lambda {
    match l {
        Var i => index i ctx,
        Abs _ => exec l ctx,
        App a b => match a {
            Abs abstracted => {
                exec abstracted (push ctx b)
            }
            _ => l
        }
    }
}


```

GC:
```
struct GC {
    set<void*> pointers_on_stack;
    set<void*> all_pointers;
    map<void*, deque<void*>> edges;

    void gc() {
        queue<void*> q(pointers_on_stack);
        set<void*> visited;
        // BFS
        all_points = visited; // skasuj nieosiągalne 
    }
}


```