from pathlib import Path


def get_env(var_name):
    env_path = Path(__file__).with_name(".env")
    env_data = env_path.read_text(encoding="utf-8")
    
    for line in env_data.split('\n'):
        # Usuwamy zbędne spacje z początku i końca linii
        line = line.strip()
        
        # Pomijamy puste linie oraz komentarze
        if not line or line.startswith('#'):
            continue
            
        # Sprawdzamy, czy linia zawiera znak '='
        if '=' in line:
            # Dzielimy tylko na pierwszego '=' (na wypadek, gdyby wartość też zawierała '=')
            name, value = line.split('=', 1)
            
            # Usuwamy spacje wokół nazwy i wartości
            if name.strip() == var_name:
                return value.strip()
                
    # Zwracamy pusty ciąg dopiero po przeszukaniu WSZYSTKICH linii
    return ""

