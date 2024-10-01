from enum import Enum, auto
from dataclasses import dataclass

from tree import *
from error_reporting import *

from typechecking.convert import *

class ExhaustivenessStatus(Enum):
    All = auto()
    Missing = auto()

@dataclass
class ExhaustivenessResult:
    status: ExhaustivenessStatus
    missing: TyPattern | None

    def All():
        return ExhaustivenessResult(ExhaustivenessStatus.All, None)

    def Missing(missing):
        return ExhaustivenessResult(ExhaustivenessStatus.Missing, missing)




class ExhaustivenessChecker:
    def __init__(self, report, ctx: TypingContext):
        self.report = report
        self.ctx = ctx
        self.type_converter = TypeConverter(report, ctx)

    def check_fit_exhaustiveness(self, fit: FitExprNode, expr_ty: Ty):
        patterns = [
            self.type_converter.convert_pattern(branch.left)
            for branch in fit.branches
        ]
        dis = self.ctx.get_dis(expr_ty.name)
        result = self.check_patterns_exhaust_dis(dis, expr_ty.generic_types, patterns)

        if result.status == ExhaustivenessStatus.Missing:
            self.report.error(fit_is_not_exhaustive(fit, result.missing))

    def check_patterns_exhaust_type(self, ty, patterns):
        if isinstance(ty, FunTy):
            if len(patterns) == 0:
                return ExhaustivenessResult.Missing(CatchallPattern())
            else:
                return ExhaustivenessResult.All()
        elif isinstance(ty, DisTy):
            decl = self.ctx.get_dis(ty.name)
            return self.check_patterns_exhaust_dis(decl, ty.generic_types, patterns)
        elif isinstance(ty, SimpleType) or isinstance(ty, TyVar):
            if self.patterns_contain_catchall(patterns):
                return ExhaustivenessResult.All()
            else:
                return ExhaustivenessResult.Missing(CatchallPattern())
        else:
            raise Exception("Unexpected type: ", ty)

    def patterns_contain_catchall(self, patterns):
        return any(isinstance(p, CatchallPattern) for p in patterns)

    def check_patterns_exhaust_dis(self, dis: DisDeclaration, generics, patterns: List[TyPattern]):
        if any(isinstance(pat, CatchallPattern) for pat in patterns):
            return ExhaustivenessResult.All()
        else:
            variants = {
                v.name: (v, [])
                for v in dis.variants
            }
            for pat in patterns:
                variants[pat.name][1].append(pat)

            for _, (v, patterns) in variants.items():
                result = self.check_patterns_exhaust_variant(v, generics, patterns)
                if result.status == ExhaustivenessStatus.Missing:
                    return result
            return ExhaustivenessResult.All()

    def check_patterns_exhaust_variant(self, variant: VariantDeclaration, generics, patterns: List[TyPattern]):
        if len(patterns) == 0:
            pat = TyPattern(variant.name, [CatchallPattern() for _ in variant.args])
            return ExhaustivenessResult.Missing(pat)
        else:
            result = self.check_patterns_exhaust_variant_args(variant.args, generics, patterns, 0, [])
            if result.status == ExhaustivenessStatus.All:
                return result
            else:
                missing = TyPattern(variant.name, result.missing)
                return ExhaustivenessResult.Missing(missing)



    def check_patterns_exhaust_variant_args(self, args, generics, patterns: List[TyPattern], index, current_pattern):
        if index >= len(args):
            return ExhaustivenessResult.All()
        elif len(patterns) == 0:
            missing = current_pattern + [args[0]] + [CatchallPattern() for _ in range(index + 1, len(args))]
            return ExhaustivenessResult.Missing(args[0])

        arg = args[index].ty
        arg = substitute(arg, generics)

        arg_pats = [pattern.children[index] for pattern in patterns]

        arg_cov = self.check_patterns_exhaust_type(arg, self.exclude_catchall(arg_pats))

        if arg_cov.status == ExhaustivenessStatus.All:
            grouped = { pat: [] for pat in arg_pats if not isinstance(pat, CatchallPattern)}
            catchall = [pattern for pattern in patterns if isinstance(pattern.children[index], CatchallPattern)]
            for pat in patterns:
                if not isinstance(pat.children[index], CatchallPattern):
                    grouped[pat.children[index]].append(pat)
            for p, pats in grouped.items():
                pats = pats + catchall
                result = self.check_patterns_exhaust_variant_args(args, generics, pats, index + 1, current_pattern + [p])
                if result.status == ExhaustivenessStatus.Missing:
                    return result
            return ExhaustivenessResult.All()
        else:
            new_patterns = [pattern for pattern in patterns if isinstance(pattern.children[index], CatchallPattern)]
            if len(new_patterns) == 0:
                missing = current_pattern + [arg_cov.missing] + [CatchallPattern() for _ in range(index + 1, len(args))]
                return ExhaustivenessResult.Missing(missing)
            else:
                return self.check_patterns_exhaust_variant_args(args, generics, new_patterns, index + 1, current_pattern + [CatchallPattern()])


    def exclude_catchall(self, patterns: List[TyPattern]):
        return [pat for pat in patterns if not isinstance(pat, CatchallPattern)]
