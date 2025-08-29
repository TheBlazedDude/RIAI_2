# Bootstrap script for Modular Offline AI App (Windows PowerShell)
# Runs training/evaluation for base modules, saves workspace selection and mappings,
# and prints readiness status. Ensure backend is running at http://localhost:8000

param(
  [int]$Seed = 1337,
  [string]$Base = "http://localhost:8000"
)

function PostJson($Path, $Obj){
  $Body = $Obj | ConvertTo-Json -Depth 6
  return Invoke-RestMethod -Method POST -Uri ($Base + $Path) -Body $Body -ContentType 'application/json'
}
function GetJson($Path){
  return Invoke-RestMethod -Method GET -Uri ($Base + $Path)
}

Write-Host "Saving pending workspace selection..."
$mods = @('chat-core','predictor-finance')
PostJson '/api/workspace' @{ selected_modules = $mods } | Out-Null

Write-Host "Training modules (seed=$Seed)..."
PostJson '/api/train' @{ module_id = 'lexicon-wordnet3'; seed = $Seed } | Out-Null
PostJson '/api/train' @{ module_id = 'chat-core'; seed = $Seed } | Out-Null
PostJson '/api/train' @{ module_id = 'predictor-finance'; seed = $Seed } | Out-Null

Write-Host "Saving model mappings..."
$module_map = @{ 'chat-core' = "chat_retrieval_$Seed"; 'predictor-finance' = "predictor_ma_$Seed" }
PostJson '/api/workspace/mappings' @{ module_map = $module_map } | Out-Null

Write-Host "Evaluating models..."
PostJson '/api/evaluate' @{ module_id = 'chat-core'; seed = $Seed; model_id = "chat_retrieval_$Seed" } | Out-Null
PostJson '/api/evaluate' @{ module_id = 'predictor-finance'; seed = $Seed; model_id = "predictor_ma_$Seed" } | Out-Null

Write-Host "Checking readiness..."
$ready = GetJson '/api/readiness'
Write-Host ("Status: {0}" -f $ready.status)
if($ready.status -ne 'ready'){
  Write-Host "Blocking items:" -ForegroundColor Yellow
  foreach($e in $ready.errors){
    Write-Host ("- {0}: {1} (Hint: {2})" -f $e.error_code, $e.human_message, $e.hint)
  }
  exit 1
} else {
  Write-Host "System is ready. Open the frontend and enter the Workspace." -ForegroundColor Green
}
