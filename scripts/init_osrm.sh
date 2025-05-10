#!/bin/bash
set -e

DATA_DIR=/data
PBF_FILE="${DATA_DIR}/milano.osm.pbf"
MIN_SIZE=10000000

# Crea directory se non esiste
mkdir -p "${DATA_DIR}"

# Scarica il file PBF se necessario
if [ ! -f "${PBF_FILE}" ] || [ $(stat -c%s "${PBF_FILE}") -lt "${MIN_SIZE}" ]; then
    echo "Scarico PBF di Milano da ${PBF_URL}..."
    curl -sSL "${PBF_URL}" -o "${PBF_FILE}"
    echo "Download completato"
fi

# Preprocess OSRM
echo "Inizio preprocess OSRM..."
osrm-extract -p /opt/profiles/bicycle.lua "${PBF_FILE}"
osrm-partition "${DATA_DIR}/milano.osrm"
osrm-customize "${DATA_DIR}/milano.osrm"

# Avvia OSRM
echo "Avvio OSRM routing service..."
exec osrm-routed --algorithm mld --port 5000 "${DATA_DIR}/milano.osrm"