---
name: coding-standards
description: Baseline coding conventions for this project (naming, readability, immutability, error handling, code-quality review). Tailored to the actual stack — React + Vite (TypeScript) frontend and FastAPI + raw asyncpg backend. Use when reviewing code quality or naming.
metadata:
  origin: ECC (adapted for this project's stack)
---

# Coding Standards & Best Practices

Baseline coding conventions for this repository.

This project's stack (see `Agent.md` for the full picture):

- **Frontend:** React 19 + Vite (TypeScript), TanStack Router + TanStack Query.
  There is **no Next.js** — no App Router, no `NextResponse`, no server
  components.
- **Backend:** FastAPI + raw `asyncpg` (no ORM), Pydantic models, forward-only
  SQL migrations.

## When to Activate

- Starting a new module
- Reviewing code for quality and maintainability
- Refactoring existing code to follow conventions
- Enforcing naming, formatting, or structural consistency
- Onboarding new contributors to coding conventions

## Scope Boundaries

Activate this skill for:
- descriptive naming
- immutability defaults
- readability, KISS, DRY, and YAGNI enforcement
- error-handling expectations and code-smell review

## Code Quality Principles

### 1. Readability First
- Code is read more than written
- Clear variable and function names
- Self-documenting code preferred over comments
- Consistent formatting

### 2. KISS (Keep It Simple, Stupid)
- Simplest solution that works
- Avoid over-engineering
- No premature optimization
- Easy to understand > clever code

### 3. DRY (Don't Repeat Yourself)
- Extract common logic into functions
- Create reusable components
- Share utilities across modules
- Avoid copy-paste programming

### 4. YAGNI (You Aren't Gonna Need It)
- Don't build features before they're needed
- Avoid speculative generality
- Add complexity only when required
- Start simple, refactor when needed

## TypeScript/JavaScript Standards (frontend)

### Variable Naming

```typescript
// PASS: GOOD: Descriptive names
const userSearchQuery = 'alice'
const isUserAuthenticated = true
const totalUsers = 1000

// FAIL: BAD: Unclear names
const q = 'alice'
const flag = true
const x = 1000
```

### Function Naming

```typescript
// PASS: GOOD: Verb-noun pattern
async function fetchUsers() { }
function calculateSimilarity(a: number[], b: number[]) { }
function isValidEmail(email: string): boolean { }

// FAIL: BAD: Unclear or noun-only
async function users() { }
function similarity(a, b) { }
function email(e) { }
```

### Immutability Pattern (CRITICAL)

```typescript
// PASS: ALWAYS use spread operator
const updatedUser = {
  ...user,
  full_name: 'New Name'
}

const updatedArray = [...items, newItem]

// FAIL: NEVER mutate directly
user.full_name = 'New Name'  // BAD
items.push(newItem)          // BAD
```

### Error Handling

```typescript
// PASS: GOOD: Comprehensive error handling (matches src/api/users.ts)
export async function fetchUsers(): Promise<User[]> {
  const res = await fetch('/api/users')
  if (!res.ok) {
    throw new Error(`Failed to fetch users: ${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<User[]>
}

// FAIL: BAD: No error handling
async function fetchUsers() {
  const res = await fetch('/api/users')
  return res.json()
}
```

### Async/Await Best Practices

```typescript
// PASS: GOOD: Parallel execution when possible
const [users, stats, config] = await Promise.all([
  fetchUsers(),
  fetchStats(),
  fetchConfig(),
])

// FAIL: BAD: Sequential when unnecessary
const users = await fetchUsers()
const stats = await fetchStats()
const config = await fetchConfig()
```

### Type Safety

```typescript
// PASS: GOOD: Proper types
interface User {
  id: string
  email: string
  full_name: string
  created_at: string
}

async function fetchUser(id: string): Promise<User> {
  // Implementation
}

// FAIL: BAD: Using 'any'
async function fetchUser(id: any): Promise<any> {
  // Implementation
}
```

## React Best Practices

### Component Structure

```typescript
// PASS: GOOD: Functional component with types
interface ButtonProps {
  children: React.ReactNode
  onClick: () => void
  disabled?: boolean
  variant?: 'primary' | 'secondary'
}

export function Button({
  children,
  onClick,
  disabled = false,
  variant = 'primary',
}: ButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`btn btn-${variant}`}
    >
      {children}
    </button>
  )
}

