#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
destino="${1:-${repo_dir}/data/zzu_pecg}"
descargas="${destino}/downloads"
mkdir -p "${descargas}"

nombres=(
  ECGCode.csv DiseaseCode.csv AttributesDictionary.csv ExampleReadingCode.ipynb
  Child_ecg.z01 Child_ecg.zip
)
urls=(
  https://ndownloader.figshare.com/files/53512538
  https://ndownloader.figshare.com/files/53512544
  https://ndownloader.figshare.com/files/53580632
  https://ndownloader.figshare.com/files/53581268
  https://ndownloader.figshare.com/files/53524583
  https://ndownloader.figshare.com/files/53523902
)
md5s=(
  7612c5af0e01e052eb85792c5e362f12
  0bff597c23397c0d05a937fe09807ad4
  ffbbb7ebd8ad4425b3a859739eb65eb1
  66694258f55ea75bf3454546d486a0e5
  4782e8c17b478745853db85210ce46aa
  d7bb207d0f559c5f697bd7e442975718
)

for i in "${!nombres[@]}"; do
  archivo="${descargas}/${nombres[$i]}"
  if [[ ! -f "${archivo}" ]] || [[ "$(md5sum "${archivo}" | awk '{print $1}')" != "${md5s[$i]}" ]]; then
    curl --fail --location --retry 5 --retry-delay 3 --continue-at - \
      --output "${archivo}" "${urls[$i]}"
  fi
  echo "${md5s[$i]}  ${archivo}" | md5sum --check --status
  echo "OK ${nombres[$i]}"
done

if [[ ! -d "${destino}/Child_ecg" ]]; then
  7z x "${descargas}/Child_ecg.zip" "-o${destino}" -y
fi

n_hea="$(find "${destino}/Child_ecg" -type f -name '*.hea' | wc -l)"
n_dat="$(find "${destino}/Child_ecg" -type f -name '*.dat' | wc -l)"
if [[ "${n_hea}" != 14190 || "${n_dat}" != 14190 ]]; then
  echo "ZZU FALLA: hea=${n_hea}, dat=${n_dat}, esperados 14190/14190" >&2
  exit 1
fi
echo "ZZU VERDE: ${n_hea} cabeceras, ${n_dat} señales"
