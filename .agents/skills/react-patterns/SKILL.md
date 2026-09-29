---
name: react-patterns
description: React 19 patterns for THIS project — a React + Vite SPA with TanStack Router and TanStack Query. Covers hooks discipline, Suspense + error boundaries, forms, data fetching, state-location decisions, and accessibility-first composition. No Next.js / RSC / Server Components. Use when writing or reviewing React components.
metadata:
  origin: ECC (adapted for this project — React + Vite SPA, no RSC)
---

# React Patterns

Idiomatic React 19 patterns for this project's frontend.

**Stack note:** this is a **client-side SPA built with React 19 + Vite**, using
**TanStack Router** for routing and **TanStack Query** for server state. There
are **no React Server Components, no `"use client"`/`"use server"` directives,
and no Server Actions** — those are Next.js/RSC-framework concerns and do not
apply here. Prefer the TanStack ecosystem for new capabilities (see
`frontend/README.md`).

## When to Activate

- Writing or modifying React function components, custom hooks, or component trees
- Reviewing JSX/TSX files
- Designing state shape or component composition
- Choosing between local state, lifted state, context, and external stores
- Implementing forms or wiring data fetching with TanStack Query

## Core Principles

### 1. Render is a Pure Function of Props and State

```tsx
// Good: derive during render
function Cart({ items }: { items: CartItem[] }) {
  const total = items.reduce((sum, i) => sum + i.price * i.qty, 0)
  return <span>{formatMoney(total)}</span>
}

// Bad: derived state stored separately
function Cart({ items }: { items: CartItem[] }) {
  const [total, setTotal] = useState(0)
  useEffect(() => {
    setTotal(items.reduce((sum, i) => sum + i.price * i.qty, 0))
  }, [items])
  return <span>{formatMoney(total)}</span>
}
```

Derived state in `useEffect` adds a render cycle, can desync, and obscures the
data flow.

### 2. Side Effects Outside Render

Effects, mutations, network calls, and subscriptions live in event handlers or
`useEffect` — never in the render body.

### 3. Composition Over Inheritance

React has no inheritance model for components. Compose with `children`, render
props, or component props.

## Hooks Discipline

- Call hooks at the top level only, never conditionally
- Clean up every subscription, interval, and listener in the effect's return
- Use the functional updater (`setX(prev => prev + 1)`) when new state depends on
  old
- Default position: **do not memoize**. Add `useMemo`/`useCallback` only when a
  profiler or a real dependency chain proves it matters
- Extract a custom hook only when the same hook sequence appears in 2+ components

## State Location Decision Tree

```
Used by one component?
  -> useState inside it

Used by parent + a few descendants?
  -> lift to nearest common ancestor

Used across distant branches AND low-frequency reads (theme, auth, locale)?
  -> React Context

High-frequency updates shared across the tree?
  -> external store — prefer TanStack Store (fits this stack)

Derived from a server?
  -> TanStack Query (already the standard here)
```

Most pages need neither context nor a global store. Server data belongs in
TanStack Query, not in `useState`/context. Resist abstraction until duplicated
lifting becomes painful.

## Data Fetching (use TanStack Query)

This project fetches all server state through **TanStack Query**. Do **not** use
`useEffect` + `fetch` for application data — it invites race conditions and has
no cache, retry, or Suspense integration.

```tsx
// matches src/pages/HomePage.tsx
import { useQuery } from '@tanstack/react-query'
import { fetchUsers } from '../api/users'

function UsersPage() {
  const { data: users, isPending, isError, error } = useQuery({
    queryKey: ['users'],
    queryFn: fetchUsers,
  })

  if (isPending) return <Spinner />
  if (isError) return <ErrorView error={error} />
  return <UserList users={users} />
}
```

| Need | Tool |
|---|---|
| Client cache + mutations + invalidation | TanStack Query (`useQuery`, `useMutation`) |
| One-off fire-and-forget (e.g. analytics ping) | `fetch()` in an event handler |
| Real-time updates | Server-Sent Events / WebSockets, surfaced into Query cache |

Keep `fetch` wrappers in `src/api/` (like `src/api/users.ts`) and reference them
as `queryFn`s — don't inline `fetch` in components.

### Mutations + invalidation

```tsx
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createUser } from '../api/users'

function useCreateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: createUser,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })
}
```

## Suspense + Error Boundaries

```tsx
<ErrorBoundary fallback={<ErrorView />}>
  <Suspense fallback={<UserSkeleton />}>
    <UserDetail id={id} />
  </Suspense>
</ErrorBoundary>
```

- Place Suspense boundaries close to the data, not at the route root — reveal
  content progressively
- Error Boundary is still a class API; use `react-error-boundary` for a
  hook-friendly wrapper (add via `npm install react-error-boundary`)
- A boundary catches errors thrown during render/lifecycle of its children —
  **not** in event handlers or async code
- To use Suspense with TanStack Query, opt in with `useSuspenseQuery`

## Forms

### React 19 client actions

In a Vite SPA, `useActionState` runs the action **on the client** (there is no
`"use server"`). The action posts to the API via a normal fetch wrapper.

