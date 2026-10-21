"""Compare a Windows IERS2010 DLL with reference cases embedded in IERS .F files.

The same script can also exercise a locally built macOS/Linux shared library.
It calls the raw GNU Fortran ABI directly, with all subroutine arguments passed
by reference. The values and tolerances are recorded alongside each case.
"""

from __future__ import annotations

import ctypes as C
from pathlib import Path
import os
import sys


D = C.c_double
I = C.c_int32


def floats(*values: float):
    return [D(value) for value in values]


def check(name: str, actual, expected, tolerance: float) -> None:
    actual = tuple(actual)
    expected = tuple(expected)
    if len(actual) != len(expected):
        raise AssertionError(f"{name}: output length {len(actual)} != {len(expected)}")
    errors = tuple(abs(got - want) for got, want in zip(actual, expected))
    if any(error > tolerance for error in errors):
        raise AssertionError(
            f"{name}: got {actual}, expected {expected}, "
            f"max error {max(errors):.9g} > {tolerance:.9g}"
        )
    print(f"PASS {name}: max error {max(errors):.3g}")


def subroutine(dll, name: str, inputs, output_count: int):
    values = floats(*inputs) + floats(*([0.0] * output_count))
    fn = getattr(dll, name.lower() + "_")
    fn.argtypes = [C.POINTER(D)] * len(values)
    fn.restype = None
    fn(*(C.byref(value) for value in values))
    return tuple(value.value for value in values[-output_count:])


