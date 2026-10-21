#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "${1:?Where checkout required}" && pwd)"
out="$(pwd)/dist"
objects="$(pwd)/build/obj"
mkdir -p "$out" "$objects"

cd "$repo"
# HARDISP.F is originally a command-line PROGRAM. Where's patch turns it into
# a callable SUBROUTINE. The DEHANT patch adjusts call sites to match the
# iau_CAL2JD and iau_DAT symbols in the downloaded helper sources.
patch -p0 --batch --forward -i external/iers/HARDISP.patch
patch -p0 --batch --forward -i external/iers/dehanttideinel.patch

src="$repo/external/iers/src_2010"
mapfile -d '' files < <(find "$src" -type f -name '*.F' -print0 | sort -z)
if (( ${#files[@]} < 40 )); then
  echo "Expected at least 40 Fortran source files, found ${#files[@]}" >&2
  exit 1
fi

for file in "${files[@]}"; do
  relative="${file#"$src"/}"
  name="${relative//\//_}"
  name="${name%.F}.o"
  gfortran -O2 -std=legacy -fallow-argument-mismatch \
    -ffixed-line-length-none -c "$file" -o "$objects/$name"
done

gfortran -shared -Wl,--export-all-symbols \
  -Wl,"--out-implib,$out/libiers2010.dll.a" \
  -o "$out/iers2010.dll" "$objects"/*.o

# Include the data file read by GPT2.F and the MinGW runtime DLLs.
cp "$src/gpt2_5.grd" "$out/"
for runtime in libgfortran-5.dll libgcc_s_seh-1.dll libquadmath-0.dll libwinpthread-1.dll; do
  if [[ -f "/mingw64/bin/$runtime" ]]; then
    cp "/mingw64/bin/$runtime" "$out/"
  fi
done

nm -g --defined-only "$out/iers2010.dll" | grep -qiE ' [Tt] _?apg_$'
echo "Built $out/iers2010.dll"
