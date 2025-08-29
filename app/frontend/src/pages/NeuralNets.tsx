import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

export default function NeuralNets(){
  const [items, setItems] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [nnId, setNnId] = useState('')
  const [nnName, setNnName] = useState('')
  const [nnFamily, setNnFamily] = useState('')
  // Extended NNSpec fields
  const [task, setTask] = useState('dialogue')
  const [inShape, setInShape] = useState('') // e.g., 1,128 or 224,224,3
  const [inDtype, setInDtype] = useState('float32')
  const [outUnits, setOutUnits] = useState('')
  const [outActivation, setOutActivation] = useState('softmax')
  const [initScheme, setInitScheme] = useState('xavier')
  const [initSeed, setInitSeed] = useState('1337')
  const [specText, setSpecText] = useState('') // optional JSON blob
  const [saving, setSaving] = useState(false)
  const navigate = useNavigate()

  async function load(){
    setLoading(true)
    setError(null)
    try{
      const res = await fetch('/api/registry/neural_nets')
      if(!res.ok) throw new Error('Failed to load neural nets')
      const data = await res.json()
      setItems(data.neural_nets || [])
    }catch(e:any){
      setError(String(e))
    }finally{
      setLoading(false)
    }
  }

  useEffect(()=>{ load() },[])

  function parseShape(s: string){
    const t = (s||'').trim()
    if(!t) return undefined
    try{
      // accept comma-delimited or JSON array
      if(t.startsWith('[')){
        const arr = JSON.parse(t)
        if(Array.isArray(arr)) return arr.map((x:any)=> Number(x))
      }
      return t.split(',').map(x=> Number(x.trim())).filter(x=> !Number.isNaN(x))
    }catch{ return undefined }
  }

  function parseSpec(s: string){
    const t = (s||'').trim()
    if(!t) return undefined
    try{ return JSON.parse(t) }catch{ return undefined }
  }

  async function create(){
    if(!nnId.trim()){
      alert('Please provide an NN id (alphanumeric/underscore).')
      return
    }
    const input = {
      shape: parseShape(inShape),
      dtype: inDtype || undefined,
    } as any
    if(!input.shape) delete (input as any).shape

    const output = {
      units: outUnits ? Number(outUnits) : undefined,
      activation: outActivation || undefined,
    } as any

    const init = {
      scheme: initScheme || undefined,
      seed: initSeed ? Number(initSeed) : undefined,
    } as any

    const spec = parseSpec(specText)

    const payload: any = {
      id: nnId.trim(),
      name: nnName.trim() || nnId.trim(),
      family: nnFamily || undefined,
      task: task || undefined,
      input: (input.shape || input.dtype) ? input : undefined,
      output: (output.units || output.activation) ? output : undefined,
      init: (init.scheme || typeof init.seed === 'number') ? init : undefined,
      spec: spec,
    }

    try{
      setSaving(true)
      const res = await fetch('/api/registry/neural_nets', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      if(!res.ok) throw new Error('Failed to create NN')
      setNnId(''); setNnName(''); setNnFamily('');
      setTask('dialogue'); setInShape(''); setInDtype('float32'); setOutUnits(''); setOutActivation('softmax');
      setInitScheme('xavier'); setInitSeed('1337'); setSpecText('')
      await load()
    }catch(e:any){
      alert(String(e))
    }finally{
      setSaving(false)
    }
  }

  if(loading) return <div>Loading neural nets…</div>
  if(error) return (
    <div style={{color:'red'}}>
      <div>Error: {error}</div>
      <div style={{marginTop:8}}><button onClick={load}>Retry</button></div>
    </div>
  )

  return (
    <div>
      <h2>Neural Networks</h2>
      <p style={{fontSize:12, color:'#6b7280'}}>Create and manage NNs. You can then create or map models to these NNs in the next step.</p>

      <div style={{border:'1px solid #e5e7eb', borderRadius:12, padding:12, marginBottom:16}}>
        <strong>New Neural Network</strong>
        <div style={{display:'grid', gridTemplateColumns:'1fr 1fr 1fr auto', gap:8, marginTop:8, alignItems:'center'}}>
          <input placeholder="id (e.g., my_transformer)" value={nnId} onChange={e=> setNnId(e.target.value)}
                 style={{padding:8, border:'1px solid #e5e7eb', borderRadius:8}}/>
          <input placeholder="name" value={nnName} onChange={e=> setNnName(e.target.value)}
                 style={{padding:8, border:'1px solid #e5e7eb', borderRadius:8}}/>
          <input placeholder="family (optional)" value={nnFamily} onChange={e=> setNnFamily(e.target.value)}
                 style={{padding:8, border:'1px solid #e5e7eb', borderRadius:8}}/>
          <button onClick={create} disabled={saving}>{saving? 'Creating…':'Create'}</button>
        </div>
        <div style={{display:'grid', gridTemplateColumns:'1fr 1fr 1fr 1fr', gap:8, marginTop:8}}>
          <input placeholder="task (e.g., dialogue|vision|forecast)" value={task} onChange={e=> setTask(e.target.value)}
                 style={{padding:8, border:'1px solid #e5e7eb', borderRadius:8}}/>
          <input placeholder="input shape (e.g., 1,128 or [224,224,3])" value={inShape} onChange={e=> setInShape(e.target.value)}
                 style={{padding:8, border:'1px solid #e5e7eb', borderRadius:8}}/>
          <input placeholder="input dtype (e.g., float32)" value={inDtype} onChange={e=> setInDtype(e.target.value)}
                 style={{padding:8, border:'1px solid #e5e7eb', borderRadius:8}}/>
          <input placeholder="output units (e.g., 3)" value={outUnits} onChange={e=> setOutUnits(e.target.value)}
                 style={{padding:8, border:'1px solid #e5e7eb', borderRadius:8}}/>
        </div>
        <div style={{display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:8, marginTop:8}}>
          <input placeholder="output activation (e.g., softmax|linear)" value={outActivation} onChange={e=> setOutActivation(e.target.value)}
                 style={{padding:8, border:'1px solid #e5e7eb', borderRadius:8}}/>
          <input placeholder="init scheme (xavier|kaiming|normal)" value={initScheme} onChange={e=> setInitScheme(e.target.value)}
                 style={{padding:8, border:'1px solid #e5e7eb', borderRadius:8}}/>
          <input placeholder="init seed (e.g., 1337)" value={initSeed} onChange={e=> setInitSeed(e.target.value)}
                 style={{padding:8, border:'1px solid #e5e7eb', borderRadius:8}}/>
        </div>
        <div style={{marginTop:8}}>
          <textarea placeholder="optional: full spec JSON (advanced)" value={specText} onChange={e=> setSpecText(e.target.value)}
                    rows={4} style={{width:'100%', padding:8, border:'1px solid #e5e7eb', borderRadius:8}}/>
        </div>
      </div>

      <div style={{display:'grid', gap:8}}>
        {items.length === 0 ? (
          <div style={{fontSize:12, color:'#6b7280'}}>No neural nets yet. Create one above.</div>
        ) : items.map(nn => (
          <div key={nn.id} style={{border:'1px solid #e5e7eb', borderRadius:12, padding:12, display:'flex', justifyContent:'space-between'}}>
            <div>
              <strong>{nn.name || nn.id}</strong>
              <div style={{fontSize:12, color:'#374151'}}>id: {nn.id}{nn.family? ` • family: ${nn.family}`:''}{nn.task? ` • task: ${nn.task}`:''}</div>
              {(nn.input || nn.output) && (
                <div style={{fontSize:12, color:'#6b7280', marginTop:4}}>
                  {nn.input? `in: ${Array.isArray(nn.input?.shape)? '['+nn.input.shape.join(',')+']':''} ${nn.input?.dtype||''}`:''}
                  {nn.output? ` • out: ${nn.output?.units??''} ${nn.output?.activation||''}`:''}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      <div style={{display:'flex', justifyContent:'flex-end', gap:12, marginTop:16}}>
        <button onClick={load} disabled={loading}>{loading? 'Saving…':'Save'}</button>
        <button onClick={()=> navigate('/models')}>Save & Continue → Models</button>
      </div>
    </div>
  )
}
