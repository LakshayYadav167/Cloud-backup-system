// =============================================================================
// Cloud Backup System - Production Jenkins Declarative CI/CD Pipeline
// =============================================================================
// Target: Local Self-Hosted Jenkins Instance (₹0 Budget - Zero Cloud Fees)
// Enforces automated quality gates:
//   1. Environment audit (Python, Node, Docker)
//   2. Backend dependencies & isolated pytest test suite with JUnit XML
//   3. Frontend dependencies, Vitest suite with JUnit XML & Vite build
//   4. Multi-container Docker Compose configuration validation
//   5. Docker container image build (Backend & Frontend)
//   6. Opt-in Floci S3 emulator live integration testing
//   7. JUnit test report publishing and distribution artifact archiving
// =============================================================================

pipeline {
    agent any

    parameters {
        booleanParam(
            name: 'BUILD_DOCKER_IMAGES',
            defaultValue: true,
            description: 'Build local Docker container images for backend and frontend.'
        )
        booleanParam(
            name: 'RUN_INTEGRATION_TESTS',
            defaultValue: false,
            description: 'Optionally start local Floci emulator and run live S3 integration tests.'
        )
    }

    environment {
        APP_ENV           = 'ci'
        CI                = 'true'
        BACKEND_DIR       = 'backend'
        FRONTEND_DIR      = 'frontend'
        STORAGE_PROVIDER  = 'local'
    }

    options {
        timeout(time: 25, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '15', artifactNumToKeepStr: '5'))
        disableConcurrentBuilds()
    }

    stages {
        // ---------------------------------------------------------------------
        // Stage 1: Checkout Source Code
        // ---------------------------------------------------------------------
        stage('Checkout') {
            steps {
                echo 'Checking out source code from Git repository...'
                checkout scm
            }
        }

        // ---------------------------------------------------------------------
        // Stage 2: Environment Audit & Tool Verification
        // ---------------------------------------------------------------------
        stage('Environment Validation') {
            steps {
                echo 'Auditing host execution environment and tool availability...'
                script {
                    if (isUnix()) {
                        sh '''
                            set -e
                            python3 --version || python --version
                            node --version
                            npm --version
                            docker --version || true
                            docker compose version || true
                        '''
                    } else {
                        bat '''
                            python --version
                            node --version
                            npm.cmd --version
                            docker --version
                            docker compose version
                        '''
                    }
                }
            }
        }

        // ---------------------------------------------------------------------
        // Stage 3: Backend Dependencies Installation
        // ---------------------------------------------------------------------
        stage('Backend Dependencies') {
            steps {
                echo 'Installing backend dependencies from requirements.txt...'
                dir("${env.BACKEND_DIR}") {
                    script {
                        if (isUnix()) {
                            sh 'python3 -m pip install --no-cache-dir -r requirements.txt || pip install --no-cache-dir -r requirements.txt'
                        } else {
                            bat 'python -m pip install --no-cache-dir -r requirements.txt'
                        }
                    }
                }
            }
        }

        // ---------------------------------------------------------------------
        // Stage 4: Backend Unit, Security & Mocked S3 Tests
        // ---------------------------------------------------------------------
        stage('Backend Tests') {
            steps {
                echo 'Executing pytest backend suite with JUnit XML generation...'
                dir("${env.BACKEND_DIR}") {
                    script {
                        // Ensure reports directory exists
                        if (isUnix()) {
                            sh 'mkdir -p reports'
                            sh 'python3 -m pytest tests/ --junitxml=reports/backend-junit.xml -v'
                        } else {
                            bat 'if not exist reports mkdir reports'
                            bat 'python -m pytest tests/ --junitxml=reports/backend-junit.xml -v'
                        }
                    }
                }
            }
        }

        // ---------------------------------------------------------------------
        // Stage 5: Frontend Dependencies Installation
        // ---------------------------------------------------------------------
        stage('Frontend Dependencies') {
            steps {
                echo 'Installing frontend npm dependencies reproducibly from package-lock.json...'
                dir("${env.FRONTEND_DIR}") {
                    script {
                        if (isUnix()) {
                            sh 'npm ci'
                        } else {
                            bat 'npm.cmd ci'
                        }
                    }
                }
            }
        }

        // ---------------------------------------------------------------------
        // Stage 6: Frontend Unit & Component Tests
        // ---------------------------------------------------------------------
        stage('Frontend Tests') {
            steps {
                echo 'Executing Vitest dashboard component test suite...'
                dir("${env.FRONTEND_DIR}") {
                    script {
                        if (isUnix()) {
                            sh 'mkdir -p reports'
                            sh 'npx vitest run --reporter=default --reporter=junit --outputFile=reports/frontend-junit.xml'
                        } else {
                            bat 'if not exist reports mkdir reports'
                            bat 'npx.cmd vitest run --reporter=default --reporter=junit --outputFile=reports/frontend-junit.xml'
                        }
                    }
                }
            }
        }

        // ---------------------------------------------------------------------
        // Stage 7: Frontend Production Bundle Build
        // ---------------------------------------------------------------------
        stage('Frontend Build') {
            steps {
                echo 'Compiling production TypeScript & Vite distribution bundle...'
                dir("${env.FRONTEND_DIR}") {
                    script {
                        if (isUnix()) {
                            sh 'npm run build'
                            sh 'test -f dist/index.html || exit 1'
                        } else {
                            bat 'npm.cmd run build'
                            bat 'if not exist dist\\index.html exit /b 1'
                        }
                    }
                }
            }
        }

        // ---------------------------------------------------------------------
        // Stage 8: Docker Compose Configuration Validation
        // ---------------------------------------------------------------------
        stage('Docker Compose Validation') {
            steps {
                echo 'Validating Docker Compose service definitions (Local & Floci profiles)...'
                script {
                    if (isUnix()) {
                        sh 'docker compose config'
                        sh 'docker compose --profile s3 config'
                    } else {
                        bat 'docker compose config'
                        bat 'docker compose --profile s3 config'
                    }
                }
            }
        }

        // ---------------------------------------------------------------------
        // Stage 9: Container Image Build (Local Docker Daemon)
        // ---------------------------------------------------------------------
        stage('Container Image Build') {
            when {
                expression { return params.BUILD_DOCKER_IMAGES == null ? true : params.BUILD_DOCKER_IMAGES }
            }
            steps {
                echo 'Building multi-stage Docker container images locally...'
                script {
                    if (isUnix()) {
                        sh 'docker build -t cloud-backup-backend:ci -f docker/Dockerfile.backend backend'
                        sh 'docker build -t cloud-backup-frontend:ci -f docker/Dockerfile.frontend frontend'
                    } else {
                        bat 'docker build -t cloud-backup-backend:ci -f docker/Dockerfile.backend backend'
                        bat 'docker build -t cloud-backup-frontend:ci -f docker/Dockerfile.frontend frontend'
                    }
                }
            }
        }

        // ---------------------------------------------------------------------
        // Stage 10: Floci S3 Live Integration Tests (Opt-In Parameter)
        // ---------------------------------------------------------------------
        stage('Floci Integration Tests') {
            when {
                expression { return params.RUN_INTEGRATION_TESTS == null ? false : params.RUN_INTEGRATION_TESTS }
            }
            steps {
                echo 'Spinning up Floci emulator container and executing live S3 integration tests...'
                script {
                    try {
                        if (isUnix()) {
                            sh 'docker compose --profile s3 up -d floci'
                        } else {
                            bat 'docker compose --profile s3 up -d floci'
                        }
                        dir("${env.BACKEND_DIR}") {
                            if (isUnix()) {
                                sh 'python3 -m pytest tests/test_floci_integration.py -v'
                            } else {
                                bat 'python -m pytest tests/test_floci_integration.py -v'
                            }
                        }
                    } finally {
                        // Safe stoppage: stop container, preserve persistent volumes
                        echo 'Stopping Floci container (preserving persistent data volumes)...'
                        if (isUnix()) {
                            sh 'docker compose stop floci'
                        } else {
                            bat 'docker compose stop floci'
                        }
                    }
                }
            }
        }
    }

    // -------------------------------------------------------------------------
    // Post Actions: Test Reporting, Artifact Archiving & Workspace Cleanup
    // -------------------------------------------------------------------------
    post {
        always {
            echo 'Collecting test execution metrics and publishing reports...'
            // Publish JUnit XML test results from backend and frontend suites
            junit testResults: '**/reports/*-junit.xml', allowEmptyResults: true

            // Archive production build bundle and test reports
            archiveArtifacts artifacts: '**/reports/*-junit.xml, frontend/dist/**', allowEmptyArchive: true

            echo 'Cleaning ephemeral workspace (preserving named Docker volumes)...'
            cleanWs deleteDirs: true, notFailBuild: true
        }
        success {
            echo '================================================================='
            echo ' [SUCCESS] Cloud Backup System CI/CD Quality Gates Passed!      '
            echo ' 100% Free & Open-Source Verified · ₹0 Budget Maintained        '
            echo '================================================================='
        }
        failure {
            echo '================================================================='
            echo ' [FAILURE] Quality Gate Violated. Inspect stage logs above.      '
            echo '================================================================='
        }
    }
}
