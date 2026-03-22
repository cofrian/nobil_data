# Setup Git repository for NOBIL data ingestion

$projectPath = "c:\Users\team\Downloads\nobil-postgres-historico-supabase\nobil-postgres-historico-supabase"
Set-Location $projectPath

Write-Host "1. Checking Git installation..."
git --version

Write-Host "`n2. Initializing Git repository..."
git init

Write-Host "`n3. Configuring Git user (if not already set)..."
git config --global user.email "nobil-sync@local" 2>$null
git config --global user.name "NOBIL Sync" 2>$null

Write-Host "`n4. Creating .gitignore..."
@"
.env
.venv/
venv/
logs/
*.pyc
__pycache__/
*.egg-info/
.pytest_cache/
*.log
".gitignore.temp
Get-Content ".gitignore.temp" | Out-File ".gitignore" -Encoding UTF8
Remove-Item ".gitignore.temp"

Write-Host "`n5. Checking out main branch..."
git checkout -B main

Write-Host "`n6. Adding remote GitHub repository..."
git remote add origin https://github.com/cofrian/nobil_data.git 2>$null || git remote set-url origin https://github.com/cofrian/nobil_data.git

Write-Host "`n7. Staging data files..."
git add data/ src/ requirements.txt schema.sql README.md nobil-postgres-historico.service 2>$null

Write-Host "`n8. Creating initial commit..."
git commit -m "Initial NOBIL real-time ingestion data and code" 2>$null || Write-Host "Already committed"

Write-Host "`n9. Setting up push..."
git push -u origin main 2>$null || Write-Host "Push requires authentication - next steps will handle this"

Write-Host "`n✅ Git repository initialized successfully!"
Write-Host "Repository location: $projectPath"
git config --get remote.origin.url
