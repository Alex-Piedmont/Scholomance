import type React from 'react'
import { stripHtml } from '../parseRawData'

export function ContentSectionWrapper({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <div className="py-5 border-b border-gray-100 last:border-b-0">
      <h2 className="text-lg font-semibold text-gray-900 mb-3">{title}</h2>
      {children}
    </div>
  )
}

export function TextSection({ title, text }: { title: string; text?: string }) {
  if (!text) return null
  return (
    <ContentSectionWrapper title={title}>
      <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">{text}</p>
    </ContentSectionWrapper>
  )
}

export function BulletSection({
  title,
  items,
  color = 'blue',
}: {
  title: string
  items: string[]
  color?: string
}) {
  if (!items.length) return null
  const dotClass = color === 'green' ? 'text-green-500' : 'text-blue-500'
  return (
    <ContentSectionWrapper title={title}>
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="flex gap-2 text-gray-700">
            <span className={`${dotClass} mt-1 flex-shrink-0`}>•</span>
            <span>{item.replace(/\r\r/g, ' ').replace(/\r/g, ' ')}</span>
          </li>
        ))}
      </ul>
    </ContentSectionWrapper>
  )
}

export function CheckmarkListSection({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null
  return (
    <ContentSectionWrapper title={title}>
      <ul className="space-y-2">
        {items.map((adv, i) => (
          <li key={i} className="flex gap-2 text-gray-700">
            <span className="text-green-500 mt-1 flex-shrink-0">✓</span>
            <span>{adv}</span>
          </li>
        ))}
      </ul>
    </ContentSectionWrapper>
  )
}

export function SideSectionWrapper({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <div className="py-4 first:pt-0 last:pb-0">
      <h3 className="text-sm font-semibold text-gray-900 mb-2 uppercase tracking-wide">
        {title}
      </h3>
      {children}
    </div>
  )
}

export function DocIcon() {
  return (
    <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
      />
    </svg>
  )
}

export { stripHtml }
