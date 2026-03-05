from django.shortcuts import render

import uuid
import random
from datetime import timedelta

from django.utils import timezone
from django.db import transaction
from django.conf import settings
from django.core.files.storage import default_storage

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from usuarios_api.email_utils import enviar_codigo_registro

import bcrypt

from db.models import Usuarios, Ciudadanos, CiudadanoDocumentos
from .models import RegistroCiudadanoBorrador

# Create your views here.
from django.contrib.auth.hashers import check_password, make_password, identify_hasher

from rest_framework_simplejwt.tokens import RefreshToken

import bcrypt

from db.models import Usuarios

from uuid import uuid4
from django.core.files.storage import default_storage
from django.utils.text import get_valid_filename
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        correo = (request.data.get("correo") or "").strip().lower()
        password = request.data.get("password") or ""

        if not correo or not password:
            return Response(
                {"detail": "correo y password son obligatorios"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = Usuarios.objects.get(correo=correo)
        except Usuarios.DoesNotExist:
            return Response({"detail": "Credenciales inválidas"}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.activo:
            return Response({"detail": "Usuario inactivo"}, status=status.HTTP_403_FORBIDDEN)

        #  Validar password con Django (soporta pbkdf2, argon2, bcrypt, etc.)
        try:
            ok = check_password(password, user.password_hash)
        except Exception:
            return Response({"detail": "Error validando credenciales"}, status=status.HTTP_400_BAD_REQUEST)

        if not ok:
            return Response({"detail": "Credenciales inválidas"}, status=status.HTTP_401_UNAUTHORIZED)

        # Generar JWT usando SimpleJWT pero con un "subject" custom
        refresh = RefreshToken()
        refresh["uid"] = str(user.id)
        refresh["tipo"] = str(user.tipo)
        refresh["correo"] = str(user.correo)

        access = refresh.access_token
        access["uid"] = str(user.id)
        access["tipo"] = str(user.tipo)
        access["correo"] = str(user.correo)

        return Response(
            {
                "access": str(access),
                "refresh": str(refresh),
                "usuario": {
                    "id": str(user.id),
                    "tipo": str(user.tipo),
                    "correo": user.correo,
                    "activo": user.activo,
                    "correo_verificado": user.correo_verificado,
                }
            },
            status=status.HTTP_200_OK
        )


def gen_codigo_6():
    return f"{random.randint(0, 999999):06d}"


class RegisterPaso1View(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        cedula = (request.data.get("cedula") or "").strip()
        nombres = (request.data.get("nombres") or "").strip()
        apellidos = (request.data.get("apellidos") or "").strip()
        telefono = (request.data.get("telefono") or "").strip() or None

        if not cedula or not nombres or not apellidos:
            return Response({"detail": "cedula, nombres, apellidos son obligatorios"}, status=400)

        # Si ya existe ciudadano con esa cédula, bloquéalo
        if Ciudadanos.objects.filter(cedula=cedula).exists():
            return Response({"detail": "Ya existe un ciudadano con esa cédula"}, status=409)

        borrador = RegistroCiudadanoBorrador.objects.create(
            cedula=cedula,
            nombres=nombres,
            apellidos=apellidos,
            telefono=telefono,
        )
        return Response({"uid": str(borrador.id), "detail": "Paso 1 guardado"}, status=201)


class RegisterEnviarCodigoView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        uid = (request.data.get("uid") or "").strip()
        correo = (request.data.get("correo") or "").strip().lower()

        if not uid or not correo:
            return Response({"detail": "uid y correo son obligatorios"}, status=400)

        try:
            borrador = RegistroCiudadanoBorrador.objects.get(id=uid)
        except RegistroCiudadanoBorrador.DoesNotExist:
            return Response({"detail": "uid inválido"}, status=404)

        # correo ya usado por otro usuario real
        if Usuarios.objects.filter(correo=correo).exists():
            return Response({"detail": "Este correo ya está registrado"}, status=409)

        # Genera OTP
        codigo = gen_codigo_6()
        borrador.correo = correo
        borrador.codigo_6 = codigo
        borrador.codigo_expira = timezone.now() + timedelta(minutes=10)
        borrador.correo_verificado = False
        borrador.save()

        #  Enviar correo real
        enviado = enviar_codigo_registro(correo=correo, codigo=codigo, minutos=10)
        if not enviado:
            return Response({"detail": "No se pudo enviar el correo, intenta nuevamente"}, status=500)

        resp = {"detail": "Código enviado", "expira_en_min": 10}

        # SOLO DEV (opcional)
        #if settings.DEBUG:
        #    resp["dev_codigo"] = codigo

        return Response(resp, status=200)


class RegisterVerificarCodigoView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        uid = (request.data.get("uid") or "").strip()
        codigo = (request.data.get("codigo") or "").strip()

        if not uid or not codigo:
            return Response({"detail": "uid y codigo son obligatorios"}, status=400)

        try:
            borrador = RegistroCiudadanoBorrador.objects.get(id=uid)
        except RegistroCiudadanoBorrador.DoesNotExist:
            return Response({"detail": "uid inválido"}, status=404)

        if not borrador.codigo_6 or not borrador.codigo_expira:
            return Response({"detail": "Primero debes solicitar un código"}, status=400)

        if timezone.now() > borrador.codigo_expira:
            return Response({"detail": "Código expirado. Solicita uno nuevo."}, status=400)

        if codigo != borrador.codigo_6:
            return Response({"detail": "Código incorrecto"}, status=400)

        borrador.correo_verificado = True
        borrador.save()

        return Response({"detail": "Correo verificado "}, status=200)


class RegisterFechaView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        uid = (request.data.get("uid") or "").strip()
        fecha = (request.data.get("fecha_nacimiento") or "").strip()  # "YYYY-MM-DD"

        if not uid or not fecha:
            return Response({"detail": "uid y fecha_nacimiento son obligatorios"}, status=400)

        try:
            borrador = RegistroCiudadanoBorrador.objects.get(id=uid)
        except RegistroCiudadanoBorrador.DoesNotExist:
            return Response({"detail": "uid inválido"}, status=404)

        try:
            borrador.fecha_nacimiento = timezone.datetime.fromisoformat(fecha).date()
        except Exception:
            return Response({"detail": "Formato inválido, usa YYYY-MM-DD"}, status=400)

        borrador.save()
        return Response({"detail": "Fecha guardada"}, status=200)


class RegisterDocumentosView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        uid = (request.data.get("uid") or "").strip()
        if not uid:
            return Response({"detail": "uid es obligatorio"}, status=400)

        try:
            borrador = RegistroCiudadanoBorrador.objects.get(id=uid)
        except RegistroCiudadanoBorrador.DoesNotExist:
            return Response({"detail": "uid inválido"}, status=404)

        frontal = request.FILES.get("cedula_frontal")
        trasera = request.FILES.get("cedula_trasera")
        if not frontal or not trasera:
            return Response(
                {"detail": "Debes enviar cedula_frontal y cedula_trasera"},
                status=400
            )

        # (opcional pero recomendado) validar que sean imágenes
        if not (frontal.content_type or "").startswith("image/"):
            return Response({"detail": "cedula_frontal debe ser imagen"}, status=400)
        if not (trasera.content_type or "").startswith("image/"):
            return Response({"detail": "cedula_trasera debe ser imagen"}, status=400)

        folder = f"registros/{uid}/"

        # nombres seguros + únicos para evitar choques
        f_name = f"{uuid4().hex}_{get_valid_filename(frontal.name)}"
        t_name = f"{uuid4().hex}_{get_valid_filename(trasera.name)}"

        frontal_path = default_storage.save(folder + f_name, frontal)
        trasera_path = default_storage.save(folder + t_name, trasera)

        # ✅ URL REAL del storage (sirve local, Cloudinary, S3, etc.)
        frontal_url = default_storage.url(frontal_path)
        trasera_url = default_storage.url(trasera_path)

        # si el storage devuelve /media/..., lo hacemos absoluto
        if frontal_url.startswith("/"):
            frontal_url = request.build_absolute_uri(frontal_url)
        if trasera_url.startswith("/"):
            trasera_url = request.build_absolute_uri(trasera_url)

        # guardas en tu borrador
        borrador.cedula_frontal_url = frontal_url
        borrador.cedula_trasera_url = trasera_url
        borrador.save()

        return Response(
            {
                "detail": "Documentos guardados",
                "url_frontal": frontal_url,
                "url_trasera": trasera_url,
            },
            status=200
        )

#class RegisterDocumentosView(APIView):
#    permission_classes = [AllowAny]
#
#    def post(self, request):
#        uid = (request.data.get("uid") or "").strip()
#
#        if not uid:
#            return Response({"detail": "uid es obligatorio"}, status=400)
#
#        try:
#            borrador = RegistroCiudadanoBorrador.objects.get(id=uid)
#        except RegistroCiudadanoBorrador.DoesNotExist:
#            return Response({"detail": "uid inválido"}, status=404)
#
#        frontal = request.FILES.get("cedula_frontal")
#        trasera = request.FILES.get("cedula_trasera")
#
#        if not frontal or not trasera:
#            return Response({"detail": "Debes enviar cedula_frontal y cedula_trasera"}, status=400)
#
#        # Guarda archivos en MEDIA (local)
#        folder = f"registros/{uid}/"
#        frontal_path = default_storage.save(folder + frontal.name, frontal)
#        trasera_path = default_storage.save(folder + trasera.name, trasera)
#
#        # URLs absolutas para Flutter
#        frontal_url = request.build_absolute_uri(settings.MEDIA_URL + frontal_path)
#        trasera_url = request.build_absolute_uri(settings.MEDIA_URL + trasera_path)
#
#        borrador.cedula_frontal_url = frontal_url
#        borrador.cedula_trasera_url = trasera_url
#        borrador.save()
#
#        return Response({"detail": "Documentos guardados", "url_frontal": frontal_url, "url_trasera": trasera_url}, status=200)


class RegisterFinalizarView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        uid = (request.data.get("uid") or "").strip()
        password = (request.data.get("password") or "").strip()

        if not uid or not password:
            return Response({"detail": "uid y password son obligatorios"}, status=400)

        if len(password) < 6:
            return Response({"detail": "Password mínimo 6 caracteres"}, status=400)

        try:
            borrador = RegistroCiudadanoBorrador.objects.get(id=uid)
        except RegistroCiudadanoBorrador.DoesNotExist:
            return Response({"detail": "uid inválido"}, status=404)

        if borrador.finalizado:
            return Response({"detail": "Este registro ya fue finalizado"}, status=400)

        # Validaciones de pasos previos
        if not borrador.correo or not borrador.correo_verificado:
            return Response({"detail": "Debes verificar el correo primero"}, status=400)

        if not borrador.fecha_nacimiento:
            return Response({"detail": "Falta fecha de nacimiento"}, status=400)

        if not borrador.cedula_frontal_url or not borrador.cedula_trasera_url:
            return Response({"detail": "Falta subir cédula frontal/trasera"}, status=400)

        # Doble validación de duplicados
        if Usuarios.objects.filter(correo=borrador.correo).exists():
            return Response({"detail": "Correo ya registrado"}, status=409)

        if Ciudadanos.objects.filter(cedula=borrador.cedula).exists():
            return Response({"detail": "Cédula ya registrada"}, status=409)

        # Hash bcrypt como en login
        #pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        pw_hash = make_password(password) #hashea todos los tipos
        now = timezone.now()

        with transaction.atomic():
            # 1) usuario
            user = Usuarios.objects.create(
                id=uuid.uuid4(),
                tipo="ciudadano",
                correo=borrador.correo,
                password_hash=pw_hash,
                activo=True,
                correo_verificado=True,
                created_at=now,
                updated_at=now,
            )

            # 2) ciudadano
            ciu = Ciudadanos.objects.create(
                usuario=user,
                cedula=borrador.cedula,
                nombres=borrador.nombres,
                apellidos=borrador.apellidos,
                telefono=borrador.telefono,
                fecha_nacimiento=borrador.fecha_nacimiento,
                created_at=now,
                updated_at=now,
            )

            # 3) documentos (tu tabla permite muchos por ciudadano; ponemos uno tipo 'cedula')
            CiudadanoDocumentos.objects.create(
                id=uuid.uuid4(),
                ciudadano=ciu,
                tipo_documento="cedula",
                url_frontal=borrador.cedula_frontal_url,
                url_trasera=borrador.cedula_trasera_url,
                created_at=now,
                updated_at=now,
            )

            borrador.finalizado = True
            borrador.save()

        return Response({"detail": "Registro completo  ", "usuario_id": str(user.id)}, status=201)