def main(path: Path) -> None:
    path = path.resolve()
    dll = C.CDLL(str(path))
    cases = 0
    failures = []

    def verify(name: str, actual, expected, tolerance: float):
        nonlocal cases
        try:
            check(name, actual, expected, tolerance)
        except AssertionError as exc:
            failures.append(str(exc))
            print(f"FAIL {exc}")
        cases += 1

    # APG.F
    verify(
        "APG.F",
        subroutine(dll, "apg", [0.6274877539940092, 2.454994088489240,
                                0.2617993877991494, 0.8726646259971648], 3),
        [-0.9677190006296187757e-4, -0.1042668498001996791,
         0.4662515377110782594e-1], 1e-11,
    )

    # FUNDARG.F
    verify(
        "FUNDARG.F",
        subroutine(dll, "fundarg", [0.07995893223819302], 5),
        [2.291187512612069099, 6.212931111003726414, 3.658025792050572989,
         4.554139562402433228, -0.5167379217231804489], 1e-11,
    )

    # RG_ZONT2.F
    verify(
        "RG_ZONT2.F",
        subroutine(dll, "rg_zont2", [0.07995893223819302], 3),
        [7.983287678576557467e-2, 5.035331113978199288e-5,
         -4.249711616463017e-14], 1e-12,
    )

    # ORTHO_EOP.F
    time = D(47100.0)
    eop = (D * 3)()
    dll.ortho_eop_(C.byref(time), eop)
    verify("ORTHO_EOP.F", eop,
           [-162.8386373279636530, 117.7907525842668974,
            -23.39092370609808214], 1e-9)

    # PMSDNUT2.F
    rmjd = D(54335.0)
    pm = (D * 2)()
    dll.pmsdnut2_(C.byref(rmjd), pm)
    verify("PMSDNUT2.F", pm,
           [24.83144238273364834, -14.09240692041837661], 1e-9)

    # UTLIBR.F: both examples in the source.
    verify("UTLIBR.F case 1", subroutine(dll, "utlibr", [44239.1], 2),
           [2.441143834386761746, -14.78971247349449492], 1e-9)
    verify("UTLIBR.F case 2", subroutine(dll, "utlibr", [55227.4], 2),
           [-2.655705844335680244, 27.39445826599846967], 1e-9)

    # GCONV2.F uses its built-in GRS80 ellipsoid constants.
    verify("GCONV2.F",
           subroutine(dll, "gconv2", [0.0, 0.0, 4075579.496,
                                        931853.192, 4801569.002], 3),
           [0.857728298603, 0.224779294628, 665.9207], 1e-4)

    # GPT.F and GMF.F.
    verify("GPT.F",
           subroutine(dll, "gpt", [55055.0, 0.6708665767,
                                     -1.393397187, 812.546], 3),
           [918.0710638757363995, 19.31914181012882992,
            -42.19185643717770517], 1e-9)
    verify("GMF.F",
           subroutine(dll, "gmf", [55055.0, 0.6708665767,
                                     -1.393397187, 844.715, 1.278564131], 2),
           [3.425245519339138678, 3.449589116182419257], 1e-11)

    # FCUL_A.F and FCUL_B.F are functions returning a double, not subroutines.
    for name, args, expected in (
        ("FCUL_A.F", [30.67166667, 2075.0, 300.15, 15.0],
         3.800243667312344087),
        ("FCUL_B.F", [30.67166667, 2075.0, 224.0, 15.0],
         3.800758725284345996),
    ):
        fn = getattr(dll, name[:-2].lower() + "_")
        fn.argtypes = [C.POINTER(D)] * 4
        fn.restype = D
        values = floats(*args)
        verify(name, [fn(*(C.byref(value) for value in values))], [expected], 1e-11)

    # FCUL_ZD_HPA.F exports FCULZD_HPA (without the underscore after FCUL).
    # Its header says ELLIP_HT=2010.344, but the published expected values
    # match ELLIP_HT=2003.344 exactly. The latter is used for this reference
    # comparison; the discrepancy is documented in the test report.
    verify("FCUL_ZD_HPA.F (height 2003.344)",
           subroutine(dll, "fculzd_hpa", [30.67166667, 2003.344,
                                           798.4188, 14.322, 0.532], 3),
           [1.935225924846803114, 1.932992176591644462,
            0.2233748255158703871e-2], 1e-11)

    verify("VMF1.F",
           subroutine(dll, "vmf1", [0.00127683, 0.00060955,
                                      55055.0, 0.6708665767, 1.278564131], 2),
           [3.424342122738070593, 3.448299714692572238], 1e-11)
    verify("VMF1_HT.F",
           subroutine(dll, "vmf1_ht", [0.00127683, 0.00060955,
                                         55055.0, 0.6708665767,
                                         824.17, 1.278564131], 2),
           [3.425088087972572470, 3.448299714692572238], 1e-11)

    # DEHANTTIDEINEL.F: station, Sun and Moon positions; UTC date.
    tide_cases = [
        (
            [4075578.385, 931852.890, 4801570.154],
            [137859926952.015, 54228127881.4350, 23509422341.6960],
            [-179996231.920342, -312468450.131567, -169288918.592160],
            [2009, 4, 13],
            [0.7700420357108125891e-1, 0.6304056321824967613e-1,
             0.5516568152597246810e-1],
        ),
        (
            [1112189.660, -4842955.026, 3985352.284],
            [-54537460436.2357, 130244288385.279, 56463429031.5996],
            [300396716.912, 243238281.451, 120548075.939],
            [2012, 7, 13],
            [-0.2036831479592075833e-1, 0.5658254776225972449e-1,
             -0.7597679676871742227e-1],
        ),
        (
            [1112200.5696, -4842957.8511, 3985345.9122],
            [100210282451.6279, 103055630398.3160, 56855096480.4475],
            [369817604.4348, 1897917.5258, 120804980.8284],
            [2015, 7, 15],
            [0.00509570869172363845, 0.0828663025983528700,
             -0.0636634925404189617],
        ),
    ]
    for index, (station, sun, moon, date, expected) in enumerate(tide_cases, 1):
        xsta = (D * 3)(*station)
        xsun = (D * 3)(*sun)
        xmon = (D * 3)(*moon)
        year, month, day = (I(value) for value in date)
        hour = D(0)
        result = (D * 3)()
        dll.dehanttideinel_(xsta, C.byref(year), C.byref(month),
                            C.byref(day), C.byref(hour), xsun, xmon, result)
        verify(f"DEHANTTIDEINEL.F case {index}", result, expected, 1e-10)

    # The fourth header example has a Sun position about one order of
    # magnitude too close and repeats case 3's expected displacement. A
    # standalone Fortran driver confirms the large mismatch; retain the
    # observation without treating this inconsistent source example as a
    # DLL regression.
    xsta = (D * 3)(1112152.8166, -4842857.5435, 3985496.1783)
    xsun = (D * 3)(8382471154.1312895, 10512408445.356153,
                   -5360583240.3763866)
    xmon = (D * 3)(380934092.93550891, 2871428.1904491195,
                   79015680.553570181)
    year, month, day, hour = I(2017), I(1), I(15), D(0)
    result = (D * 3)()
    dll.dehanttideinel_(xsta, C.byref(year), C.byref(month),
                        C.byref(day), C.byref(hour), xsun, xmon, result)
    print("SOURCE DISCREPANCY DEHANTTIDEINEL.F case 4: "
          f"computed {tuple(result)}, header repeats case 3's expected values")

    # GPT2.F reads gpt2_5.grd from the process working directory. Its source
    # rounds expected outputs, so compare at half of the displayed precision.
    old_cwd = Path.cwd()
    try:
        os.chdir(path.parent)
        for time_flag, expected in (
            (0, [1002.56, 22.12, -6.53, 15.63, 0.0012647,
                 0.0005726, 44.06]),
            (1, [1003.49, 11.95, -5.47, 9.58, 0.0012395,
                 0.0005560, 44.06]),
        ):
            dmjd = D(56141.0)
            latitude = (D * 1)(48.20 * 3.141592653589793 / 180.0)
            longitude = (D * 1)(16.37 * 3.141592653589793 / 180.0)
            height = (D * 1)(156.0)
            nstat = I(1)
            it = I(time_flag)
            outputs = [(D * 1)() for _ in range(7)]
            dll.gpt2_(C.byref(dmjd), latitude, longitude, height,
                      C.byref(nstat), C.byref(it), *outputs)
            actual = [output[0] for output in outputs]
            # The published values have 2 to 7 decimal places.
            for column, (got, want) in enumerate(zip(actual, expected)):
                tolerance = 0.005 if column in (0, 1, 2, 3, 6) else 0.00000005
                verify(f"GPT2.F case {time_flag}, output {column + 1}",
                       [got], [want], tolerance)
    finally:
        os.chdir(old_cwd)

    print(f"{cases - len(failures)}/{cases} reference comparisons passed for {path.name}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
