import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getModules, getWorkspace, listModels, getMappings, saveMappings, listNeuralNets, trainJob, evaluateJob, getReadiness } from '../lib/api'

function isCompatible(mod: any, model: any){
  const caps: string[] = mod?.capabilities || []
  if(!caps.includes(model?.capability)) return false
  if((mod?.task||'') !== (model?.task||'')) return false
  return true
}

export default function ModelLauncherOps(){
  const [modules, setModules] = useState<any[]>([])
  const [ws, setWs] = useState<any>(null)
  const [models, setModels] = useState<any[]>([])
  const [mapState, setMapState] = useState<Record<string,string>>({})
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState<Record<string, boolean>>({})
  const [nns, setNns] = useState<any[]>([])
  const [nnSel, setNnSel] = useState<Record<string,string>>({}) // moduleId -> nn_id
  const [preparing, setPreparing] = useState<boolean>(false)
  const [prepNote, setPrepNote] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(()=>{
    Promise.all([getModules(), getWorkspace(), listModels(), getMappings(), listNeuralNets()])
      .then(([mods, ws, mdl, maps, nnres])=>{
        setModules(mods.modules||[])
        setWs(ws)
        setModels(mdl.models||[])
        setMapState(maps?.module_map || {})
        setNns((nnres?.neural_nets)||[])
      })
      .catch(e=> setMessage('Load failed: '+String(e)))
      .finally(()=> setLoading(false))
  },[])

  const selectedModules = useMemo(()=>{
    const ids: string[] = ws?.selected_modules || []
    const map = new Map(modules.map(m=>[m.id, m]))
    return ids.map(id => map.get(id)).filter(Boolean)
  }, [ws, modules])

  function setMapped(moduleId: string, modelId: string){
    setMapState(prev => ({...prev, [moduleId]: modelId}))
  }

  async function onCreateFromNN(moduleId: string){
    try{
      const nn_id = nnSel[moduleId]
      if(!nn_id){ setMessage('Select a Neural Network first.'); return }
      setBusy(b=> ({...b, [moduleId]: true}))
      const res = await trainJob(moduleId, ws?.seed ?? 1337, nn_id)
      const trainedId = res?.job?.result?.model_id
      // Refresh models
      const mdl = await listModels()
      setModels(mdl.models||[])
      if(trainedId){ setMapped(moduleId, trainedId); setMessage(`Created model ${trainedId} from NN ${nn_id}.`) }
    }catch(e:any){
      setMessage('Create Model from NN failed: '+String(e))
    }finally{
      setBusy(b=> ({...b, [moduleId]: false}))
    }
  }

  async function onSave(){
    try{
      setMessage(null)
      await saveMappings({ module_map: mapState })
      setMessage('Mappings saved.')
    }catch(e:any){
      setMessage('Failed to save mappings: '+String(e))
    }
  }

  function sleep(ms: number){ return new Promise(res=> setTimeout(res, ms)) }

  async function prepareAndContinue(){
    try{
      setPreparing(true)
      setPrepNote('Preparing models (training if needed)…')

      const seed = ws?.seed ?? 1337
      // Ensure each selected module has a mapped model; if not, train to create one
      const newMap: Record<string,string> = { ...mapState }
      for(const mod of selectedModules){
        const moduleId = mod.id
        let modelId = newMap[moduleId]
        if(!modelId){
          setPrepNote(`Training ${moduleId} to create a model…`)
          try{
            const res = await trainJob(moduleId, seed)
            const trainedId = res?.job?.result?.model_id
            if(trainedId){ newMap[moduleId] = trainedId; modelId = trainedId }
          }catch(e){ /* ignore, proceed */ }
        }else{
          // Even if already mapped, run a short training to warm up artifacts
          setPrepNote(`Training ${moduleId}…`)
          try{ await trainJob(moduleId, seed) }catch(e){ /* ignore */ }
        }
      }

      // Save (possibly updated) mappings
      setPrepNote('Saving mappings…')
      try{ await saveMappings({ module_map: newMap }); setMapState(newMap) }catch(e){ /* ignore */ }

      // Evaluate each mapped module to produce fresh metrics
      for(const mod of selectedModules){
        const moduleId = mod.id
        const modelId = newMap[moduleId]
        if(modelId){
          setPrepNote(`Evaluating ${moduleId}…`)
          try{ await evaluateJob(moduleId, seed, modelId) }catch(e){ /* ignore */ }
        }
      }

      // Poll readiness up to ~10 seconds
      setPrepNote('Finalizing readiness…')
      const start = Date.now()
      let ready = false
      while(Date.now() - start < 10000){
        try{
          const r = await getReadiness()
          if(r?.status === 'ready'){ ready = true; break }
        }catch(e){ /* ignore */ }
        await sleep(800)
      }
      if(!ready){ setMessage('Warning: Readiness not fully green yet; proceeding. You can re-check on the Workspace page.') }
      navigate('/workspace')
    }finally{
      setPreparing(false)
      setPrepNote(null)
    }
  }


  if(loading) return <div>Loading…</div>

  return (
    <div>
      <h2>Model Selection</h2>
      <div style={{fontSize:12, color:'#6b7280', marginBottom:12}}>Use the workspace seed shown in the header. Map exactly one compatible model per selected module.</div>
      <div style={{display:'grid', gap:12}}>
        {selectedModules.map((m: any)=>{
          const compat = (models||[]).filter(md => isCompatible(m, md))
          const sel = mapState[m.id] || ''
          const ready = !!sel
          return (
            <div key={m.id} style={{border:'1px solid #e5e7eb', borderRadius:12, padding:12}}>
              <div style={{display:'flex', justifyContent:'space-between'}}>
                <div>
                  <strong>{m.name || m.id}</strong>
                  <div style={{fontSize:12, color:'#374151'}}>Task: {m.task}</div>
                </div>
                <div>
                  <span style={{padding:'4px 8px', borderRadius:8, background: ready? '#ecfdf5':'#fef3c7', color: ready? '#065f46':'#92400e'}}>
                    {ready? 'Mapped' : 'Not mapped'}
                  </span>
                </div>
              </div>
              <div style={{display:'flex', gap:12, alignItems:'center', marginTop:8}}>
                <label>Model</label>
                <select value={sel} onChange={e=> setMapped(m.id, e.target.value)}>
                  <option value="">-- choose compatible model --</option>
                  {compat.map(md => (
                    <option key={md.id} value={md.id}>{md.name || md.id}</option>
                  ))}
                </select>
              </div>
              <div style={{display:'flex', gap:12, alignItems:'center', marginTop:8}}>
                <label>Create from NN</label>
                <select value={nnSel[m.id] || ''} onChange={e=> setNnSel(prev=> ({...prev, [m.id]: e.target.value}))}>
                  <option value="">-- select NN --</option>
                  {nns.map(nn => (
                    <option key={nn.id} value={nn.id}>{nn.name || nn.id}</option>
                  ))}
                </select>
                <button onClick={()=> onCreateFromNN(m.id)} disabled={!!busy[m.id]}>{busy[m.id]? 'Creating…':'Create Model from NN'}</button>
              </div>
            </div>
          )
        })}
      </div>
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', gap:12, marginTop:12}}>
        <div style={{fontSize:12, color:'#374151'}}>
          {preparing ? (<>Preparing: {prepNote || '…'}</>) : null}
        </div>
        <div style={{display:'flex', gap:12}}>
          <button onClick={onSave} disabled={preparing}>Save</button>
          <button onClick={prepareAndContinue} disabled={preparing || selectedModules.length===0}>
            {preparing ? `Preparing…` : 'Save, Train & Continue → Workspace'}
          </button>
        </div>
      </div>
      {message && <div style={{marginTop:8, fontSize:12}}>{message}</div>}
    </div>
  )
}
