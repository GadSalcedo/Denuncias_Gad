// Despliegue automatizado de aplicación Django (Denuncias Gad) en servidores remotos usando Jenkins.
def targets = [:]

pipeline {
    agent any

    // No se necesita JDK para Django, pero puedes definir python si es necesario para tareas locales de CI
    // tools {
    //     python 'Python3'
    // }

    options {
        buildDiscarder logRotator(artifactDaysToKeepStr: '', artifactNumToKeepStr: '5', daysToKeepStr: '', numToKeepStr: '5')
        disableConcurrentBuilds()
    }

    environment {
        APP_NAME = 'denuncias-gad'
        CONTAINER = 'denuncias-gad-web' // Nombre del servicio en docker-compose
        REMOTE_BASE_PATH = '/apis_docker/denuncias-gad'
    }

    stages {
        stage('Cargar configuración de despliegue') {
            steps {
                // Se espera un JSON en Jenkins Credentials con la info de hosts (dev, testing, prod)
                withCredentials([string(credentialsId: 'deployment-config', variable: 'DEPLOY_CONFIG_JSON')]) {
                    script {
                        def raw = new groovy.json.JsonSlurper().parseText(DEPLOY_CONFIG_JSON)
                        targets = raw.collectEntries { k, v -> [(k): v as HashMap] } as HashMap
                    }
                }
            }
        }

        stage('Verificar rama válida') {
            when {
                not {
                    anyOf {
                        branch 'development'
                        branch 'preproduction'
                        branch 'main'
                    }
                }
            }
            steps {
                echo "🔀 La rama '${env.BRANCH_NAME}' no está habilitada para despliegue. Terminando ejecución."
                script {
                    currentBuild.result = 'NOT_BUILT'
                    error("Despliegue no permitido desde esta rama.")
                }
            }
        }

        // En Python/Django no solemos "compilar" un JAR, pero podríamos correr tests o linting aquí.
        // stage('Tests & Linting') {
        //     steps {
        //         sh 'pip install -r requirements.txt'
        //         sh 'python manage.py test'
        //     }
        // }

        stage('Desplegar en DEV') {
            when {
                branch 'development'
            }
            steps {
                script {
                    deployTo(targets.dev)
                }
            }
        }

        stage('Desplegar en TESTING') {
            when {
                branch 'preproduction'
            }
            steps {
                script {
                    deployTo(targets.testing)
                }
            }
        }

        stage('Desplegar en PROD') {
            when {
                branch 'main'
            }
            steps {
                script {
                    deployTo(targets.prod)
                }
            }
        }
    }

    post {
        success {
            echo "🎉 Despliegue exitoso para rama '${env.BRANCH_NAME}'"
        }
        failure {
            echo "❌ Falló el despliegue en rama '${env.BRANCH_NAME}'"
        }
    }
}

def deployTo(target) {
    def remote = [
        name: target.host,
        host: target.host,
        port: target.port,
        allowAnyHosts: true
    ]

    withCredentials([usernamePassword(credentialsId: target.credentialsId, usernameVariable: 'USR', passwordVariable: 'PSW')]) {
        remote.user = USR
        remote.password = PSW
    }

    def remotePath = "${REMOTE_BASE_PATH}"
    def timestamp = new Date().format("yyyyMMdd-HHmmss")
    def backupTag = "${APP_NAME}:backup-${timestamp}"
    def backupFolder = "/respaldos_docker/${target.name}/${APP_NAME}"
    def tarFile = "${APP_NAME}-${timestamp}.tar"
    def tarPath = "${backupFolder}/${tarFile}"

    echo "🚀 Iniciando despliegue en ${target.host}..."

    // Crear directorio remoto si no existe
    sshCommand remote: remote, command: "mkdir -p ${remotePath}"

    // SOLUCIÓN SEGURA Y ROBUSTA: Construcción local y transferencia de imagen (Docker Save/Load)
    // Esto garantiza que lo que se probó en Jenkins sea EXACTAMENTE lo que corre en el servidor.
    
    sh "docker build -t ${APP_NAME}:latest ."
    sh "docker save ${APP_NAME}:latest | gzip > ${APP_NAME}.tar.gz"
    
    echo "📦 Transfiriendo imagen comprimida al servidor..."
    sshPut remote: remote, from: "${APP_NAME}.tar.gz", into: "/tmp/${APP_NAME}.tar.gz"
    
    echo "📥 Cargando imagen en el servidor remoto..."
    sshCommand remote: remote, command: """
        gunzip -c /tmp/${APP_NAME}.tar.gz | docker load
        rm /tmp/${APP_NAME}.tar.gz
    """

    // Sincronizar archivos de configuración y archivos necesarios para ejecución
    // Solo enviamos lo necesario para ejecutar, el código fuente ya está en la imagen Docker.
    // Incluimos .env si es necesario, o asegúrate de que esté en el servidor.
    sh "tar -czf config.tar.gz docker-compose.yml entrypoint.sh"
    sshPut remote: remote, from: "config.tar.gz", into: "${remotePath}/config.tar.gz"
    sshCommand remote: remote, command: "cd ${remotePath} && tar -xzf config.tar.gz && rm config.tar.gz"

    // IMPORTANTE: Asegúrate de que el archivo .env exista en el servidor remoto en ${remotePath}/.env 
    // o cárgalo aquí si es seguro hacerlo (aunque se recomienda manejar secretos vía Jenkins Credentials).

    sshCommand remote: remote, command: """
        set -e

        echo '🧹 Limpiando imágenes huérfanas y temporales para liberar espacio...'
        docker image prune -f || true
        rm -f /tmp/${APP_NAME}-*.tar

        echo '🧹 Verificando y eliminando respaldos antiguos (más de 2 días)...'
        if [ -d "${backupFolder}" ]; then
            find ${backupFolder} -name "${APP_NAME}-*.tar" -type f -mtime +2 -print -delete
        fi

        # Intentar respaldar la imagen 'web' actual (asumiendo que tiene el tag del APP_NAME o similar)
        if docker image inspect ${APP_NAME}_web:latest >/dev/null 2>&1; then
            echo '🔄 Respaldando imagen actual como ${backupTag}...'
            docker tag ${APP_NAME}_web:latest ${backupTag}

            echo '📂 Verificando carpeta destino en respaldos...'
            mkdir -p ${backupFolder}

            echo '📦 Exportando imagen ${backupTag}...'
            docker save -o ${tarPath} ${backupTag}

            latest_id=\$(docker images --no-trunc --quiet ${APP_NAME}_web:latest)
            backup_id=\$(docker images --no-trunc --quiet ${backupTag})

            if [ \"\$latest_id\" = \"\$backup_id\" ]; then
                docker rmi ${backupTag}
            else
                docker rmi -f ${backupTag} || true
            fi
        else
            echo '❌ No hay imagen actual para respaldar.'
        fi
    """

    // Levantar el stack completo (incluye db) para asegurar que las dependencias se cumplan
    sshCommand remote: remote, command: """
        cd ${remotePath}
        docker compose up -d
    """

    // Limpieza final
    sshCommand remote: remote, command: """
        echo '🔄 Eliminando imágenes huérfanas...'
        docker image prune -f
    """

    echo "✅ Despliegue completado en ${target.host}"
}
