# usuarios_api/email_utils.py
from django.conf import settings
from django.core.mail import EmailMultiAlternatives


#def _enviar_email_html(correo: str, asunto: str, texto_plano: str, html: str) -> bool:
#    try:
#        email = EmailMultiAlternatives(
#            subject=asunto,
#            body=texto_plano,
#            from_email=settings.EMAIL_HOST_USER,
#            to=[correo],
#        )
#        email.attach_alternative(html, "text/html")
#        email.send()
#        return True
#    except Exception as e:
#        print(" Error enviando correo:", e)
#        return False
from .gmail_api import send_gmail_html

def _enviar_email_html(correo: str, asunto: str, texto_plano: str, html: str) -> bool:
    return send_gmail_html(
        to_email=correo,
        subject=asunto,
        text_body=texto_plano,
        html_body=html,
    )


def enviar_codigo_reset(correo: str, codigo: str, minutos: int = 10) -> bool:
    asunto = "🔐 Código de recuperación - Denuncias GAD Salcedo"

    texto_plano = (
        "Hola 👋\n\n"
        f"Tu código de recuperación es: {codigo}\n"
        f"Este código expira en {minutos} minutos.\n\n"
        "Si tú no solicitaste este cambio, ignora este mensaje.\n\n"
        "GAD Municipal de Salcedo"
    )

    html = f"""
    <div style="font-family: Arial, sans-serif; background:#f4f6f8; padding:30px">
      <div style="max-width:520px; margin:auto; background:white; padding:25px; border-radius:10px">
        <h2 style="color:#2C64C4; text-align:center;">GAD Municipal de Salcedo</h2>
        <p>Hola 👋</p>
        <p>Hemos recibido una solicitud para <b>recuperar tu contraseña</b>.</p>

        <p style="text-align:center; margin:30px 0;">
          <span style="font-size:28px; letter-spacing:6px; background:#2C64C4; color:white;
                       padding:12px 20px; border-radius:8px; display:inline-block;">
            {codigo}
          </span>
        </p>

        <p>⏰ Este código expira en <b>{minutos} minutos</b>.</p>
        <p style="color:#555;">Si tú no solicitaste este cambio, puedes ignorar este mensaje.</p>

        <hr style="margin:25px 0">
        <p style="font-size:12px; color:#999; text-align:center;">
          Sistema de Denuncias Públicas<br>GAD Municipal de Salcedo
        </p>
      </div>
    </div>
    """
    return _enviar_email_html(correo, asunto, texto_plano, html)


def enviar_codigo_registro(correo: str, codigo: str, minutos: int = 10) -> bool:
    asunto = " Verificación de correo - Denuncias GAD Salcedo"

    texto_plano = (
        "Hola 👋\n\n"
        f"Tu código de verificación es: {codigo}\n"
        f"Este código expira en {minutos} minutos.\n\n"
        "Si tú no estás registrándote, ignora este mensaje.\n\n"
        "GAD Municipal de Salcedo"
    )

    html = f"""
    <div style="font-family: Arial, sans-serif; background:#f4f6f8; padding:30px">
      <div style="max-width:520px; margin:auto; background:white; padding:25px; border-radius:10px">
        <h2 style="color:#2C64C4; text-align:center;">GAD Municipal de Salcedo</h2>
        <p>Hola 👋</p>
        <p>Para <b>completar tu registro</b>, confirma tu correo con este código:</p>

        <p style="text-align:center; margin:30px 0;">
          <span style="font-size:28px; letter-spacing:6px; background:#2C64C4; color:white;
                       padding:12px 20px; border-radius:8px; display:inline-block;">
            {codigo}
          </span>
        </p>

        <p>⏰ Este código expira en <b>{minutos} minutos</b>.</p>
        <p style="color:#555;">Si tú no solicitaste el registro, puedes ignorar este mensaje.</p>

        <hr style="margin:25px 0">
        <p style="font-size:12px; color:#999; text-align:center;">
          Sistema de Denuncias Públicas<br>GAD Municipal de Salcedo
        </p>
      </div>
    </div>
    """
    return _enviar_email_html(correo, asunto, texto_plano, html)