```tsx
import { useActionState } from 'react'
import { createUser } from '../api/users'

type FormState = { error: string | null }
const initial: FormState = { error: null }

async function createUserAction(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const email = String(formData.get('email'))
  const full_name = String(formData.get('full_name'))
  try {
    await createUser({ email, full_name })
    return { error: null }
  } catch (e) {
    return { error: e instanceof Error ? e.message : 'Failed to create user' }
  }
}

export function UserForm() {
  const [state, formAction, pending] = useActionState(createUserAction, initial)
  return (
    <form action={formAction}>
      <input name="full_name" required />
      <input name="email" type="email" required />
      <button type="submit" disabled={pending}>Save</button>
      {state.error && <p role="alert">{state.error}</p>}
    </form>
  )
}
```

### Controlled inputs

Use controlled inputs when the value drives other UI, formats on every
keystroke, or implements real-time validation.

### Complex forms

For multi-step forms, dynamic field arrays, or cross-field validation, use
**[TanStack Form](https://tanstack.com/form)** (the ecosystem choice for this
project) rather than hand-rolling form state — that's a maintenance trap past
trivial complexity.

### Optimistic UI with `useOptimistic`

```tsx
import { useOptimistic } from 'react'
import { sendMessage } from '../api/messages'

export function MessageList({ messages }: { messages: Message[] }) {
  const [optimistic, addOptimistic] = useOptimistic(
    messages,
    (state, newMessage: Message) => [...state, newMessage],
  )

  async function send(formData: FormData) {
    const text = String(formData.get('text'))
    addOptimistic({ id: 'pending', text, sender: 'me' })
    await sendMessage(text) // client-side API call; no Server Action
  }

  return (
    <>
      <ul>{optimistic.map((m) => <li key={m.id}>{m.text}</li>)}</ul>
      <form action={send}>
        <input name="text" />
        <button type="submit">Send</button>
      </form>
    </>
  )
}
```

## Composition Recipes

### Slot via `children`

```tsx
<Layout>
  <Header />
  <Main>{content}</Main>
</Layout>
```

### Named slots

```tsx
<Page header={<Nav />} sidebar={<Filters />}>
  <Results />
</Page>
```

### Compound components (shared state via Context)

```tsx
<Tabs defaultValue="profile">
  <Tabs.List>
    <Tabs.Trigger value="profile">Profile</Tabs.Trigger>
    <Tabs.Trigger value="settings">Settings</Tabs.Trigger>
  </Tabs.List>
  <Tabs.Panel value="profile"><Profile /></Tabs.Panel>
  <Tabs.Panel value="settings"><Settings /></Tabs.Panel>
</Tabs>
```

### Custom hook over render prop

A hook (`useData(id)`) returning `{ data, isLoading }` is usually cleaner than a
function-as-child. With TanStack Query, that hook is often just a thin wrapper
around `useQuery`.

## Performance

### When `React.memo` Actually Helps

Wrap a component in `React.memo` only when all hold:

1. It re-renders frequently
2. Its props are usually the same between renders
3. Its render is measurably expensive

`React.memo` adds an equality check on every render; if props usually differ,
it's pure overhead.

### Avoiding Render Cascades

- Push state down rather than up where possible
- Split context: one context per concern, so a `theme` change doesn't re-render
  auth consumers
- Use `useSyncExternalStore` for external stores — required for safe concurrent
  rendering (TanStack Store handles this for you)

### Lists

- Provide stable `key` props (a database id, never the array index)
- Virtualize long lists with **[TanStack Virtual](https://tanstack.com/virtual)**
  once visible rows exceed ~50 with non-trivial content

## Accessibility-First Composition

- Render semantic HTML (`<button>`, `<a>`, `<nav>`, `<main>`) before reaching for
  `role` attributes
- Every interactive element must be keyboard reachable
- Form inputs need labels — `<label htmlFor>` or `aria-label` when labeled only
  by an icon
- Manage focus on route changes and on modal open/close
- Give error messages `role="alert"` so they're announced

## Routing (TanStack Router)

This project uses **TanStack Router** with a code-based route tree
(`src/router.tsx`: `createRootRoute` + `createRoute` + `createRouter`). The core
component patterns above are router-agnostic; router-specific features (loaders,
search params, typed navigation) follow the
[TanStack Router docs](https://tanstack.com/router). Keep route components thin —
page components live in `src/pages/`.

## Out of Scope

- **Next.js / RSC**: Server Components, Server Actions, App Router data loading —
  not used in this Vite SPA. Do not add `"use client"`/`"use server"` directives.
- **React Native**: platform-specific patterns differ; not applicable here.

## Examples

### Custom hook for debounced search

```tsx
function useDebounce<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(id)
  }, [value, delay])
  return debounced
}

function SearchBox() {
  const [query, setQuery] = useState('')
  const debounced = useDebounce(query, 300)
  const { data } = useQuery({
    queryKey: ['search', debounced],
    queryFn: () => searchApi(debounced),
    enabled: debounced.length > 0,
  })
  return (
    <>
      <input value={query} onChange={(e) => setQuery(e.target.value)} />
      <Results items={data ?? []} />
    </>
  )
}
```

### Splitting context to avoid render cascades

```tsx
// Two contexts: one rarely changes, one frequently.
const ThemeContext = createContext<Theme>('light')
const NotificationsContext = createContext<Notification[]>([])

// A component consuming only ThemeContext does NOT re-render when
// notifications change.
```
