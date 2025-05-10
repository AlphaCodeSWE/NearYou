#!/bin/bash
# Script per generare certificati SSL di sviluppo

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${CYAN}Generazione certificati SSL per ambiente di sviluppo...${NC}"

# Crea directory certs se non esiste
mkdir -p certs
cd certs

# Genera CA key
if [ ! -f ca.key ]; then
    openssl genrsa -out ca.key 2048
    echo -e "${GREEN}✓ CA key generata${NC}"
fi

# Genera CA certificate
if [ ! -f ca.crt ]; then
    openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 \
        -out ca.crt \
        -subj "/C=IT/ST=Development/L=Milano/O=NearYou/OU=Dev/CN=NearYou-Dev-CA"
    echo -e "${GREEN}✓ CA certificate generato${NC}"
fi

# Genera client key
if [ ! -f client_key.pem ]; then
    openssl genrsa -out client_key.pem 2048
    echo -e "${GREEN}✓ Client key generata${NC}"
fi

# Genera client CSR
if [ ! -f client.csr ]; then
    openssl req -new -key client_key.pem -out client.csr \
        -subj "/C=IT/ST=Development/L=Milano/O=NearYou/OU=Dev/CN=client-dev"
    echo -e "${GREEN}✓ Client CSR generato${NC}"
fi

# Firma client certificate
if [ ! -f client_cert.pem ]; then
    openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key \
        -CAcreateserial -out client_cert.pem -days 365 -sha256
    echo -e "${GREEN}✓ Client certificate firmato${NC}"
fi

# Genera Kafka keystore e truststore
if [ ! -f kafka.keystore.jks ]; then
    # Genera keystore password
    STORE_PASS="developmentpass123"
    
    # Crea keystore
    keytool -genkey -noprompt \
        -alias kafka-dev \
        -dname "CN=kafka, OU=Dev, O=NearYou, L=Milano, ST=Development, C=IT" \
        -keystore kafka.keystore.jks \
        -storepass "$STORE_PASS" \
        -keypass "$STORE_PASS" \
        -keyalg RSA \
        -validity 365
    
    # Importa CA nel keystore
    keytool -import -noprompt \
        -alias ca-root \
        -file ca.crt \
        -keystore kafka.keystore.jks \
        -storepass "$STORE_PASS"
    
    echo -e "${GREEN}✓ Kafka keystore generato${NC}"
fi

if [ ! -f kafka.truststore.jks ]; then
    # Crea truststore
    keytool -import -noprompt \
        -alias ca-root \
        -file ca.crt \
        -keystore kafka.truststore.jks \
        -storepass "$STORE_PASS"
    
    echo -e "${GREEN}✓ Kafka truststore generato${NC}"
fi

cd ..
echo -e "${GREEN}✓ Tutti i certificati di sviluppo sono stati generati${NC}"