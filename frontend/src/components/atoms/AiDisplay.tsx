import { useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import rehypeRaw from 'rehype-raw'
import remarkGfm from 'remark-gfm'
import DOMPurify from 'dompurify'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'

type Props = {
  content: string
  className?: string
}

export function AiDisplay({ content, className = '' }: Props) {
  const sanitizedContent = useMemo(() => {
    if (!content) return ''
    return DOMPurify.sanitize(content, {
      FORCE_BODY: true,
      ALLOWED_TAGS: [
        'p', 'b', 'i', 'em', 'strong', 'a', 'ul', 'ol', 'li', 'br',
        'code', 'pre', 'span', 'h1', 'h2', 'h3', 'h4',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
      ],
      ALLOWED_ATTR: ['href', 'target', 'class'],
    })
  }, [content])

  return (
    <div className={`ai-content-wrapper ${className}`} style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
      <ReactMarkdown
        rehypePlugins={[rehypeRaw]}
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ node, ...props }) => (
            <a {...props} target="_blank" rel="noopener noreferrer" className="text-[#3ecf8e] hover:underline" />
          ),
          code({ node, inline, className: codeClassName, children, ...props }: any) {
            const match = /language-(\w+)/.exec(codeClassName || '')
            return !inline && match ? (
              <SyntaxHighlighter
                style={vscDarkPlus}
                language={match[1]}
                PreTag="div"
                {...props}
              >
                {String(children).replace(/\n$/, '')}
              </SyntaxHighlighter>
            ) : (
              <code className={codeClassName} {...props}>{children}</code>
            )
          },
        }}
      >
        {sanitizedContent}
      </ReactMarkdown>
    </div>
  )
}
