import React from 'react'

export default function MetricsCharts({ capability, modelId }: { capability?: string, modelId?: string }){
  return (
    <div style={{border:'1px dashed #d1d5db', borderRadius:12, padding:12}}>
      <strong>Metrics Charts</strong>
      <div style={{fontSize:12, color:'#374151', marginTop:4}}>
        Placeholder charts for latency p50/p95 and task metrics.
      </div>
      <div style={{marginTop:8, fontSize:12}}>capability: {capability || 'n/a'} | model: {modelId || 'n/a'}</div>
      <div style={{height:160, background:'#f9fafb', borderRadius:8, marginTop:8, display:'flex', alignItems:'center', justifyContent:'center', color:'#9ca3af'}}>
        Chart Area
      </div>
      <div style={{marginTop:8, display:'flex', gap:8}}>
        <button>Export chart</button>
        <button>Export latest report JSON</button>
      </div>
    </div>
  )
}
