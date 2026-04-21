import { useState, useEffect, useCallback } from 'react'
import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { LoginModal, type GateReason } from './LoginModal'
import { GateContext } from './gateContext'
import { statsApi } from '../../api/client'
import type { StatsOverview } from '../../api/types'

export function Layout() {
  const [gate, setGate] = useState<{ open: boolean; reason: GateReason }>({
    open: false,
    reason: null,
  })
  const [stats, setStats] = useState<StatsOverview | null>(null)
  const location = useLocation()

  useEffect(() => {
    statsApi.getOverview().then(setStats).catch(() => setStats(null))
  }, [])

  const requireLogin = useCallback((reason: GateReason) => {
    setGate({ open: true, reason })
  }, [])

  const closeLogin = useCallback(() => {
    setGate((prev) => ({ ...prev, open: false }))
  }, [])

  const onGatedClick =
    (reason: GateReason) =>
    (e: React.MouseEvent<HTMLButtonElement>) => {
      e.preventDefault()
      requireLogin(reason)
    }

  const isDiscoverActive =
    location.pathname === '/' || location.pathname.startsWith('/browse')

  return (
    <GateContext.Provider value={{ requireLogin }}>
      <div className="app">
        <header className="app-header">
          <div className="app-header__inner">
            <NavLink to="/" className="brand-lockup" aria-label="Phronesis home">
              <img src="/assets/piedmont-wordmark.png" alt="Piedmont" />
              <div className="brand-lockup__divider" />
              <div className="brand-lockup__product">
                <div className="brand-lockup__name">Phronesis</div>
                <div className="brand-lockup__sub">University Tech Transfer</div>
              </div>
            </NavLink>

            <nav className="header-nav">
              <NavLink
                to="/"
                className={isDiscoverActive ? 'is-active' : undefined}
                end={false}
              >
                Discover
              </NavLink>
              <button type="button" onClick={onGatedClick('Enrich')}>
                Enrich
              </button>
              <button type="button" onClick={onGatedClick('Evaluate')}>
                Evaluate
              </button>
            </nav>

            <div className="header-stats">
              {stats && (
                <>
                  <div className="header-stats__item">
                    <b>{stats.total_technologies.toLocaleString()}</b> technologies
                  </div>
                  <div className="header-stats__item">
                    <b>{stats.total_universities}</b> universities
                  </div>
                </>
              )}
            </div>
          </div>
        </header>

        <Outlet />

        <footer className="app-footer">
          <img src="/assets/piedmont-mountain-navy.png" alt="" />
          <span>Piedmont Innovation</span>
          <span className="sep">·</span>
          <span>Phronesis</span>
          <span className="sep">·</span>
          <a
            href="https://github.com/Alex-Piedmont/Scholomance"
            target="_blank"
            rel="noreferrer"
          >
            Scholomance repo
          </a>
        </footer>

        <LoginModal open={gate.open} onClose={closeLogin} gateReason={gate.reason} />
      </div>
    </GateContext.Provider>
  )
}
