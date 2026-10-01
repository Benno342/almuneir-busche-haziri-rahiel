import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import App from './App'

describe('App', () => {
  it('shows the slots page first', () => {
    render(<App />)
    expect(screen.getByRole('heading', { level: 2, name: 'Courts & Slots' })).toBeInTheDocument()
  })

  it('navigates between the placeholder pages', async () => {
    render(<App />)
    await userEvent.click(screen.getByRole('button', { name: 'Warteliste' }))
    expect(screen.getByRole('heading', { level: 2, name: 'Warteliste' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Warteliste' })).toHaveAttribute('aria-current', 'page')
  })
})
