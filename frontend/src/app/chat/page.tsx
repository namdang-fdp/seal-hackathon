'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import {
  Send,
  Paperclip,
  Plus,
  FileText,
  X,
  Sparkles,
  MessageSquare,
  ChevronRight,
  File,
  FileSpreadsheet,
  FileType2,
  Bot,
  User,
  PanelRightOpen,
  PanelRightClose,
} from 'lucide-react'

/* ── Types ─────────────────────────────────── */

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  attachedFiles?: AttachedFile[]
}

interface AttachedFile {
  id: string
  name: string
  type: string
  size: string
}

interface Conversation {
  id: string
  title: string
  lastMessage: string
  date: Date
  messageCount: number
}

/* ── Mock Data ─────────────────────────────── */

const mockFiles: AttachedFile[] = [
  { id: 'f1', name: 'sales_data_q4.csv', type: 'csv', size: '2.4 MB' },
  { id: 'f2', name: 'product_specs.pdf', type: 'pdf', size: '5.1 MB' },
  { id: 'f3', name: 'user_feedback.json', type: 'json', size: '890 KB' },
  { id: 'f4', name: 'meeting_notes.md', type: 'md', size: '12 KB' },
  { id: 'f5', name: 'financial_report.xlsx', type: 'xlsx', size: '3.7 MB' },
]

const mockConversations: Conversation[] = [
  { id: 'c1', title: 'Q4 Sales Analysis', lastMessage: 'The revenue trend shows a 12% increase...', date: new Date('2026-04-11'), messageCount: 8 },
  { id: 'c2', title: 'Product Feature Extraction', lastMessage: 'Based on the specs document, the top features...', date: new Date('2026-04-10'), messageCount: 14 },
  { id: 'c3', title: 'User Sentiment Report', lastMessage: 'Overall sentiment is 72% positive across...', date: new Date('2026-04-09'), messageCount: 6 },
]

const suggestedPrompts = [
  { icon: '📊', title: 'Analyze my data', description: 'Summarize trends and key insights from your uploaded files' },
  { icon: '🔍', title: 'Find patterns', description: 'Discover hidden correlations and patterns in your datasets' },
  { icon: '📝', title: 'Generate report', description: 'Create a comprehensive report from your data files' },
  { icon: '❓', title: 'Ask a question', description: 'Get specific answers about your uploaded documents' },
]

/* ── Helpers ────────────────────────────────── */

function getFileIcon(type: string) {
  switch (type) {
    case 'csv':
    case 'xlsx':
      return <FileSpreadsheet className="w-4 h-4" />
    case 'pdf':
      return <FileText className="w-4 h-4" />
    case 'md':
    case 'txt':
      return <FileType2 className="w-4 h-4" />
    default:
      return <File className="w-4 h-4" />
  }
}

function getFileColor(type: string) {
  switch (type) {
    case 'csv':
    case 'xlsx':
      return 'text-emerald-400 bg-emerald-500/10'
    case 'pdf':
      return 'text-rose-400 bg-rose-500/10'
    case 'json':
      return 'text-amber-400 bg-amber-500/10'
    case 'md':
    case 'txt':
      return 'text-sky-400 bg-sky-500/10'
    default:
      return 'text-zinc-400 bg-zinc-500/10'
  }
}

/* ── AI response simulator ─────────────────── */

