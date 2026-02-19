$timestamp = Get-Date -Format "yyyyMMdd-HHmm"
$backupFile = "C:\backups\backup-$timestamp.sql.gz.enc"
$containerName = "hms_postgres"
$dbUser = "hms_user"
$dbName = "hospital_monitoring"
$passphrase = $env:BACKUP_PASSPHRASE

if (-not $passphrase) {
    Write-Host "Error: BACKUP_PASSPHRASE environment variable is not set."
    exit 1
}

if (-not (Test-Path "C:\backups")) {
    New-Item -ItemType Directory -Force -Path "C:\backups"
}

Write-Host "Starting backup for $dbName..."
docker exec $containerName pg_dump -U $dbUser $dbName | gzip | openssl enc -aes-256-cbc -salt -pass pass:$passphrase > $backupFile

if ($?) {
    Write-Host "Backup completed successfully: $backupFile"
} else {
    Write-Host "Backup failed!"
    exit 1
}
