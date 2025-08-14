#!/bin/bash

# Script per eseguire test di sistema NearYou
# Verifica il rispetto di tutti i requisiti funzionali, non funzionali e di vincolo

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funzioni di utilità
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Configurazione
export PYTHONPATH="${PROJECT_ROOT}/src:${PROJECT_ROOT}/services:${PROJECT_ROOT}"
export PYTEST_CURRENT_TEST=""

# Directory dei test
TESTS_DIR="${PROJECT_ROOT}/tests"
SYSTEM_TESTS_DIR="${TESTS_DIR}/system"
REPORTS_DIR="${TESTS_DIR}/reports"

# Crea directory reports se non esiste
mkdir -p "${REPORTS_DIR}"

# Funzione per verificare prerequisiti
check_prerequisites() {
    print_header "Verifica Prerequisiti"
    
    # Verifica Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 non trovato"
        exit 1
    fi
    print_success "Python 3 trovato: $(python3 --version)"
    
    # Verifica pytest
    if ! python3 -c "import pytest" &> /dev/null; then
        print_error "pytest non installato"
        print_info "Installa con: pip install pytest"
        exit 1
    fi
    print_success "pytest disponibile"
    
    # Verifica dipendenze test
    local missing_deps=()
    for dep in requests redis psycopg2-binary clickhouse-driver; do
        if ! python3 -c "import ${dep//-/_}" &> /dev/null 2>&1; then
            missing_deps+=("$dep")
        fi
    done
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        print_warning "Dipendenze mancanti: ${missing_deps[*]}"
        print_info "I test useranno mock per le dipendenze mancanti"
    else
        print_success "Tutte le dipendenze disponibili"
    fi
    
    # Verifica struttura project
    if [ ! -f "${PROJECT_ROOT}/docker-compose.yml" ]; then
        print_error "docker-compose.yml non trovato nella root del progetto"
        exit 1
    fi
    print_success "Struttura progetto valida"
}

# Funzione per eseguire categoria di test
run_test_category() {
    local category="$1"
    local description="$2"
    local test_file="$3"
    local markers="$4"
    
    print_header "$description"
    
    local cmd="python3 -m pytest"
    local args="-v --tb=short --color=yes"
    
    # Aggiungi markers se specificati
    if [ -n "$markers" ]; then
        args="$args -m \"$markers\""
    fi
    
    # Aggiungi file specifico se fornito
    if [ -n "$test_file" ]; then
        args="$args $test_file"
    else
        args="$args ${SYSTEM_TESTS_DIR}/"
    fi
    
    # Report XML per CI/CD
    local xml_report="${REPORTS_DIR}/system_${category}.xml"
    args="$args --junitxml=$xml_report"
    
    # Report di copertura se disponibile
    if python3 -c "import coverage" &> /dev/null; then
        args="$args --cov=src --cov=services --cov-report=html:${REPORTS_DIR}/coverage_${category}"
    fi
    
    print_info "Comando: $cmd $args"
    echo
    
    if eval "$cmd $args"; then
        print_success "Test $category completati con successo"
        return 0
    else
        print_error "Test $category falliti"
        return 1
    fi
}

