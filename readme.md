# NearYou - Piattaforma di Advertising Geolocalizzato

[![CI/CD](https://github.com/AlphaCodeSWE/NearYou/actions/workflows/ci.yml/badge.svg)](https://github.com/AlphaCodeSWE/NearYou/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/AlphaCodeSWE/NearYou/branch/main/graph/badge.svg)](https://codecov.io/gh/AlphaCodeSWE/NearYou)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

> Piattaforma innovativa per l'advertising personalizzato basato sulla posizione in tempo reale

![NearYou Architecture](docs/images/architecture-overview.png)

## 🎯 Panoramica

NearYou è una piattaforma di advertising geo-localizzato che fornisce messaggi promozionali personalizzati agli utenti basandosi sulla loro vicinanza ai negozi e sulle loro preferenze personali.

### ✨ Caratteristiche Principali

- 🚀 **Streaming in tempo reale** dei dati GPS tramite Apache Kafka
- 🤖 **Messaggi personalizzati** generati da LLM (Language Model)
- 🗺️ **Dashboard interattiva** con mappa real-time
- 📊 **Analytics avanzate** con ClickHouse e Grafana
- 🔐 **Autenticazione sicura** con JWT
- 🚲 **Routing ottimizzato** per ciclisti con OSRM
- 📱 **Responsive UI** per tutti i dispositivi

## 🏗️ Architettura

Il sistema è costruito seguendo un'architettura a microservizi:
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   GPS Sensors   │──>│  Kafka Streaming │──>│    Consumer     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
│
▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Apps     │<──│  Message Gen LLM │<──│   ClickHouse    │
└─────────────────┘    └──────────────────┘    └─────────────────┘

### 🔧 Stack Tecnologico

- **Backend**: FastAPI, Python 3.10+
- **Streaming**: Apache Kafka con SSL/TLS
- **Database**: ClickHouse (eventi), PostgreSQL/PostGIS (dati geospaziali)
- **Cache**: Redis
- **LLM**: OpenAI GPT / Groq
- **Monitoring**: Grafana, Prometheus
- **Container**: Docker, Docker Compose
- **CI/CD**: GitHub Actions
- **Orchestrazione**: Airflow

## 🚀 Quick Start

### Prerequisiti

- Docker & Docker Compose
- Python 3.10+
- Make
- Git

### Installazione Locale

1. **Clona il repository**
   ```bash
   git clone https://github.com/AlphaCodeSWE/NearYou.git
   cd NearYou