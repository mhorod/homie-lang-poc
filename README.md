# Epic Homie Language

Prototype made to prepare for Compiler course

## Homie

Goals:
- ADT with pattern matching
- strong static typing
- Garbage Collector


## Example

Merge sort:
```
dis List[T] {
    Nil,
    Cons(x: T, xs: List[T])
}

dis Pair[T, U] {
    Pair(fst: T, snd: U)
}

dis Nat {
    Zero,
    Succ(n: Nat)
}

dis Bool {
    True,
    False
}

fun less(a: Nat, b: Nat) -> Bool {
    ret fit Pair::Pair a b {
        Pair _ Zero => Bool::False,
        Pair Zero _ => Bool::True,
        _ => less a.n b.n
    };
}

fun half[T](xs: List[T]) -> Pair[List[T], List[T]] {
    let rest = fit xs {
        Nil => Pair::Pair List::Nil List::Nil,
        Cons _ Nil => Pair::Pair xs List::Nil,
        Cons _ (Cons _ _) => half xs.xs.xs
    };
    ret fit xs {
        Cons _ (Cons _ _) => Pair::Pair (List::Cons xs.x rest.fst) (List::Cons xs.xs.x rest.snd),
        _ => rest
    };
}

fun merge[T](xs: List[T], ys: List[T]) -> List[T] {
    ret fit Pair::Pair xs ys {
        Pair Nil Nil => List::Nil,
        Pair Nil _ => ys,
        Pair _ Nil => xs,
        Pair _ _ => fit less xs.x ys.x {
            True => List::Cons xs.x (merge xs.xs ys),
            False => List::Cons ys.x (merge xs ys.xs)
        }
    };
}

fun sort[T](xs: List[T]) -> List[T] {
    let halves = half xs;
    ret fit xs {
        Nil => List::Nil,
        Cons _ Nil => xs,
        Cons _ _ => merge (sort halves.fst) (sort halves.snd)
    };
}
```

