import { createContext, useContext } from 'react'
import type { GateReason } from './LoginModal'

interface GateContextValue {
  requireLogin: (reason: GateReason) => void
}

export const GateContext = createContext<GateContextValue>({
  requireLogin: () => {},
})

export function useRequireLogin() {
  return useContext(GateContext).requireLogin
}
