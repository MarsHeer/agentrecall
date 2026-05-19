'use client'

export function CodeBlock({ children, language = '' }) {
  return (
    <pre><code dangerouslySetInnerHTML={{ __html: children }} /></pre>
  )
}

export function InlineCode({ children }) {
  return <code>{children}</code>
}