// FAIL: BAD: No types, unclear structure
export function Button(props) {
  return <button onClick={props.onClick}>{props.children}</button>
}
```

### Server State: use TanStack Query

```typescript
// PASS: GOOD: fetch server state via TanStack Query (matches HomePage.tsx)
import { useQuery } from '@tanstack/react-query'
import { fetchUsers } from '../api/users'

const { data: users, isPending, isError, error } = useQuery({
  queryKey: ['users'],
  queryFn: fetchUsers,
})

// FAIL: BAD: ad-hoc fetch + useEffect + useState for server data
```

### Custom Hooks

```typescript
// PASS: GOOD: Reusable custom hook
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const handler = setTimeout(() => setDebouncedValue(value), delay)
    return () => clearTimeout(handler)
  }, [value, delay])

  return debouncedValue
}
```

### State Management

```typescript
// PASS: GOOD: functional update when the next state depends on the previous
setCount(prev => prev + 1)

// FAIL: BAD: direct reference can be stale in async scenarios
setCount(count + 1)
```

For non-trivial shared client state, prefer the TanStack ecosystem
(TanStack Store) over ad-hoc globals — see `frontend/README.md`.

### Conditional Rendering

```typescript
// PASS: GOOD: Clear conditional rendering
{isPending && <Spinner />}
{isError && <ErrorMessage error={error} />}
{users && <UserList users={users} />}

// FAIL: BAD: Ternary hell
{isPending ? <Spinner /> : isError ? <ErrorMessage error={error} /> : users ? <UserList users={users} /> : null}
```

## Python Standards (backend)

### Naming & Type Hints

```python
# PASS: GOOD: descriptive names, typed
async def fetch_user(user_id: UUID) -> UserResponse:
    ...

# FAIL: BAD: unclear, untyped
async def get(u):
    ...
```

### Error Handling

```python
# PASS: GOOD: translate driver errors into meaningful HTTP responses
try:
    row = await conn.fetchrow(
        "INSERT INTO users (email, full_name) VALUES ($1, $2) RETURNING ...",
        payload.email, payload.full_name,
    )
except asyncpg.UniqueViolationError as exc:
    raise HTTPException(status_code=409, detail="Email already exists.") from exc

# FAIL: BAD: let raw driver exceptions bubble up as 500s
row = await conn.fetchrow("INSERT INTO users ...")
```

## API Design Standards (FastAPI)

This project uses FastAPI with Pydantic models. There is no Next.js — do not use
`NextResponse` or API route handlers.

### REST conventions

```
GET    /users            # List users
GET    /users/{id}       # Get a specific user
POST   /users            # Create a user
# Add PATCH/PUT/DELETE as needed following the same shape.
```

### Endpoints + validation with Pydantic

```python
# PASS: GOOD: typed request/response models do validation for you
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)

@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate) -> UserResponse:
    ...  # payload is already validated

# FAIL: BAD: accept untyped dict and validate by hand
@app.post("/users")
async def create_user(payload: dict):
    if "email" not in payload:
        ...
```

FastAPI returns structured `422` validation errors automatically for invalid
request bodies — lean on the models rather than manual checks.

## Database Standards (raw asyncpg)

```python
# PASS: GOOD: parameterized query, select only what you need
row = await conn.fetchrow(
    "SELECT id, email, full_name, created_at FROM users WHERE id = $1",
    user_id,
)

# FAIL: BAD: string interpolation (SQL injection) and SELECT *
row = await conn.fetchrow(f"SELECT * FROM users WHERE id = '{user_id}'")
```

- Always use `$1, $2, ...` placeholders; never interpolate user input into SQL.
- Schema changes are Alembic revisions with hand-written raw SQL in
  `backend/alembic/versions/` (no `--autogenerate`) — never edit an applied
  revision; add a new one.

## File Organization

### Actual project structure

```
backend/
├── alembic/                 # Alembic revisions (hand-written raw SQL, no ORM)
│   └── versions/
├── alembic.ini
└── src/backend/
    ├── app.py             # FastAPI app + routes
    ├── database.py        # asyncpg pool + lifespan (runs `upgrade head`)
    ├── config.py          # env-based settings (+ to_sync_url for Alembic)
    └── models.py          # Pydantic models

