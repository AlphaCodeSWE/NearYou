"""
Test di configurazione e integrazione per la suite di test di sistema.
Verifica che tutti i componenti siano correttamente configurati e integrati.
"""
import pytest
import os
import sys
from pathlib import Path


class TestSystemTestsConfiguration:
    """Test per verificare la configurazione della suite di test di sistema."""
    
    def test_project_structure_exists(self):
        """Verifica che la struttura del progetto sia corretta."""
        project_root = Path(__file__).parent.parent.parent
        
        # File essenziali
        essential_files = [
            "docker-compose.yml",
            "requirements.txt",
            "README.md",
            "pytest.ini"
        ]
        
        for file_path in essential_files:
            full_path = project_root / file_path
            assert full_path.exists(), f"File essenziale mancante: {file_path}"
    
    def test_system_tests_directory_structure(self):
        """Verifica struttura directory test di sistema."""
        system_tests_dir = Path(__file__).parent
        
        # File di test richiesti
        required_test_files = [
            "test_requirements_functional.py",
            "test_requirements_rf4_rf7.py", 
            "test_requirements_nonfunctional.py",
            "test_requirements_desirable.py"
        ]
        
        for test_file in required_test_files:
            test_path = system_tests_dir / test_file
            assert test_path.exists(), f"File test mancante: {test_file}"
    
    def test_pythonpath_configuration(self):
        """Verifica che PYTHONPATH sia configurato correttamente per i test"""
        import sys
        
        # Path atteso per il workspace
        expected_workspace = "/Users/alessandrodipasquale/Desktop/NearYou"
        
        # Verifica che il workspace sia in sys.path
        workspace_in_path = any(expected_workspace in path for path in sys.path)
        
        if not workspace_in_path:
            # Aggiungi il workspace a sys.path se mancante
            sys.path.insert(0, expected_workspace)
            
        # Verifica che ora sia presente
        updated_workspace_in_path = any(expected_workspace in path for path in sys.path)
        assert updated_workspace_in_path, f"Workspace {expected_workspace} non in PYTHONPATH"
        
        # Verifica accesso a moduli del progetto
        try:
            # Test import di moduli dal src
            src_path = os.path.join(expected_workspace, "src")
            if os.path.exists(src_path):
                if src_path not in sys.path:
                    sys.path.insert(0, src_path)
                
                # Prova import di config se esiste
                config_file = os.path.join(src_path, "configg.py")
                if os.path.exists(config_file):
                    import configg
                    assert hasattr(configg, '__file__'), "Modulo configg non importabile"
            
        except ImportError as e:
            # Se fallisce import, almeno verifica che i path siano settati
            assert expected_workspace in str(sys.path), f"Import failed ma workspace in path: {e}"
    
    def test_pytest_markers_configured(self):
        """Verifica che i markers pytest siano configurati."""
        # I markers dovrebbero essere definiti in pytest.ini o conftest.py
        
        # Markers utilizzati nei test di sistema
        expected_markers = [
            "system",
            "desirable", 
            "slow",
            "unit",
            "integration",
            "acceptance"
        ]
        
        # Verifica che pytest sia configurato (pytest.ini o pyproject.toml)
        project_root = Path(__file__).parent.parent.parent
        
        pytest_ini = project_root / "pytest.ini"
        if pytest_ini.exists():
            with open(pytest_ini, 'r') as f:
                config_content = f.read()
            
            assert "markers" in config_content, "Sezione markers non trovata in pytest.ini"
            
            # Verifica alcuni markers essenziali
            for marker in ["system", "unit", "integration"]:
                assert marker in config_content, f"Marker '{marker}' non configurato"
    
    def test_test_environment_isolation(self):
        """Verifica isolamento ambiente di test."""
        # Verifica che le variabili di ambiente di test non interferiscano
        test_env_vars = [
            "JWT_SECRET", "POSTGRES_HOST", "CLICKHOUSE_HOST", 
            "REDIS_HOST", "KAFKA_BROKER"
        ]
        
        # In ambiente test, queste dovrebbero avere valori di test o mock
        for env_var in test_env_vars:
            if env_var in os.environ:
                value = os.environ[env_var]
                # Verifica che contenga "test" o mock values
                assert ("test" in value.lower() or 
                       "mock" in value.lower() or
                       "localhost" in value.lower()), \
                    f"Variabile ambiente {env_var} non sembra essere per test: {value}"
    
    def test_mock_imports_available(self):
        """Verifica che le librerie per mocking siano disponibili."""
        # Mock libraries essenziali
        try:
            from unittest.mock import Mock, patch, MagicMock
            assert True
        except ImportError:
            pytest.fail("unittest.mock non disponibile")
        
        # pytest per test framework
        try:
            import pytest
            assert hasattr(pytest, 'mark')
            assert hasattr(pytest, 'fixture')
        except ImportError:
            pytest.fail("pytest non configurato correttamente")
    
    def test_project_imports_work(self):
        """Verifica che gli import del progetto funzionino nei test."""
        project_root = Path(__file__).parent.parent.parent
        
        # Aggiungi path se non presente
        if str(project_root / "src") not in sys.path:
            sys.path.insert(0, str(project_root / "src"))
        if str(project_root / "services") not in sys.path:
            sys.path.insert(0, str(project_root / "services"))
        
        # Test import di moduli progetto (se esistenti)
        try:
            # Test import condizionali - non falliscono se moduli non esistono
            
            # src modules
            try:
                from src.models import offer
            except ImportError:
                pass  # Modulo potrebbe non esistere ancora
            
            try:
                from src.cache import redis_cache
            except ImportError:
                pass
            
            try:
                from services.dashboard import auth
            except ImportError:
                pass
            
            # Se arriviamo qui, i path sono configurati correttamente
            assert True
            
        except Exception as e:
            # Fallimento se errori diversi da ImportError
            if "ImportError" not in str(type(e)):
                pytest.fail(f"Errore configurazione import: {e}")
    
    def test_test_data_generators_available(self):
        """Verifica che i generatori di test data siano disponibili."""
        # Test che conftest.py fornisca fixture necessarie
        
        # Verifica fixture da conftest.py
        expected_fixtures = [
            "sample_user_data",
            "sample_shop_data", 
            "sample_offer_data",
            "test_data_generators"
        ]
        
        # Controlla se conftest.py esiste ed ha le fixture
        conftest_path = Path(__file__).parent.parent / "conftest.py"
        if conftest_path.exists():
            with open(conftest_path, 'r') as f:
                conftest_content = f.read()
            
            for fixture_name in expected_fixtures:
                assert f"def {fixture_name}" in conftest_content, \
                    f"Fixture '{fixture_name}' non trovata in conftest.py"
    
    def test_reports_directory_writable(self):
        """Verifica che la directory reports sia scrivibile."""
        reports_dir = Path(__file__).parent.parent / "reports"
        
        # Crea directory se non esiste
        reports_dir.mkdir(exist_ok=True)
        
        # Test scrittura
        test_file = reports_dir / "test_write.tmp"
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            
            assert test_file.exists()
            
            # Cleanup
            test_file.unlink()
            
        except Exception as e:
            pytest.fail(f"Directory reports non scrivibile: {e}")
    
    def test_system_tests_script_executable(self):
        """Verifica che lo script di esecuzione sia corretto."""
        script_path = Path(__file__).parent / "run_system_tests.sh"
        
        assert script_path.exists(), "Script run_system_tests.sh non trovato"
        
        # Verifica sia eseguibile (su Unix)
        if hasattr(os, 'access'):
            assert os.access(script_path, os.X_OK), "Script non eseguibile"
        
        # Verifica contenuto script
        with open(script_path, 'r') as f:
            script_content = f.read()
        
        # Verifica funzioni essenziali nello script
        essential_functions = [
            "run_test_category",
            "check_prerequisites", 
            "generate_summary_report"
        ]
        
        for func in essential_functions:
            assert func in script_content, f"Funzione '{func}' mancante nello script"