function generateAIResponse(userMessage: string, files: AttachedFile[]): string {
  const fileNames = files.map(f => f.name).join(', ')
  const lowerMsg = userMessage.toLowerCase()

  if (files.length > 0 && (lowerMsg.includes('analyz') || lowerMsg.includes('summary') || lowerMsg.includes('summariz'))) {
    return `I've analyzed the files you referenced (${fileNames}). Here's what I found:\n\n**Key Findings:**\n- The dataset contains approximately 15,000 records with 12 feature columns\n- There are clear seasonal patterns visible in the time-series data\n- 3 potential outlier clusters were detected that may require attention\n\n**Recommendations:**\n1. Consider normalizing the revenue figures for YoY comparison\n2. The Q3 dip correlates with the product transition period\n3. I'd suggest segmenting the data by region for more granular insights\n\nWould you like me to dive deeper into any of these areas?`
  }

  if (lowerMsg.includes('trend') || lowerMsg.includes('pattern')) {
    return `Looking at the available data, I've identified several notable trends:\n\n📈 **Upward Trends:**\n- User engagement has increased 23% month-over-month\n- Average session duration grew from 4.2 to 6.8 minutes\n\n📉 **Areas of Concern:**\n- Bounce rate on mobile has increased by 8%\n- Cart abandonment rate peaked at 67% in early March\n\n🔄 **Cyclical Patterns:**\n- Weekend traffic consistently outperforms weekdays by 35%\n- There's a clear end-of-month spike in transaction volume\n\nShall I generate a detailed visualization report for these trends?`
  }

  if (lowerMsg.includes('report') || lowerMsg.includes('generate')) {
    return `I'll prepare a comprehensive report based on your data. Here's the structure:\n\n## Report Outline\n\n### 1. Executive Summary\nHigh-level overview of key metrics and findings\n\n### 2. Data Quality Assessment\n- Completeness: 94.3%\n- Missing values: Concentrated in 3 columns\n- Detected anomalies: 12 records flagged\n\n### 3. Statistical Analysis\nDistribution analysis, correlation matrix, and significance tests\n\n### 4. Actionable Insights\nPrioritized recommendations with confidence scores\n\n### 5. Appendix\nRaw calculations and methodology notes\n\n*Estimated generation time: ~2 minutes*\n\nShall I proceed with generating the full report?`
  }

  return `Thanks for your question! Based on the context from your uploaded files${files.length > 0 ? ` (${fileNames})` : ''}, here's what I can tell you:\n\nI've processed the relevant data and found some interesting insights. The information indicates several key points worth examining further.\n\nWould you like me to:\n1. **Dive deeper** into a specific aspect of the data?\n2. **Compare** different data points or time periods?\n3. **Export** the analysis results in a specific format?\n\nJust let me know how you'd like to proceed!`
}

/* ── Page Component ────────────────────────── */