frontend/
└── src/
    ├── api/               # API clients (fetch wrappers)
    ├── pages/             # route page components
    ├── router.tsx         # TanStack Router route tree
    └── main.tsx           # providers (QueryClient, Router)
```

### File Naming (frontend)

```
pages/HomePage.tsx         # PascalCase for components
hooks/useDebounce.ts       # camelCase with 'use' prefix
api/users.ts               # camelCase for modules/utilities
```

## Comments & Documentation

### When to Comment

```typescript
// PASS: GOOD: Explain WHY, not WHAT
// Use exponential backoff to avoid overwhelming the API during outages
const delay = Math.min(1000 * Math.pow(2, retryCount), 30000)

// FAIL: BAD: Stating the obvious
// Increment counter by 1
count++
```

### JSDoc for public APIs (TS) / docstrings (Python)

```typescript
/**
 * Fetches the users list from the API.
 *
 * @returns Array of users
 * @throws {Error} If the request fails
 */
export async function fetchUsers(): Promise<User[]> {
  // Implementation
}
```

## Performance Best Practices

### Memoization

```typescript
import { useMemo, useCallback } from 'react'

// PASS: GOOD: Memoize expensive computations.
// Copy before sorting — Array.prototype.sort mutates in place.
const sortedUsers = useMemo(() => {
  return [...users].sort((a, b) => a.full_name.localeCompare(b.full_name))
}, [users])

// PASS: GOOD: Memoize callbacks
const handleSearch = useCallback((query: string) => {
  setSearchQuery(query)
}, [])
```

### Lazy Loading

```typescript
import { lazy, Suspense } from 'react'

// PASS: GOOD: Lazy load heavy components
const HeavyChart = lazy(() => import('./HeavyChart'))

export function Dashboard() {
  return (
    <Suspense fallback={<Spinner />}>
      <HeavyChart />
    </Suspense>
  )
}
```

## Testing Standards

### Test Structure (AAA Pattern)

```python
async def test_upgrade_head_creates_users(conn, alembic_cfg):
    # Arrange: fresh DB (conftest drops alembic_version + users)

    # Act
    alembic_command.upgrade(alembic_cfg, "head")

    # Assert
    assert await _table_exists(conn, "users")
```

### Test Naming

```python
# PASS: GOOD: Descriptive test names
def test_returns_empty_list_when_no_users_exist(): ...
def test_failed_migration_is_rolled_back_and_not_recorded(): ...

# FAIL: BAD: Vague test names
def test_works(): ...
def test_migration(): ...
```

## Code Smell Detection

Watch for these anti-patterns:

### 1. Long Functions
```typescript
// FAIL: BAD: Function > 50 lines
function processData() {
  // 100 lines of code
}

// PASS: GOOD: Split into smaller functions
function processData() {
  const validated = validateData()
  const transformed = transformData(validated)
  return saveData(transformed)
}
```

### 2. Deep Nesting
```typescript
// FAIL: BAD: 5+ levels of nesting
if (user) {
  if (user.isAdmin) {
    if (resource) {
      if (resource.isActive) {
        if (hasPermission) {
          // Do something
        }
      }
    }
  }
}

// PASS: GOOD: Early returns
if (!user) return
if (!user.isAdmin) return
if (!resource) return
if (!resource.isActive) return
if (!hasPermission) return

// Do something
```

### 3. Magic Numbers
```typescript
// FAIL: BAD: Unexplained numbers
if (retryCount > 3) { }
setTimeout(callback, 500)

// PASS: GOOD: Named constants
const MAX_RETRIES = 3
const DEBOUNCE_DELAY_MS = 500

if (retryCount > MAX_RETRIES) { }
setTimeout(callback, DEBOUNCE_DELAY_MS)
```

**Remember**: Code quality is not negotiable. Clear, maintainable code enables rapid development and confident refactoring.
