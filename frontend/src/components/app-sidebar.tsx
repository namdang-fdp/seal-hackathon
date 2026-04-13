'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import {
  MessageSquare,
  FolderOpen,
  LogOut,
  Zap,
} from 'lucide-react'

const navItems = [
  { href: '/chat', label: 'Chat', icon: MessageSquare },
  { href: '/files', label: 'Files', icon: FolderOpen },
]

export function AppSidebar() {
  const pathname = usePathname()
  const router = useRouter()

  const handleLogout = () => {
    localStorage.removeItem('auth_token')
    router.push('/auth/login')
  }

  return (
    <aside className="fixed left-0 top-0 h-screen w-[260px] flex flex-col bg-zinc-950/80 backdrop-blur-xl border-r border-white/[0.06] z-50">
      {/* Brand */}
      <div className="px-6 py-6 border-b border-white/[0.06]">
        <Link href="/chat" className="flex items-center gap-3 group">
          <div className="relative flex items-center justify-center w-9 h-9 rounded-lg gradient-violet animate-pulse-glow">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-[15px] font-bold tracking-tight text-zinc-100 group-hover:text-white transition-colors">
              RAGNAROK
            </h1>
            <p className="text-[10px] font-medium text-zinc-500 tracking-widest uppercase">
              AI Agency
            </p>
          </div>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        <p className="px-3 mb-3 text-[10px] font-semibold text-zinc-500 uppercase tracking-widest">
          Workspace
        </p>
        {navItems.map((item) => {
          const isActive =
            pathname === item.href || pathname.startsWith(item.href + '/')
          const Icon = item.icon

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`
                relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 group
                ${
                  isActive
                    ? 'text-white bg-white/[0.08]'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04]'
                }
              `}
            >
              {/* Active indicator bar */}
              {isActive && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full gradient-violet animate-fade-in" />
              )}
              <Icon
                className={`w-[18px] h-[18px] transition-colors duration-200 ${
                  isActive
                    ? 'text-violet-400'
                    : 'text-zinc-500 group-hover:text-zinc-300'
                }`}
              />
              <span>{item.label}</span>
              {isActive && (
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-violet-400 animate-fade-in" />
              )}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-3 py-4 border-t border-white/[0.06]">
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.04] transition-all duration-200 group"
        >
          <LogOut className="w-[18px] h-[18px] text-zinc-600 group-hover:text-zinc-400 transition-colors" />
          <span>Log Out</span>
        </button>
      </div>
    </aside>
  )
}
