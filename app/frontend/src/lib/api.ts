const API_BASE = (import.meta as any)?.env?.VITE_API_BASE ? String((import.meta as any).env.VITE_API_BASE).replace(/\/$/, '') : ''

export async function getModules(){
  // Try configured base (or relative) first
  const primaryUrl = `${API_BASE}/api/modules`
  try{
    let res = await fetch(primaryUrl)
    if(res.ok) return res.json()
    // Fallback: direct to localhost backend (helps when proxy/base misconfigured)
    const fbUrl = 'http://localhost:8000/api/modules'
    res = await fetch(fbUrl)
    if(res.ok) return res.json()
    const text = await res.text().catch(()=> '')
    throw new Error(`Failed to load modules (status ${res.status}) ${text ? '- '+text : ''}`)
  }catch(err){
    // Surface network error clearly
    throw new Error('Failed to load modules: '+ String(err))
  }
}

export async function getReadiness(){
  const res = await fetch('/api/readiness')
  if(!res.ok) throw new Error('Failed to load readiness')
  return res.json()
}

export async function getWorkspace(){
  const res = await fetch('/api/workspace')
  if(!res.ok) throw new Error('Failed to load workspace')
  return res.json()
}

export async function saveWorkspace(selected_modules: string[], name?: string, seed?: number){
  const payload: any = { selected_modules }
  if(name !== undefined) payload.name = name
  if(typeof seed === 'number') payload.seed = seed
  const res = await fetch('/api/workspace', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  if(!res.ok) throw new Error('Failed to save workspace')
  return res.json()
}

// Registry: models
export async function listModels(){
  const res = await fetch('/api/registry/models')
  if(!res.ok) throw new Error('Failed to load models')
  return res.json()
}

// Workspace mappings
export async function getMappings(){
  const res = await fetch('/api/workspace/mappings')
  if(!res.ok) throw new Error('Failed to load mappings')
  return res.json()
}
export async function saveMappings(mappings: { module_map?: Record<string,string>, capability_map?: Record<string,string> }){
  const res = await fetch('/api/workspace/mappings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(mappings)
  })
  if(!res.ok) throw new Error('Failed to save mappings')
  return res.json()
}

// Guardrails
export async function getGuardrails(){
  const res = await fetch('/api/guardrails')
  if(!res.ok) throw new Error('Failed to load guardrails')
  return res.json()
}
export async function setGuardrails(payload: any){
  const res = await fetch('/api/guardrails', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  if(!res.ok) throw new Error('Failed to set guardrails')
  return res.json()
}

// Metrics
export async function latestMetrics(capability: string, model_id?: string){
  const qp = new URLSearchParams()
  if(model_id) qp.set('model_id', model_id)
  qp.set('capability', capability)
  const res = await fetch(`/api/metrics/latest?${qp.toString()}`)
  if(!res.ok) throw new Error('Failed to load latest metrics')
  return res.json()
}

// Jobs
export async function trainJob(module_id: string, seed: number, nn_id?: string){
  const payload: any = { module_id, seed }
  if(nn_id) payload.nn_id = nn_id
  const res = await fetch('/api/train', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  if(!res.ok) throw new Error('Train job failed')
  return res.json()
}
export async function evaluateJob(module_id: string, seed: number, model_id?: string){
  const res = await fetch('/api/evaluate', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ module_id, seed, model_id })
  })
  if(!res.ok) throw new Error('Evaluate job failed')
  return res.json()
}

// Runtime
export async function runtimePost(payload: any){
  const res = await fetch('/api/runtime/post', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  if(!res.ok) throw new Error('Runtime post failed')
  return res.json()
}

export async function listDatasets(){
  const res = await fetch('/api/datasets')
  if(!res.ok) throw new Error('Failed to list datasets')
  return res.json()
}

export async function ingestDataset(payload: { id?: string, name?: string, format: 'jsonl'|'text'|'csv', content: string, capability?: string, tags?: string[] }){
  const res = await fetch('/api/datasets/ingest', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  if(!res.ok) throw new Error('Failed to ingest dataset')
  return res.json()
}

export async function listNeuralNets(){
  const res = await fetch('/api/registry/neural_nets')
  if(!res.ok) throw new Error('Failed to load neural nets')
  return res.json()
}
