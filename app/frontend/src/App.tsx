import React, { useEffect, useState } from 'react'
import { Routes, Route, Link, Navigate } from 'react-router-dom'
import ModuleSelection from './pages/ModuleSelection'
import ModelLauncherOps from './pages/ModelLauncherOps'
import AIWorkspace from './pages/AIWorkspace'
import ModelLab from './pages/ModelLab'
import NeuralNets from './pages/NeuralNets'
import { BrowserRouter } from 'react-router-dom'

function TopBar() {
  const [ws, setWs] = React.useState<any>(null)
  React.useEffect(()=>{
    fetch('/api/workspace').then(r=>r.ok?r.json():null).then(setWs).catch(()=>{})
  },[])
  const name = ws?.name || 'Session'
  const seed = ws?.seed ?? 1337
  return (
    <div style={{display:'flex',justifyContent:'space-between',padding:'12px',borderBottom:'1px solid #e5e7eb'}}>
      <div>
        <strong>Modular Offline AI App</strong>
        <div style={{fontSize:12, color:'#6b7280'}}>Session: {name} • Seed: {seed}</div>
      </div>
      <nav style={{display:'flex',gap:12}}>
        <Link to="/modules">Modules</Link>
        <Link to="/nns">Neural Nets</Link>
        <Link to="/models">Models</Link>
        <Link to="/workspace">Workspace</Link>
        <Link to="/workspace/model-lab">Lab</Link>
      </nav>
    </div>
  )
}

export default function App(){
  return (
    <BrowserRouter>
      <TopBar />
      <div style={{padding:16}}>
        <Routes>
          <Route path="/" element={<Navigate to="/modules" replace />} />
          <Route path="/modules" element={<ModuleSelection />} />
          <Route path="/nns" element={<NeuralNets />} />
          <Route path="/models" element={<ModelLauncherOps />} />
          <Route path="/workspace" element={<AIWorkspace />} />
          <Route path="/workspace/model-lab" element={<ModelLab />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
