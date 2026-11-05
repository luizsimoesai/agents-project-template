import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  fetchAllUsers,
  activateUser,
  deactivateUser,
  deleteUser,
} from "@/lib/api/users"

export const USERS_KEY = ["users"]

export function useUsers() {
  return useQuery({ queryKey: USERS_KEY, queryFn: fetchAllUsers })
}

export function useActivateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => activateUser(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: USERS_KEY }),
  })
}

export function useDeactivateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deactivateUser(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: USERS_KEY }),
  })
}

export function useDeleteUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteUser(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: USERS_KEY }),
  })
}