# Funzione per generare report riassuntivo
generate_summary_report() {
    print_header "Generazione Report Riassuntivo"
    
    local summary_file="${REPORTS_DIR}/system_tests_summary.md"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    cat > "$summary_file" << EOF
# Test di Sistema NearYou - Report Riassuntivo

**Data Esecuzione:** $timestamp  
**Progetto:** NearYou  
**Versione:** $(git describe --tags --always 2>/dev/null || echo "unknown")

## Panoramica Test

Questo report riassume l'esecuzione dei test di sistema per verificare il rispetto di tutti i requisiti del sistema NearYou.

### Categorie di Test Eseguite

1. **Requisiti Funzionali (RF1-RF7)**
   - RF1: Autenticazione e autorizzazione
   - RF2: Tracking posizione e generazione eventi  
   - RF3: Elaborazione stream e proximity detection
   - RF4: Generazione messaggi personalizzati e sistema offerte
   - RF5: Dashboard utente base
   - RF6: Storage e persistenza dati
   - RF7: Cache e ottimizzazione base

2. **Requisiti Non Funzionali (RNF1-RNF2)**
   - RNF1: Documentazione
   - RNF2: Test

3. **Requisiti di Vincolo (RV1-RV6)**
   - RV1: Tecnologici
   - RV2: Browser e compatibilità
   - RV3: Tecnologie Frontend
   - RV4: Geografici  
   - RV5: Operativi
   - RV6: Hardware

4. **Requisiti Desiderabili (RFD1-RFD4)**
   - RFD1: Ottimizzazioni frontend avanzate
   - RFD2: Monitoring e osservabilità avanzate
   - RFD3: Funzionalità utente avanzate
   - RFD4: Performance e scalabilità

## File di Test

EOF

    # Aggiungi informazioni sui file di test
    for test_file in "${SYSTEM_TESTS_DIR}"/*.py; do
        if [ -f "$test_file" ]; then
            local filename=$(basename "$test_file")
            local test_count=$(grep -c "def test_" "$test_file" 2>/dev/null || echo "0")
            echo "- \`$filename\`: $test_count test" >> "$summary_file"
        fi
    done
    
    cat >> "$summary_file" << EOF

## Risultati XML

I risultati dettagliati sono disponibili nei seguenti file XML:

EOF

    # Aggiungi link ai report XML
    for xml_file in "${REPORTS_DIR}"/system_*.xml; do
        if [ -f "$xml_file" ]; then
            local filename=$(basename "$xml_file")
            echo "- [\`$filename\`](./reports/$filename)" >> "$summary_file"
        fi
    done

    cat >> "$summary_file" << EOF

## Copertura

EOF

    # Aggiungi informazioni sulla copertura se disponibile
    if [ -d "${REPORTS_DIR}/coverage_functional" ]; then
        echo "- [Report Copertura HTML](./reports/coverage_functional/index.html)" >> "$summary_file"
    fi

    cat >> "$summary_file" << EOF

## Note

- Tutti i test utilizzano mock per le dipendenze esterne
- I test sono progettati per essere eseguiti senza richiedere servizi attivi
- Ogni test verifica specifici requisiti documentati nel Piano di Qualifica

## Comando di Esecuzione

\`\`\`bash
cd tests/system
./run_system_tests.sh all
\`\`\`

## Contatti

Per domande sui test di sistema, contattare il team di sviluppo NearYou.

EOF

    print_success "Report riassuntivo generato: $summary_file"
}

# Funzione principale
main() {
    local category="${1:-all}"
    local failed_tests=0
    local total_categories=0
    
    print_header "Test di Sistema NearYou"
    print_info "Verifica requisiti funzionali, non funzionali e di vincolo"
    print_info "Categoria: $category"
    echo
    
    # Controlla prerequisiti
    check_prerequisites
    
    case "$category" in
        "all")
            print_info "Esecuzione di tutti i test di sistema"
            
            # RF1-RF3: Requisiti funzionali base
            ((total_categories++))
            if ! run_test_category "functional" "Test Requisiti Funzionali (RF1-RF3)" \
                "${SYSTEM_TESTS_DIR}/test_requirements_functional.py" "system"; then
                ((failed_tests++))
            fi
            
            # RF4-RF7: Requisiti funzionali avanzati  
            ((total_categories++))
            if ! run_test_category "advanced" "Test Requisiti Funzionali Avanzati (RF4-RF7)" \
                "${SYSTEM_TESTS_DIR}/test_requirements_rf4_rf7.py" "system"; then
                ((failed_tests++))
            fi
            
            # RNF + RV: Requisiti non funzionali e vincolo
            ((total_categories++))
            if ! run_test_category "nonfunctional" "Test Requisiti Non Funzionali e Vincolo" \
                "${SYSTEM_TESTS_DIR}/test_requirements_nonfunctional.py" "system"; then
                ((failed_tests++))
            fi
            
            # RFD: Requisiti desiderabili
            ((total_categories++))
            if ! run_test_category "desirable" "Test Requisiti Desiderabili (RFD1-RFD4)" \
                "${SYSTEM_TESTS_DIR}/test_requirements_desirable.py" "system and desirable"; then
                ((failed_tests++))
            fi
            ;;
        
        "functional")
            ((total_categories++))
            if ! run_test_category "functional" "Test Requisiti Funzionali (RF1-RF3)" \
                "${SYSTEM_TESTS_DIR}/test_requirements_functional.py" "system"; then
                ((failed_tests++))
            fi
            ;;
        
        "advanced")
            ((total_categories++))
            if ! run_test_category "advanced" "Test Requisiti Funzionali Avanzati (RF4-RF7)" \
                "${SYSTEM_TESTS_DIR}/test_requirements_rf4_rf7.py" "system"; then
                ((failed_tests++))
            fi
            ;;
        
        "nonfunctional")
            ((total_categories++))
            if ! run_test_category "nonfunctional" "Test Requisiti Non Funzionali e Vincolo" \
                "${SYSTEM_TESTS_DIR}/test_requirements_nonfunctional.py" "system"; then
                ((failed_tests++))
            fi
            ;;
        
        "desirable")
            ((total_categories++))
            if ! run_test_category "desirable" "Test Requisiti Desiderabili" \
                "${SYSTEM_TESTS_DIR}/test_requirements_desirable.py" "system and desirable"; then
                ((failed_tests++))
            fi
            ;;
        
        "help")
            cat << EOF
Uso: $0 [categoria]

Categorie disponibili:
  all           - Esegui tutti i test di sistema (default)
  functional    - Test requisiti funzionali RF1-RF3
  advanced      - Test requisiti funzionali RF4-RF7  
  nonfunctional - Test requisiti non funzionali e vincolo
  desirable     - Test requisiti desiderabili
  help          - Mostra questo aiuto

Esempi:
  $0                    # Tutti i test
  $0 functional         # Solo RF1-RF3
  $0 desirable          # Solo requisiti desiderabili

Report vengono generati in: ${REPORTS_DIR}/
EOF
            exit 0
            ;;
        
        *)
            print_error "Categoria non valida: $category"
            print_info "Usa '$0 help' per vedere le opzioni disponibili"
            exit 1
            ;;
    esac
    
    # Genera report riassuntivo
    generate_summary_report
    
    # Summary finale
    print_header "Riassunto Esecuzione"
    
    if [ $failed_tests -eq 0 ]; then
        print_success "Tutti i test di sistema completati con successo! ($total_categories/$total_categories)"
        print_info "Il sistema rispetta tutti i requisiti verificati"
    else
        print_error "Alcuni test sono falliti ($failed_tests/$total_categories categorie)"
        print_warning "Revisiona i log sopra per dettagli sui fallimenti"
    fi
    
    print_info "Report dettagliati disponibili in: ${REPORTS_DIR}/"
    echo
    
    exit $failed_tests
}

# Esegui main con tutti gli argomenti
main "$@"
