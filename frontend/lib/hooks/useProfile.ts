import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { fetchCurrentUser, updateUser } from "@/lib/api/users"
import { useAuthStore } from "@/lib/store/auth"
import type { UserUpdate } from "@/lib/types"

export const PROFILE_KEY = ["profile"]

export function useProfile() {
  return useQuery({ queryKey: PROFILE_KEY, queryFn: fetchCurrentUser })
}

export function useUpdateProfile() {
  const qc = useQueryClient()
  const user = useAuthStore((s) => s.user)
  return useMutation({
    mutationFn: (data: UserUpdate) => updateUser(user!.id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: PROFILE_KEY }),
  })
}
