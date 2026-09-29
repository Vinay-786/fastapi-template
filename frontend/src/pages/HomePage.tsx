import { useQuery } from '@tanstack/react-query'
import { fetchUsers } from '../api/users'

export function HomePage() {
  const {
    data: users,
    isPending,
    isError,
    error,
  } = useQuery({
    queryKey: ['users'],
    queryFn: fetchUsers,
  })

  return (
    <main style={{ maxWidth: 640, margin: '0 auto', padding: '2rem' }}>
      <h1>Users</h1>

      {isPending && <p>Loading users…</p>}

      {isError && (
        <p style={{ color: 'crimson' }}>
          {error instanceof Error ? error.message : 'Something went wrong.'}
        </p>
      )}

      {users && users.length === 0 && <p>No users yet.</p>}

      {users && users.length > 0 && (
        <ul>
          {users.map((user) => (
            <li key={user.id}>
              <strong>{user.full_name}</strong> — {user.email}
            </li>
          ))}
        </ul>
      )}
    </main>
  )
}