export default function ChatPage() {
  const [conversations, setConversations] = useState<Conversation[]>(mockConversations)
  const [activeConversation, setActiveConversation] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([])
  const [showFileSelector, setShowFileSelector] = useState(false)
  const [showContextPanel, setShowContextPanel] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, isTyping, scrollToBottom])

  const handleNewChat = () => {
    setActiveConversation(null)
    setMessages([])
    setAttachedFiles([])
    setInputValue('')
  }

  const handleSelectConversation = (conv: Conversation) => {
    setActiveConversation(conv.id)
    // Load mock messages for selected conversation
    setMessages([
      {
        id: '1',
        role: 'user',
        content: `Tell me about ${conv.title.toLowerCase()}`,
        timestamp: new Date(conv.date.getTime() - 60000),
      },
      {
        id: '2',
        role: 'assistant',
        content: conv.lastMessage + '\n\nI can provide more detailed analysis if you share the relevant data files.',
        timestamp: conv.date,
      },
    ])
  }

  const handleSendMessage = () => {
    if (!inputValue.trim() && attachedFiles.length === 0) return

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue,
      timestamp: new Date(),
      attachedFiles: attachedFiles.length > 0 ? [...attachedFiles] : undefined,
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    const filesForResponse = [...attachedFiles]
    setAttachedFiles([])
    setIsTyping(true)

    // If no active conversation, create one
    if (!activeConversation) {
      const newConv: Conversation = {
        id: Date.now().toString(),
        title: inputValue.slice(0, 40) + (inputValue.length > 40 ? '...' : ''),
        lastMessage: '',
        date: new Date(),
        messageCount: 1,
      }
      setConversations(prev => [newConv, ...prev])
      setActiveConversation(newConv.id)
    }

    // Simulate AI response
    setTimeout(() => {
      const response = generateAIResponse(inputValue, filesForResponse)
      const aiMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, aiMessage])
      setIsTyping(false)
    }, 1500 + Math.random() * 1000)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const toggleFileAttachment = (file: AttachedFile) => {
    setAttachedFiles(prev =>
      prev.find(f => f.id === file.id)
        ? prev.filter(f => f.id !== file.id)
        : [...prev, file]
    )
  }

  const isEmptyState = messages.length === 0

  return (
    <div className="flex h-screen">
      {/* ── Left: Conversation History ──────────── */}
      <div className="w-[280px] flex-shrink-0 border-r border-white/[0.06] bg-zinc-950/50 flex flex-col">
        <div className="p-4">
          <button
            onClick={handleNewChat}
            className="flex items-center justify-center gap-2 w-full px-4 py-2.5 rounded-lg text-sm font-medium gradient-violet text-white hover:opacity-90 transition-opacity"
          >
            <Plus className="w-4 h-4" />
            New Chat
          </button>
        </div>

        <div className="px-4 pb-2">
          <p className="text-[10px] font-semibold text-zinc-500 uppercase tracking-widest">
            Recent
          </p>
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar px-2 space-y-0.5 stagger-children">
          {conversations.map(conv => (
            <button
              key={conv.id}
              onClick={() => handleSelectConversation(conv)}
              className={`w-full text-left px-3 py-3 rounded-lg transition-all duration-200 group ${
                activeConversation === conv.id
                  ? 'bg-white/[0.08] text-white'
                  : 'text-zinc-400 hover:bg-white/[0.04] hover:text-zinc-200'
              }`}
            >
              <div className="flex items-start gap-2.5">
                <MessageSquare className="w-4 h-4 mt-0.5 flex-shrink-0 text-zinc-500 group-hover:text-zinc-400 transition-colors" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium truncate">{conv.title}</p>
                  <p className="text-xs text-zinc-500 truncate mt-0.5">{conv.lastMessage}</p>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* ── Center: Chat Area ──────────────────── */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Chat header */}
        <div className="flex items-center justify-between px-6 py-3 border-b border-white/[0.06] bg-zinc-950/30">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg gradient-violet flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-zinc-100">RAGNAROK AI</h2>
              <p className="text-[11px] text-zinc-500">
                {isTyping ? 'Thinking...' : 'Ready to assist'}
              </p>
            </div>
          </div>
          <button
            onClick={() => setShowContextPanel(!showContextPanel)}
            className="p-2 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.04] transition-all"
            title={showContextPanel ? 'Hide context panel' : 'Show context panel'}
          >
            {showContextPanel ? (
              <PanelRightClose className="w-5 h-5" />
            ) : (
              <PanelRightOpen className="w-5 h-5" />
            )}
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          {isEmptyState ? (
            /* ── Empty State ──────────────────── */
            <div className="flex flex-col items-center justify-center h-full px-6 animate-fade-in">
              <div className="w-16 h-16 rounded-2xl gradient-violet flex items-center justify-center mb-6 animate-pulse-glow">
                <Sparkles className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-zinc-100 mb-2">How can I help you today?</h2>
              <p className="text-sm text-zinc-500 mb-8 max-w-md text-center">
                Upload files in the Files tab, then ask me anything about your data. I can analyze, summarize, and find insights.
              </p>
              <div className="grid grid-cols-2 gap-3 max-w-lg w-full">
                {suggestedPrompts.map((prompt, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      setInputValue(prompt.title)
                      inputRef.current?.focus()
                    }}
                    className="text-left p-4 rounded-xl border border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.05] hover:border-violet-500/30 transition-all duration-200 group"
                  >
                    <span className="text-xl mb-2 block">{prompt.icon}</span>
                    <p className="text-sm font-medium text-zinc-200 group-hover:text-white transition-colors">
                      {prompt.title}
                    </p>
                    <p className="text-xs text-zinc-500 mt-1">{prompt.description}</p>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            /* ── Message Thread ───────────────── */
            <div className="px-6 py-6 space-y-6">
              {messages.map((msg, idx) => (
                <div
                  key={msg.id}
                  className={`flex gap-3 animate-fade-in-up ${
                    msg.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                  style={{ animationDelay: `${idx * 40}ms` }}
                >
                  {msg.role === 'assistant' && (
                    <div className="flex-shrink-0 w-8 h-8 rounded-lg gradient-violet flex items-center justify-center mt-1">
                      <Bot className="w-4 h-4 text-white" />
                    </div>
                  )}
                  <div
                    className={`max-w-[70%] ${
                      msg.role === 'user'
                        ? 'bg-violet-600/20 border border-violet-500/20 rounded-2xl rounded-br-md'
                        : 'bg-white/[0.04] border border-white/[0.06] rounded-2xl rounded-bl-md'
                    } px-4 py-3`}
                  >
                    {/* Attached files in user messages */}
                    {msg.attachedFiles && msg.attachedFiles.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mb-2">
                        {msg.attachedFiles.map(file => (
                          <span
                            key={file.id}
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium ${getFileColor(file.type)}`}
                          >
                            {getFileIcon(file.type)}
                            {file.name}
                          </span>
                        ))}
                      </div>
                    )}
                    <p className="text-sm text-zinc-200 whitespace-pre-wrap leading-relaxed">
                      {msg.content}
                    </p>
                    <p className="text-[10px] text-zinc-600 mt-2">
                      {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </p>
                  </div>
                  {msg.role === 'user' && (
                    <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-zinc-700 flex items-center justify-center mt-1">
                      <User className="w-4 h-4 text-zinc-300" />
                    </div>
                  )}
                </div>
              ))}

              {/* Typing indicator */}
              {isTyping && (
                <div className="flex gap-3 animate-fade-in">
                  <div className="flex-shrink-0 w-8 h-8 rounded-lg gradient-violet flex items-center justify-center">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                  <div className="bg-white/[0.04] border border-white/[0.06] rounded-2xl rounded-bl-md px-5 py-4">
                    <div className="typing-indicator flex items-center gap-[2px]">
                      <span />
                      <span />
                      <span />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* ── Input Area ──────────────────────── */}
        <div className="px-6 py-4 border-t border-white/[0.06] bg-zinc-950/50">
          {/* Attached files preview */}
          {attachedFiles.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-3 animate-fade-in">
              {attachedFiles.map(file => (
                <span
                  key={file.id}
                  className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium ${getFileColor(file.type)} border border-white/[0.06]`}
                >
                  {getFileIcon(file.type)}
                  {file.name}
                  <button
                    onClick={() => toggleFileAttachment(file)}
                    className="ml-1 hover:text-white transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          )}

          <div className="flex items-end gap-3">
            {/* File attach button */}
            <div className="relative">
              <button
                onClick={() => setShowFileSelector(!showFileSelector)}
                className={`p-2.5 rounded-lg transition-all duration-200 ${
                  showFileSelector
                    ? 'bg-violet-600/20 text-violet-400'
                    : 'text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.04]'
                }`}
              >
                <Paperclip className="w-5 h-5" />
              </button>

              {/* File selector dropdown */}
              {showFileSelector && (
                <div className="absolute bottom-12 left-0 w-72 glass rounded-xl border border-white/[0.08] shadow-2xl p-2 animate-fade-in-up z-50">
                  <p className="px-3 py-2 text-[10px] font-semibold text-zinc-500 uppercase tracking-widest">
                    Attach files as context
                  </p>
                  {mockFiles.map(file => {
                    const isSelected = attachedFiles.find(f => f.id === file.id)
                    return (
                      <button
                        key={file.id}
                        onClick={() => toggleFileAttachment(file)}
                        className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-all duration-200 ${
                          isSelected
                            ? 'bg-violet-600/15 border border-violet-500/20'
                            : 'hover:bg-white/[0.04] border border-transparent'
                        }`}
                      >
                        <div className={`p-1.5 rounded-md ${getFileColor(file.type)}`}>
                          {getFileIcon(file.type)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-zinc-200 truncate">{file.name}</p>
                          <p className="text-[11px] text-zinc-500">{file.size}</p>
                        </div>
                        {isSelected && (
                          <div className="w-5 h-5 rounded-full gradient-violet flex items-center justify-center">
                            <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                            </svg>
                          </div>
                        )}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Text input */}
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask anything about your files..."
                rows={1}
                className="chat-input w-full px-4 py-3 rounded-xl bg-white/[0.04] border border-white/[0.08] text-zinc-100 placeholder-zinc-500 text-sm resize-none focus:outline-none focus:border-violet-500/40 focus:bg-white/[0.06] transition-all duration-200"
              />
            </div>

            {/* Send button */}
            <button
              onClick={handleSendMessage}
              disabled={!inputValue.trim() && attachedFiles.length === 0}
              className="p-2.5 rounded-lg gradient-violet text-white hover:opacity-90 transition-opacity disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* ── Right: Context Panel ───────────────── */}
      {showContextPanel && (
        <div className="w-[280px] flex-shrink-0 border-l border-white/[0.06] bg-zinc-950/50 flex flex-col animate-slide-in-right">
          <div className="p-4 border-b border-white/[0.06]">
            <div className="flex items-center gap-2">
              <ChevronRight className="w-4 h-4 text-zinc-500" />
              <h3 className="text-sm font-semibold text-zinc-200">Context Files</h3>
            </div>
            <p className="text-[11px] text-zinc-500 mt-1">
              Files available for this chat session
            </p>
          </div>

          <div className="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-1.5 stagger-children">
            {mockFiles.map(file => {
              const isAttached = attachedFiles.find(f => f.id === file.id)
              return (
                <button
                  key={file.id}
                  onClick={() => toggleFileAttachment(file)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all duration-200 group ${
                    isAttached
                      ? 'bg-violet-600/10 border border-violet-500/20'
                      : 'hover:bg-white/[0.03] border border-transparent'
                  }`}
                >
                  <div className={`p-2 rounded-lg ${getFileColor(file.type)}`}>
                    {getFileIcon(file.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[13px] font-medium text-zinc-300 group-hover:text-zinc-100 truncate transition-colors">
                      {file.name}
                    </p>
                    <p className="text-[11px] text-zinc-600">{file.size} · {file.type.toUpperCase()}</p>
                  </div>
                </button>
              )
            })}
          </div>

          <div className="p-4 border-t border-white/[0.06]">
            <div className="flex items-center gap-2 text-[11px] text-zinc-500">
              <FileText className="w-3.5 h-3.5" />
              <span>{mockFiles.length} files available</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
