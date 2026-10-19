param(
    [string]$Message = "Update launch_optimized.py",
    [switch]$Push = $false
)

$source = "D:\aitools\Wan2GP\launch_optimized.py"
$dest = "D:\aitools\launch_optimization_repo\launch_optimized.py"

if (Test-Path $source) {
    Copy-Item -Path $source -Destination $dest -Force
    Push-Location "D:\aitools\launch_optimization_repo"
    git add launch_optimized.py README.md
    $diff = git status --porcelain
    if ($diff) {
        git commit -m $Message
        Write-Host "Berjaya commit perubahan ke Git Repo: $Message"
    } else {
        Write-Host "Tiada perubahan dikesan pada launch_optimized.py."
    }
    if ($Push) {
        Write-Host "Menolak (Pushing) ke GitHub origin master..."
        git push origin master
    }
    Pop-Location
} else {
    Write-Error "Fail sumber tidak dijumpai: $source"
}
