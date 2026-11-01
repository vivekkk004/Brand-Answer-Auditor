import Badge from '../ui/Badge'

const ROLE = {
  user: { label: 'Input', tone: 'slate' },
  assistant: { label: 'Model', tone: 'indigo' },
  tool: { label: 'Tool result', tone: 'green' },
}

function pretty(value) {
  if (typeof value !== 'string') return JSON.stringify(value, null, 2)
  try {
    return JSON.stringify(JSON.parse(value), null, 2)
  } catch {
    return value
  }
}

function CodeBlock({ children }) {
  return (
    <pre className="mt-2 max-h-72 overflow-auto rounded-lg bg-slate-50 p-3 text-xs leading-5 whitespace-pre-wrap text-slate-700 ring-1 ring-slate-200">
      {children}
    </pre>
  )
}

/**
 * The verifier agent's whole conversation, as saved on the answer: what the model was
 * given, which tools it called with which arguments, and what the tools returned.
 * This is the trace used to debug a wrong label or a failed verification.
 */
export default function AgentConversation({ exchanges }) {
  if (!exchanges?.length) {
    return <p className="text-sm text-slate-500">No agent conversation was recorded.</p>
  }

  return (
    <ol className="relative space-y-4 border-l border-slate-200 pl-6">
      {exchanges.map((message, index) => {
        const role = ROLE[message.role] || { label: message.role, tone: 'slate' }
        return (
          <li key={index} className="relative">
            <span className="absolute top-1.5 -left-[29px] h-2.5 w-2.5 rounded-full border-2 border-white bg-slate-300" />
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={role.tone}>{role.label}</Badge>
              {message.tool_name ? (
                <code className="text-xs text-slate-500">{message.tool_name}</code>
              ) : null}
              <span className="text-xs text-slate-400">step {index + 1}</span>
            </div>
            {message.content ? <CodeBlock>{pretty(message.content)}</CodeBlock> : null}
            {message.tool_calls?.map((call) => (
              <div key={call.id} className="mt-2">
                <p className="text-xs font-medium text-slate-600">
                  Calls <code className="text-indigo-700">{call.name}</code>
                </p>
                <CodeBlock>{pretty(call.arguments)}</CodeBlock>
              </div>
            ))}
          </li>
        )
      })}
    </ol>
  )
}
