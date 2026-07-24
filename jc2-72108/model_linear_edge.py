#!/usr/bin/env python3
"""Generate exact and modular Singular models for Proposition 4.3 case (2).

The lower edges are
    P_e = x A(T),  Q_e = x^2 y D(T),  T = x y^2,
with deg A = 7 and deg D = 10. Direct symbolic differentiation gives
    [P_e,Q_e] = x^2 (A D + T(2 A D' - 3 A' D)).
The target [P,Q]=x^2 therefore imposes the coefficient identity below.
"""
from __future__ import annotations
from pathlib import Path
import sympy as sp

ROOT = Path(__file__).resolve().parent
T = sp.symbols("T")
z = sp.symbols("z")
a = sp.symbols("a1:8")
Dvars = sp.symbols("d1:11")
A_full = 1 + sum(a[i-1] * T**i for i in range(1, 8))
D_full = 1 + sum(Dvars[j-1] * T**j for j in range(1, 11))
edge_identity = sp.expand(
    A_full * D_full + T * (2*A_full*sp.diff(D_full,T) - 3*sp.diff(A_full,T)*D_full) - 1
)
coeff_eqs_full = [sp.expand(edge_identity.coeff(T,k)) for k in range(1,18)]
subs_gauge = {a[6]: sp.Integer(1)}
coeff_eqs = [sp.expand(e.subs(subs_gauge)) for e in coeff_eqs_full]
coeff_eqs = [e for e in coeff_eqs if e != 0]
saturation = sp.expand(z * Dvars[9] - 1)
variables = [z, *reversed(Dvars), *reversed(a[:6])]
s = sp.symbols("s")
Arev = sp.expand(s**7 * A_full.subs(T,1/s))
Drev = sp.expand(s**10 * D_full.subs(T,1/s))
reverse_identity = sp.expand(3*sp.diff(Arev,s)*Drev - 2*Arev*sp.diff(Drev,s) - s**16)
assert sp.expand(s**16 * edge_identity.subs(T,1/s) - reverse_identity) == 0
x,y = sp.symbols("x y")
txy = x*y**2
Pe = x*A_full.subs(T,txy)
Qe = x**2*y*D_full.subs(T,txy)
bracket = sp.expand(sp.diff(Pe,x)*sp.diff(Qe,y)-sp.diff(Pe,y)*sp.diff(Qe,x))
assert sp.expand(bracket - x**2*(edge_identity.subs(T,txy)+1)) == 0

def sx(e: sp.Expr) -> str:
    return str(sp.expand(e)).replace("**","^")

def ideal_text() -> str:
    return "  " + ",\n  ".join(sx(e) for e in [*coeff_eqs, saturation]) + ";"

def emit(characteristic: int, name: str) -> Path:
    out = ROOT / name
    lines = [
        "option(redSB);",
        f"ring r={characteristic},({','.join(map(str,variables))}),dp;",
        "ideal I=", ideal_text(),
        'print("INPUT_GENERATORS "+string(size(I)));',
        "ideal G=slimgb(I);",
        'print("DIM "+string(dim(G)));',
        'print("VDIM "+string(vdim(G)));',
        'print("GB_SIZE "+string(size(G)));',
        'if(size(G)==1 && G[1]==1){print("UNIT_IDEAL [1]");}else{print("NONUNIT");G;}',
        "quit;",
    ]
    out.write_text("\n".join(lines)+"\n")
    return out

def emit_lex(characteristic: int, name: str) -> Path:
    out = ROOT / name
    lines = [
        'LIB "standard.lib";', "option(redSB);",
        f"ring r={characteristic},({','.join(map(str,variables))}),lp;",
        "ideal I=", ideal_text(),
        'print("LEX_INPUT "+string(size(I)));',
        'ideal L=stdfglm(I,"slimgb");',
        'print("LEX_DIM "+string(dim(L)));',
        'print("LEX_VDIM "+string(vdim(L)));',
        'print("LEX_SIZE "+string(size(L)));', "L;", "quit;",
    ]
    out.write_text("\n".join(lines)+"\n")
    return out

def emit_metadata() -> None:
    data = ["# Linear-edge exact model", "", f"A(T) = {A_full}", f"D(T) = {D_full}",
            f"E(T) = {edge_identity}", f"reverse identity = {reverse_identity}", "",
            "Coefficient equations before gauge:"]
    data += [f"[T^{i}] E = {e}" for i,e in enumerate(coeff_eqs_full,1)]
    data += ["", "Gauge: a7=1", f"Saturation: {saturation}"]
    (ROOT/"linear_edge_model.txt").write_text("\n".join(data)+"\n")

if __name__ == "__main__":
    emit_metadata()
    print(emit(0,"linear_edge_QQ.sing"))
    print(emit_lex(0,"linear_edge_lex_QQ.sing"))