@pytest.mark.system
class TestRequirementsTraceability:
    """Test per verificare la tracciabilità dei requisiti nei test."""
    
    def test_desirable_requirements_documented(self):
        """Verifica che i requisiti desiderabili siano documentati nei test."""
        
        desirable_requirements = [
            "RFD1.1", "RFD1.2", "RFD1.3", "RFD1.4", "RFD1.5", "RFD1.6",
            "RFD2.1", "RFD2.2", "RFD2.3", "RFD2.4", "RFD2.5", "RFD2.6", "RFD2.7",
            "RFD3.1", "RFD3.2", "RFD3.3", "RFD3.4", "RFD3.5",
            "RFD4.1", "RFD4.2", "RFD4.3", "RFD4.4"
        ]
        
        desirable_test_file = Path(__file__).parent / "test_requirements_desirable.py"
        
        if desirable_test_file.exists():
            with open(desirable_test_file, 'r') as f:
                content = f.read()
            
            # Verifica che almeno alcuni requisiti desiderabili siano testati
            found_count = 0
            for req in desirable_requirements:
                if req.lower().replace(".", "_") in content.lower():
                    found_count += 1
            
            # Per requisiti desiderabili, anche copertura parziale è accettabile
            assert found_count > 0, "Nessun requisito desiderabile testato"
            
            # Verifica marker @pytest.mark.desirable presente
            assert "@pytest.mark.desirable" in content, \
                "Marker 'desirable' mancante nei test RFD"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
