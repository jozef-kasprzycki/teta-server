def get_env(var_name):
    env_data = open('./.env', 'r').read()
    
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

