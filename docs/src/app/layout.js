'use client'
import './globals.css'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useState } from 'react'

const nav = [
  { title: 'Getting Started', href: '/' },
  { title: 'Core Concepts', href: '/core-concepts' },
  { title: 'Graph Memory', href: '/graph-memory' },
  { title: 'AI Processing', href: '/ai-processing' },
  { title: 'Python SDK', href: '/python-sdk' },
  { title: 'Node.js SDK', href: '/nodejs-sdk' },
  { title: 'Cloud API', href: '/cloud-api' },
  { title: 'Self-Hosting', href: '/self-hosting' },
  { title: 'Pricing', href: '/pricing' },
]

function Sidebar({ open, onClose }) {
  const pathname = usePathname()
  return (
    <nav className={`sidebar ${open ? 'open' : ''}`}>
      <Link href="/" className="logo" onClick={onClose}>🧠 AgentRecall</Link>
      <div className="nav-section">
        {nav.map(item => (
          <Link
            key={item.href}
            href={item.href}
            className={pathname === item.href ? 'nav-link active' : 'nav-link'}
            onClick={onClose}
          >
            {item.title}
          </Link>
        ))}
      </div>
    </nav>
  )
}

export default function RootLayout({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
      </head>
      <body>
        <button className="menu-btn" onClick={() => setSidebarOpen(!sidebarOpen)}>☰</button>
        <div className="layout">
          <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
          <main className="content">{children}</main>
        </div>
      </body>
    </html>
  )
}
