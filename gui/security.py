from werkzeug.security import generate_password_hash, check_password_hash

def hash_password(password):
    """Genera un hash seguro para una contraseña."""
    return generate_password_hash(password, method='pbkdf2:sha256')

def check_password(p_hash, password):
    """Verifica si una contraseña coincide con su hash."""
    return check_password_hash(p_hash, password)
