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
    def backupTag = "${CONTAINER}:backup-${timestamp}"
    def backupFolder = "/respaldos_docker/${target.name}/${APP_NAME}"
    def tarFile = "${CONTAINER}-${timestamp}.tar"
    def tarPath = "${backupFolder}/${tarFile}"

    echo "🚀 Iniciando despliegue en ${target.host}..."

    // Crear directorio remoto si no existe
    sshCommand remote: remote, command: "mkdir -p ${remotePath}"

    // Sincronizar archivos necesarios
    // 1. Enviamos el código fuente comprimido (método compatible con el script Java del usuario)
    sh "tar -czf project.tar.gz --exclude='.git' --exclude='__pycache__' --exclude='media' --exclude='static' --ignore-failed-read ."
    sshPut remote: remote, from: "project.tar.gz", into: "${remotePath}/project.tar.gz"
    sshCommand remote: remote, command: "cd ${remotePath} && tar -xzf project.tar.gz && rm project.tar.gz"

    // 2. Enviamos Dockerfile y docker-compose explicitamente (asegurando integridad)
    sshPut remote: remote, from: "Dockerfile", into: "${remotePath}/Dockerfile"
    sshPut remote: remote, from: "docker-compose.yml", into: "${remotePath}/docker-compose.yml"
    sshPut remote: remote, from: "entrypoint.sh", into: "${remotePath}/entrypoint.sh"

    sshCommand remote: remote, command: """
        set -e

        echo '🧹 Limpiando imágenes huérfanas y temporales para liberar espacio...'
        docker image prune -f || true
        rm -f /tmp/${CONTAINER}-*.tar

        echo '🧹 Verificando y eliminando respaldos antiguos (más de 2 días)...'
        if [ -d "${backupFolder}" ]; then
            find ${backupFolder} -name "${CONTAINER}-*.tar" -type f -mtime +2 -print -delete
        fi

        # Respaldar la imagen actual antes de reconstruir
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

    // Levantar con docker-compose usando build (estilo del script Java adaptado a docker-compose)
    sshCommand remote: remote, command: """
        cd ${remotePath}
        docker compose up -d --build
    """

    // Limpieza final
    sshCommand remote: remote, command: """
        echo '🔄 Eliminando imágenes huérfanas...'
        docker image prune -f
    """

    echo "✅ Despliegue completado en ${target.host}"
}
