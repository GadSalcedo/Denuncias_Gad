import os
import logging
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings

logger = logging.getLogger(__name__)

_initialized = False


def init_firebase():
    global _initialized

    if _initialized:
        return

    path = str(getattr(settings, "FIREBASE_SERVICE_ACCOUNT_PATH", "")).strip()
    logger.info(f"[FCM] Intentando inicializar con: {path}")

    if not path or not os.path.exists(path) or not os.path.isfile(path):
        logger.warning(f"[FCM] Archivo de credenciales no válido o no encontrado en: {path}. Push deshabilitado.")
        # No marcamos _initialized = True para permitir reintento si el archivo aparece,
        # aunque en Django esto requeriría reinicio usualmente. 
        # Pero lo más importante es que send_push detecte que no hubo éxito.
        return

    try:
        if not firebase_admin._apps:
            import json
            with open(path, 'r', encoding='utf-8') as f:
                info = json.load(f)
            
            # Limpiar posibles escapes mal interpretados en la clave privada
            if 'private_key' in info and isinstance(info['private_key'], str):
                info['private_key'] = info['private_key'].replace('\\n', '\n')
            
            cred = credentials.Certificate(info)
            firebase_admin.initialize_app(cred)
            logger.info("[FCM] Inicializado correctamente")
        _initialized = True
    except Exception as e:
        logger.exception(f"[FCM] Error inicializando Firebase: {e}")


def send_push(tokens: list[str], title: str, body: str, data: dict | None = None) -> int:
    if not tokens:
        return 0

    init_firebase()

    # Verificamos si realmente hay una app inicializada
    if not _initialized or not firebase_admin._apps:
        logger.warning("[FCM] Firebase no inicializado. Push omitido.")
        return 0

    messages = [
        messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=token,
        )
        for token in tokens
    ]

    try:
        response = messaging.send_each(messages)

        bad_tokens = []

        for resp, token in zip(response.responses, tokens):
            if not resp.success:
                error_msg = str(resp.exception).lower()
                logger.warning(f"[FCM] Error token {token}: {resp.exception}")

                # Tokens inválidos o no registrados
                if any(err in error_msg for err in [
                    "requested entity was not found",
                    "unregistered",
                    "not found",
                    "invalid registration token"
                ]):
                    bad_tokens.append(token)

        # 🔥 Eliminación automática de tokens inválidos
        if bad_tokens:
            from notificaciones.models import DeviceToken  # Ajusta si es necesario
            deleted_count, _ = DeviceToken.objects.filter(
                fcm_token__in=bad_tokens
            ).delete()

            logger.info(f"[FCM] Tokens inválidos eliminados: {deleted_count}")

        return response.success_count

    except Exception as e:
        logger.exception(f"[FCM] Error enviando push: {e}")
        return 0
