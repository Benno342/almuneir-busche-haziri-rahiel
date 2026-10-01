import { useState } from 'react'
import { BookingsPage } from './pages/BookingsPage'
import { PaymentsPage } from './pages/PaymentsPage'
import { SlotsPage } from './pages/SlotsPage'
import { WaitlistPage } from './pages/WaitlistPage'

const PAGES = {
  slots: { label: 'Courts & Slots', Component: SlotsPage },
  bookings: { label: 'Meine Buchungen', Component: BookingsPage },
  payments: { label: 'Zahlungen', Component: PaymentsPage },
  waitlist: { label: 'Warteliste', Component: WaitlistPage },
} as const

type PageKey = keyof typeof PAGES

export default function App() {
  const [page, setPage] = useState<PageKey>('slots')
  const { Component } = PAGES[page]

  return (
    <div className="app">
      <header>
        <h1>Padel Club</h1>
        <nav>
          {(Object.keys(PAGES) as PageKey[]).map((key) => (
            <button key={key} aria-current={key === page ? 'page' : undefined} onClick={() => setPage(key)}>
              {PAGES[key].label}
            </button>
          ))}
        </nav>
      </header>
      <main>
        <Component />
      </main>
    </div>
  )
}
