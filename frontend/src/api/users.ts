export interface User {
  id: string
  email: string
  full_name: string
  created_at: string
}

export async function fetchUsers(): Promise<User[]> {
  const res = await fetch('/api/users')
  if (!res.ok) {
    throw new Error(`Failed to fetch users: ${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<User[]>
}
