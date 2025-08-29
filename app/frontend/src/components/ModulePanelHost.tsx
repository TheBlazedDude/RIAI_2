import React from 'react'

// Renders placeholder runtime panels declared by modules via ui_panels
export default function ModulePanelHost({ modules }: { modules: Array<any> }){
  const items: Array<{key:string, title:string, description:string}> = []
  modules.forEach(m => {
    (m.ui_panels||[]).forEach((p: string) => {
      if(p === 'chat_panel'){
        // Skip chat_panel to avoid duplicate Chat UI; the core Chat pane is always present if chat is selected
        return
      } else if(p === 'predictions_dashboard'){
        items.push({ key: `${m.id}:${p}`, title: 'Predictions Dashboard', description: 'Predictor dashboard from '+m.id })
      } else if(p === 'vision_preview'){
        items.push({ key: `${m.id}:${p}`, title: 'Vision Preview', description: 'Vision preview panel from '+m.id })
      } else if(p === 'speech_console'){
        items.push({ key: `${m.id}:${p}`, title: 'Speech Console', description: 'Speech console panel from '+m.id })
      }
    })
  })

  if(items.length === 0){
    return <div style={{fontSize:12, color:'#6b7280'}}>No runtime panels declared by selected modules.</div>
  }

  return (
    <div style={{display:'grid', gap:12}}>
      {items.map(it => (
        <div key={it.key} style={{border:'1px solid #e5e7eb', borderRadius:12, padding:12}}>
          <strong>{it.title}</strong>
          <div style={{fontSize:12, color:'#374151', marginTop:4}}>{it.description}</div>
        </div>
      ))}
    </div>
  )
}
