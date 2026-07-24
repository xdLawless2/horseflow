#!/usr/bin/env python3
"""Emit the reduced Proposition 4.3 ideals over a pure rational ring.

The algebraic coefficient theta is promoted to a polynomial variable and its
irreducible minimal polynomial is appended as an ideal generator. Rational
denominators are cleared generator-by-generator, preserving the characteristic-
zero zero set and avoiding coefficient-extension parser ambiguities in Singular.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sympy as sp

from model_linear_reduced import ROOT, derive, ring_expr


def primitive_integer(expr: sp.Expr, variables: list[sp.Symbol]) -> sp.Expr:
    numerator, _ = sp.fraction(sp.together(expr))
    poly = sp.Poly(sp.expand(numerator), *variables, domain=sp.QQ)
    _, poly = poly.primitive()
    if poly.LC() < 0:
        poly = -poly
    return poly.as_expr()


def sx(expr: sp.Expr) -> str:
    return str(sp.expand(expr)).replace("**", "^")


def emit(branch: tuple[int, int], basis: Path) -> Path:
    K, minpoly, S, A, B, V, consistency = derive(basis)
    ss, rr = branch
    z, p, q, h, k, theta = sp.symbols("z p q h k theta")
    ring_symbols = [p, q, h, k]
    all_variables = [z, p, q, h, k, theta]

    equations = [A[i] for i in range(1, rr)] + [B[i] for i in range(ss)] + consistency
    equations = [x for x in equations if x != S.zero]
    product = A[rr] * A[8] * V[12] * B[ss]
    expressions = [ring_expr(K, x, ring_symbols) for x in equations]
    expressions.append(z * ring_expr(K, product, ring_symbols) - 1)

    coefficients = [sp.Rational(c.numerator, c.denominator) for c in K.mod.to_list()]
    phi = sum(c * theta ** (len(coefficients) - 1 - i) for i, c in enumerate(coefficients))
    generators = [primitive_integer(e, all_variables) for e in expressions]
    generators.append(primitive_integer(phi, all_variables))

    tag = f"{ss}_{rr}"
    output = ROOT / f"linear_reduced_{tag}_QQ.sing"
    lines = [
        "option(redSB);",
        "ring r=0,(z,p,q,h,k,theta),dp;",
        "ideal I=",
        "  " + ",\n  ".join(sx(e) for e in generators) + ";",
        f'print("BRANCH {tag} INPUT "+string(size(I)));',
        "matrix T;",
        "ideal G=liftstd(I,T);",
        'print("GB "+string(size(G)));',
        f'if(size(G)==1 && G[1]==1){{print("BRANCH {tag}: UNIT");}}else{{print("BRANCH {tag}: NONUNIT");G;}}',
        "matrix CHECK=matrix(G)-matrix(I)*T;",
        'if(CHECK==0){print("LIFT_CHECK: ZERO");}else{print("LIFT_CHECK: FAILURE");CHECK;}',
        'print("TRANSFORM_ROWS "+string(nrows(T))+" COLS "+string(ncols(T)));',
        "T;",
        "quit;",
    ]
    output.write_text("\n".join(lines) + "\n")
    metadata = {
        "branch": [ss, rr],
        "equations_before_minpoly": len(expressions),
        "generators": len(generators),
        "consistency_equations": len(consistency),
        "coefficient_model": "QQ[z,p,q,h,k,theta]/(minpoly(theta))",
        "output": output.name,
    }
    (ROOT / f"linear_reduced_{tag}.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--basis", type=Path, required=True)
    parser.add_argument("--branch", choices=["1_3", "2_5", "3_7"])
    args = parser.parse_args()
    branches = [tuple(map(int, args.branch.split("_")))] if args.branch else [(1, 3), (2, 5), (3, 7)]
    for branch in branches:
        print(emit(branch, args.basis))


if __name__ == "__main__":
    main()
