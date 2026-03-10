"""
Shared authentication utilities for multiturn chat application.
Provides centralized user verification with role information.
"""
from passlib.context import CryptContext
from psycopg_pool import ConnectionPool

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def verify_user_and_get_role(username: str, password: str, pool: ConnectionPool):
    """
    Verifies user credentials and retrieves role information.

    Returns:
        tuple: (is_valid: bool, user_data: dict or None)

        user_data contains:
        - username: str
        - org: int
        - user_id: str
        - isadmin: bool
    """
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT password_hash, org, user_id, COALESCE(isadmin, FALSE) as isadmin
                FROM multiturn_chat.users
                WHERE username = %s
            """, (username,))
            result = cur.fetchone()

            if not result:
                return False, None

            password_hash, org, user_id, isadmin = result

            if not pwd_context.verify(password, password_hash):
                return False, None

            return True, {
                'username': username,
                'org': org,
                'user_id': user_id or username,
                'isadmin': isadmin
            }
